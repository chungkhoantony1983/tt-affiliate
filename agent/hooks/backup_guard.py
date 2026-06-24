#!/usr/bin/env python3
"""GL-008: 非Gitフォルダ自動バックアップ — PreToolUse hook (Write|Edit).

非Gitフォルダへのファイル書き込み時に、変更前のファイルを自動バックアップする。
Git管理されたリポジトリでは何もしない（Git自体がロールバック機能を提供するため）。

バックアップ先: {対象フォルダ}/.claude-backups/{YYYY-MM-DD}/{HHMMSS}_{filename}
保持期間: 7日（session_start.py Section 8 が古いバックアップを自動削除）

設計判断:
  - ブロックではなく透過型（exit 0 で常に通過。バックアップは副作用）
  - フェイルオープン（バックアップ失敗でも書き込みは許可）
  - .claude-backups/ 自体への書き込みはバックアップしない（無限再帰防止）
  - 新規ファイル（まだ存在しない）はバックアップ対象外
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# バックアップディレクトリ名
_BACKUP_DIR = ".claude-backups"

# バックアップ対象外パターン
_SKIP_PATTERNS = (
    _BACKUP_DIR,
    ".claude/logs/",
    ".claude-session-lock",
    "__pycache__",
    ".pyc",
)


def _is_git_managed(filepath: str) -> bool:
    """ファイルが Git 管理下にあるか判定する。"""
    dirpath = os.path.dirname(os.path.abspath(filepath))
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=dirpath,
            capture_output=True,
            text=True,
            timeout=0.5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _find_backup_root(filepath: str) -> str | None:
    """バックアップルートディレクトリを決定する。

    コンテキストロックのパスがあればそれを使い、なければファイルの親ディレクトリを使う。
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        # コンテキストロックからロック先パスを取得
        locks_dir = os.path.join(project_dir, ".claude", "logs", ".context-locks")
        if os.path.isdir(locks_dir):
            for lockfile in os.listdir(locks_dir):
                lockpath = os.path.join(locks_dir, lockfile)
                try:
                    with open(lockpath, encoding="utf-8") as f:
                        locked_path = f.read().strip()
                    if locked_path and os.path.abspath(filepath).startswith(
                        os.path.abspath(locked_path)
                    ):
                        return locked_path
                except (OSError, UnicodeDecodeError):
                    continue
    # フォールバック: ファイルの親ディレクトリ
    return os.path.dirname(os.path.abspath(filepath))


def _backup_file(filepath: str) -> None:
    """ファイルのバックアップを作成する。"""
    abs_path = os.path.abspath(filepath)

    # 存在しないファイルはバックアップ不要（新規作成）
    if not os.path.isfile(abs_path):
        return

    # スキップ対象チェック
    for pattern in _SKIP_PATTERNS:
        if pattern in abs_path:
            return

    backup_root = _find_backup_root(filepath)
    if not backup_root:
        return

    now = datetime.now()
    date_dir = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")
    filename = os.path.basename(abs_path)

    backup_dir = os.path.join(backup_root, _BACKUP_DIR, date_dir)
    backup_path = os.path.join(backup_dir, f"{timestamp}_{filename}")

    # 同一秒に同名ファイルの重複バックアップを防止
    if os.path.exists(backup_path):
        backup_path = os.path.join(
            backup_dir, f"{timestamp}_{int(time.time() * 1000) % 1000}_{filename}"
        )

    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(abs_path, backup_path)


def _extract_filepath(tool_name: str, tool_input: dict) -> str | None:
    """ツール入力からファイルパスを抽出する。"""
    if tool_name in ("Write", "Edit"):
        return tool_input.get("file_path")
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    filepath = _extract_filepath(tool_name, tool_input)
    if not filepath:
        sys.exit(0)

    # Git管理下なら何もしない
    if _is_git_managed(filepath):
        sys.exit(0)

    # 非Gitフォルダ → 自動バックアップ
    try:
        _backup_file(filepath)
    except Exception:
        pass  # フェイルオープン: バックアップ失敗でも書き込みは許可

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # フェイルオープン
