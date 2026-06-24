#!/usr/bin/env python3
"""R-008: Agreement Hash Guard — PreToolUse hook.

Protects agreed-upon documents (requirements, structural definitions)
from unintended modification by tracking SHA256 hashes.

Also enforces DR immutability: DRs that exist on the base branch
(i.e., already merged) cannot be modified. Only DRs created in the
current branch are editable.

When a file registered in .agreement-hashes is about to be modified,
this hook blocks the write (exit 2) and warns the user.

Performance target: <0.1s (mtime-based skip optimization).
"""
import hashlib
import json
import os
import re
import signal
import subprocess
import sys

try:
    signal.alarm(1)
except (AttributeError, ValueError):
    pass


def _get_hashes_path() -> str:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return ""
    return os.path.join(project_dir, ".claude", "logs", ".agreement-hashes")


def _read_hashes() -> dict:
    """Read agreement hashes. Format: {path: {hash, mtime}}."""
    path = _get_hashes_path()
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return {}


def _file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except (FileNotFoundError, PermissionError):
        return ""
    return h.hexdigest()


def _is_merged_dr(file_path: str) -> bool:
    """ファイルがベースブランチに存在するマージ済み DR か判定する。

    decision-records パス配下のファイルで、かつ origin/main に存在する場合は
    マージ済みとみなし True を返す。git コマンド失敗時はフェイルオープン。
    """
    resolved = os.path.realpath(os.path.expanduser(file_path))
    # decision-records パス配下か判定
    if "decision-records" not in resolved:
        return False
    # DR ファイルパターン（.md のみ対象）
    if not resolved.endswith(".md"):
        return False
    # work-logs サブディレクトリは除外（一時ファイル）
    if "work-logs" in resolved or "review-logs" in resolved:
        return False
    try:
        # git リポジトリのルートを特定
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=0.3,
            cwd=os.path.dirname(resolved),
        )
        if result.returncode != 0:
            return False
        repo_root = result.stdout.strip()
        # リポジトリルートからの相対パスを計算
        rel_path = os.path.relpath(resolved, repo_root)
        # origin/main にこのファイルが存在するか確認
        result2 = subprocess.run(
            ["git", "cat-file", "-e", f"origin/main:{rel_path}"],
            capture_output=True, timeout=0.3,
            cwd=repo_root,
        )
        return result2.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False  # フェイルオープン


def _extract_bash_write_paths(cmd: str) -> list:
    """Best-effort extraction of file paths from bash write commands."""
    paths = []
    for pattern in [r'\bcp\b.*\s(\S+)\s*$', r'\bmv\b.*\s(\S+)\s*$']:
        m = re.search(pattern, cmd)
        if m and not m.group(1).startswith('-'):
            paths.append(m.group(1))
    return paths


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})

    target_paths = []
    if tool in ("Write", "Edit"):
        fp = inp.get("file_path", "")
        if fp:
            target_paths.append(fp)
    elif tool == "Bash":
        cmd = inp.get("command", "")
        target_paths = _extract_bash_write_paths(cmd)
        if not target_paths:
            sys.exit(0)
    else:
        sys.exit(0)

    # --- DR 不変ルール: マージ済み DR の改変をブロック ---
    for target in target_paths:
        if _is_merged_dr(target):
            print(
                f"⚠ DR 不変ルール違反: '{target}' はベースブランチにマージ済みの DR です。\n"
                f"  マージ済み DR の内容は改変不可です（追記・修正・削除すべて禁止）。\n"
                f"  → 既存 DR の変更が必要な場合は、新規 DR を起票し supersedes で参照してください。",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- 合意ハッシュチェック ---
    hashes = _read_hashes()
    if not hashes:
        sys.exit(0)

    for target in target_paths:
        resolved = os.path.realpath(os.path.expanduser(target))

        for registered_path, info in hashes.items():
            reg_resolved = os.path.realpath(os.path.expanduser(registered_path))
            if resolved != reg_resolved:
                continue

            registered_hash = info.get("hash", "")
            if not registered_hash:
                continue

            print(
                f"R-008 合意保護: '{target}' は [LOCKED] 状態です。\n"
                f"  この文書は合意済みのため、変更にはユーザーの明示的な承認が必要です。\n"
                f"  変更が必要な場合は、ユーザーに確認してください。",
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
        print(
            f"[Hook Warning] agreement_hash_guard.py error: {e}",
            file=sys.stderr,
        )
        try:
            from hook_logger import log_hook_error
            log_hook_error("agreement_hash_guard.py", e)
        except Exception:
            pass
        sys.exit(0)
