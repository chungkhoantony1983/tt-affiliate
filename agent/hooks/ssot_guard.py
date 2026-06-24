#!/usr/bin/env python3
"""GL-003 / GL-006: SSoT Guard — PreToolUse hook.

learned-rules.yaml と improvement-backlog.yaml への書き込みが
SSoT（repo-registry.md が存在する .claude/references/）内であることを検証する。

配布先リポ（repo-registry.md なし）への書き込みをブロックする。
また、リポ CLAUDE.md への learned-rules 形式の書き込みも検出する。

Check 3: SSoT ファイルへの書き込み時に ssot_impact が work-log で宣言済みか検証する。
未宣言の場合は警告し、resolve に戻って ssot_impact を宣言するよう促す。

Check 4 (GL-006): learned-rules.yaml への書き込みでPJ固有の戦略的制約
（テックスタック選定、設計方針、PJ固有ビジネスルール等）を検出し、ブロックする。
learned-rules.yaml は AI 汎用運用ルール専用。PJ固有制約は DR / docs/specs/ / work-log に配置する。
"""
from __future__ import annotations
import json
import os
import re
import sys


# SSoT 管理対象ファイル名
_SSOT_FILES = ("learned-rules.yaml", "improvement-backlog.yaml")

# learned-rules 形式のパターン（CLAUDE.md への書き込み検出用）
_RULE_PATTERN = re.compile(
    r"(?:^|\n)\s*-\s+id:\s+\w+-\d+.*?(?:rule:|type:\s+(?:bridge|permanent))",
    re.DOTALL,
)

# PJ固有制約の検出パターン（learned-rules.yaml への書き込み検出用）
# rule: フィールドの内容にPJ固有の戦略的制約が含まれるかチェック
_PJ_CONSTRAINT_PATTERNS = [
    # テックスタック選定（具体的なフレームワーク+「使用/採用/選定」）
    re.compile(
        r"(?:React\s*Native|Capacitor|Vite|Next\.?js|Nuxt|Flutter|Expo)"
        r".*?(?:使用|採用|選定|利用|移行|統合|活用)",
        re.IGNORECASE,
    ),
    # PJ固有の設計方針（「〜方式/方針で」の形でPJ名を含む）
    re.compile(
        r"(?:マイクロサービス|モノリス|サーバーレス|BFF|CQRS)"
        r".*?(?:方式|方針|アーキテクチャ|構成).*?(?:採用|決定|確定)",
        re.IGNORECASE,
    ),
    # PJ固有のDB・インフラ選定
    re.compile(
        r"(?:PostgreSQL|MySQL|DynamoDB|Firestore|Supabase|PlanetScale)"
        r".*?(?:使用|採用|統合|活用|接続)",
        re.IGNORECASE,
    ),
    # PJ固有のビジネスルール（特定PJ名+制約）
    re.compile(
        r"(?:TIKTOK_SECRET|SHOPEE_SECRET|API_KEY_PROD)"
        r".*?(?:必須|禁止|制約|前提|方針)",
        re.IGNORECASE,
    ),
]


def _is_ssot_dir(file_path: str) -> bool:
    """ファイルが SSoT ディレクトリ内にあるか判定。

    SSoT = repo-registry.md が存在する .claude/references/ 配下。
    """
    resolved = os.path.realpath(os.path.expanduser(file_path))
    # .claude/references/ を含むパスを探す
    parts = resolved.split(os.sep)
    for i, part in enumerate(parts):
        if part == ".claude" and i + 1 < len(parts) and parts[i + 1] == "references":
            # .claude/references/ のディレクトリパスを構築
            ref_dir = os.sep.join(parts[: i + 2])
            registry = os.path.join(ref_dir, "repo-registry.md")
            return os.path.isfile(registry)
    return False


def _is_ssot_file(resolved_path: str) -> bool:
    """SSoT ルート (.claude/) 配下のファイルかつ、除外ディレクトリでないか判定。

    除外: .claude/logs/, .claude/hooks/ (hook 自身の更新は対象外)
    work-log テンプレートの更新等は対象。
    """
    parts = resolved_path.split(os.sep)
    for i, part in enumerate(parts):
        if part == ".claude":
            # .claude/ 配下であることを確認
            ref_dir = os.sep.join(parts[: i + 1])
            registry = os.path.join(ref_dir, "references", "repo-registry.md")
            if not os.path.isfile(registry):
                return False  # SSoT ではない（配布先リポ）
            # 除外ディレクトリチェック
            remaining = parts[i + 1 :] if i + 1 < len(parts) else []
            if remaining and remaining[0] in ("logs", "hooks"):
                return False
            return True
    return False


def _find_ssot_impact_file() -> str | None:
    """ssot_impact 宣言ファイル (.claude/logs/.ssot-impact-declared) を検索。

    ファイルが存在すれば宣言済みとみなす。
    """
    claude_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not claude_dir:
        return None
    impact_path = os.path.join(claude_dir, ".claude", "logs", ".ssot-impact-declared")
    if os.path.isfile(impact_path):
        return impact_path
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})

    file_path = ""
    content = ""

    if tool in ("Write", "Edit"):
        file_path = inp.get("file_path", "")
        if tool == "Write":
            content = inp.get("content", "")
        else:
            content = inp.get("new_string", "")
    else:
        sys.exit(0)

    if not file_path:
        sys.exit(0)

    basename = os.path.basename(file_path)

    # === Check 1: SSoT 管理対象ファイルへの書き込み ===
    if basename in _SSOT_FILES:
        if not _is_ssot_dir(file_path):
            print(
                f"⚠ GL-003 違反: {basename} への書き込みは SSoT でのみ許可されています。\n"
                f"  書き込み先: {file_path}\n"
                f"  SSoT パス: repo-registry.md が存在する .claude/references/ 配下\n"
                f"  → SSoT の {basename} に書き込んでください。\n"
                f"  → 配布先リポの {basename} は /sync で上書きされます。",
                file=sys.stderr,
            )
            sys.exit(2)

    # === Check 2: リポ CLAUDE.md への learned-rules 形式の書き込み ===
    if basename == "CLAUDE.md" and content:
        if _RULE_PATTERN.search(content):
            print(
                "⚠ GL-003 違反: CLAUDE.md に learned-rules 形式のルールを検出しました。\n"
                "  ルールは SSoT の learned-rules.yaml に一元保存してください。\n"
                "  → /ai-learn を使用して SSoT に書き込んでください。\n"
                "  → CLAUDE.md にルールを書くと管理が分散します。",
                file=sys.stderr,
            )
            sys.exit(2)

    # === Check 4 (GL-006): learned-rules.yaml へのPJ固有制約書き込みブロック ===
    if basename == "learned-rules.yaml" and content:
        for pj_pattern in _PJ_CONSTRAINT_PATTERNS:
            match = pj_pattern.search(content)
            if match:
                matched_text = match.group(0)[:80]
                print(
                    f"⚠ GL-006 違反: learned-rules.yaml にPJ固有の戦略的制約を検出しました。\n"
                    f"  検出内容: \"{matched_text}\"\n"
                    f"  learned-rules.yaml は AI 汎用運用ルール専用です。\n"
                    f"  → PJ固有の設計判断 → DR（decision-records）\n"
                    f"  → PJ固有の仕様・設計 → docs/specs/\n"
                    f"  → セッション中の制約 → work-log 制約追加履歴\n"
                    f"  → /ai-learn はAI運用ルールのみ学習可能です。",
                    file=sys.stderr,
                )
                sys.exit(2)

    # === Check 3: SSoT ファイル書き込み時の ssot_impact 宣言チェック ===
    # .claude/ 配下（SSoT ルート）への書き込みで、work-log / hooks / logs を除く
    resolved = os.path.realpath(os.path.expanduser(file_path))
    if _is_ssot_file(resolved):
        impact_file = _find_ssot_impact_file()
        if impact_file is None:
            print(
                "⚠ ssot_impact 未宣言: SSoT ファイルへの書き込みですが、"
                "work-log に ssot_impact が宣言されていません。\n"
                f"  書き込み先: {file_path}\n"
                "  → Step 7 (resolve) に戻って ssot_impact を宣言してください。\n"
                "  → 宣言済みの場合は .claude/logs/.ssot-impact-declared に記録してください。",
                file=sys.stderr,
            )
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # フェイルオープン: hook 自体のエラーでは通過
        print(f"[Hook Warning] ssot_guard.py error: {e}", file=sys.stderr)
        try:
            from hook_logger import log_hook_error
            log_hook_error("ssot_guard.py", e)
        except Exception:
            pass
        sys.exit(0)
