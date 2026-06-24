#!/usr/bin/env python3
"""GL-006: PJ固有 CLAUDE.md コンテンツガード — PreToolUse hook.

{repo}/CLAUDE.md（PJ固有パス設定ファイル）への書き込みで、
PJ固有パス設定テーブル以外のコンテンツ追加をブロックする。

対象:
- SSoT の CLAUDE.md (.claude/CLAUDE.md) は対象外（フレームワーク定義の正本）
- {repo}/CLAUDE.md のみ対象（PJ固有パス設定テーブルのみ許可）

検出対象:
- テックスタック・フレームワーク名の記述
- 制約・設計方針の記述
- SSoT索引テーブルの追加
"""
from __future__ import annotations
import json
import os
import re
import sys


def _is_ssot_claude_md(file_path: str) -> bool:
    """SSoT の CLAUDE.md かどうか判定。

    SSoT = repo-registry.md が存在する .claude/ 配下の CLAUDE.md。
    """
    resolved = os.path.realpath(os.path.expanduser(file_path))
    parts = resolved.split(os.sep)
    for i, part in enumerate(parts):
        if part == ".claude":
            ref_dir = os.sep.join(parts[: i + 1])
            registry = os.path.join(ref_dir, "references", "repo-registry.md")
            if os.path.isfile(registry):
                return True
    return False


def _is_repo_claude_md(file_path: str) -> bool:
    """リポジトリルートの CLAUDE.md かどうか判定。

    {repo}/CLAUDE.md = git リポジトリルート直下の CLAUDE.md。
    .claude/CLAUDE.md は対象外。
    """
    resolved = os.path.realpath(os.path.expanduser(file_path))
    basename = os.path.basename(resolved)
    if basename != "CLAUDE.md":
        return False
    # SSoT の CLAUDE.md は対象外
    if _is_ssot_claude_md(resolved):
        return False
    # .claude/ 配下の CLAUDE.md は対象外（sync で管理されるコピー）
    if "/.claude/" in resolved or resolved.endswith("/.claude"):
        return False
    # 親ディレクトリに .git があるか確認（リポルート判定）
    parent = os.path.dirname(resolved)
    if os.path.isdir(os.path.join(parent, ".git")):
        return True
    # worktree の場合: .git がファイル（gitdir 参照）の場合もリポルート
    git_path = os.path.join(parent, ".git")
    if os.path.isfile(git_path):
        return True
    return False


# PJ固有パス設定テーブルのみ許可。以下のパターンを検出してブロック:
_PROHIBITED_PATTERNS = [
    # テックスタック・フレームワーク記述
    (
        re.compile(
            r"(?:tech[-\s]?stack|テックスタック|フレームワーク|framework)\s*[:：]",
            re.IGNORECASE,
        ),
        "テックスタック・フレームワーク定義",
    ),
    # 制約・方針の記述
    (
        re.compile(
            r"(?:^|\n)#+\s*(?:制約|constraints?|設計方針|design\s*(?:principle|policy))",
            re.IGNORECASE | re.MULTILINE,
        ),
        "制約・設計方針セクション",
    ),
    # SSoT索引テーブルの追加
    (
        re.compile(
            r"(?:^|\n)#+\s*(?:SSoT\s*索引|SSoT\s*index)",
            re.IGNORECASE | re.MULTILINE,
        ),
        "SSoT索引テーブル",
    ),
    # learned-rules 形式のルール
    (
        re.compile(
            r"(?:^|\n)\s*-\s+id:\s+\w+-\d+.*?(?:rule:|type:\s+(?:bridge|permanent))",
            re.DOTALL,
        ),
        "learned-rules 形式のルール",
    ),
    # 具体的な技術選定の記述（React, Vue, Next, Vite 等）
    (
        re.compile(
            r"(?:^|\n)#+\s*(?:技術選定|tech\s*selection|アーキテクチャ|architecture)",
            re.IGNORECASE | re.MULTILINE,
        ),
        "技術選定・アーキテクチャセクション",
    ),
]

# 許可パターン: PJ固有パス設定テーブルの構成要素
_ALLOWED_PATTERNS = [
    re.compile(r"PJ固有パス設定"),
    re.compile(r"\{BASE_BRANCH\}"),
    re.compile(r"\{DR_PATH\}"),
    re.compile(r"\{REVIEW_LOG_PATH\}"),
    re.compile(r"\|\s*変数\s*\|\s*値\s*\|"),  # テーブルヘッダー
]


def _is_path_settings_only(content: str) -> bool:
    """書き込み内容がPJ固有パス設定テーブル関連のみかどうか判定。"""
    for pattern in _ALLOWED_PATTERNS:
        if pattern.search(content):
            return True
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})

    if tool not in ("Write", "Edit"):
        sys.exit(0)

    file_path = inp.get("file_path", "")
    if not file_path:
        sys.exit(0)

    # {repo}/CLAUDE.md 以外は対象外
    if not _is_repo_claude_md(file_path):
        sys.exit(0)

    # 書き込み内容を取得
    if tool == "Write":
        content = inp.get("content", "")
    else:
        content = inp.get("new_string", "")

    if not content:
        sys.exit(0)

    # PJ固有パス設定テーブル関連の書き込みは許可
    if _is_path_settings_only(content):
        sys.exit(0)

    # 禁止パターンのチェック
    for pattern, description in _PROHIBITED_PATTERNS:
        if pattern.search(content):
            print(
                f"⚠ GL-006 違反: {{repo}}/CLAUDE.md に{description}を検出しました。\n"
                f"  {{repo}}/CLAUDE.md はPJ固有パス設定テーブルのみ許可されています。\n"
                f"  → PJ固有の設計判断・制約の正しい配置先:\n"
                f"    - 確定判断 → DR（decision-records）\n"
                f"    - 仕様・設計 → docs/specs/\n"
                f"    - セッション中の制約 → work-log 制約追加履歴\n"
                f"    - AI運用ルール → learned-rules.yaml（PJ制約は不可）\n",
                file=sys.stderr,
            )
            sys.exit(2)

    # 禁止パターンに該当しなくても通過（false positive 防止のフェイルオープン）
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # フェイルオープン: hook 自体のエラーでは通過
        print(f"[Hook Warning] claude_md_guard.py error: {e}", file=sys.stderr)
        try:
            from hook_logger import log_hook_error
            log_hook_error("claude_md_guard.py", e)
        except Exception:
            pass
        sys.exit(0)
