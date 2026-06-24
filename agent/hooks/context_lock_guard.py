#!/usr/bin/env python3
"""GL-001: Context Lock Path Guard — PreToolUse hook.

Validates that all file write operations target paths within the locked context.
Prevents a single chat session from silently writing to multiple working directories
(e.g., writing to both main AND a worktree).

S-009: Also detects uncommitted changes when joining an existing worktree.

How it works:
  1. Step 0 of any skill writes the locked path to:
       {CLAUDE_PROJECT_DIR}/.claude/logs/.context-locks/{PID}
  2. This hook reads ALL files in .context-locks/ on every Write/Edit/Bash call
  3. If the target file path is OUTSIDE all locked paths → exit 2 (block)

Concurrency support:
  Each Claude Code session writes its own lock file (using shell PID as filename).
  The hook allows writes to ANY currently-locked path.
  CLAUDE.md instructions provide per-session isolation (each chat only writes to
  its own locked worktree). This hook is a defensive safety net.

If no lock files exist, all writes are allowed (no session has locked yet).
"""
import json
import os
import re
import signal
import subprocess
import sys

# 1秒タイムアウト（ハング防止）
try:
    signal.alarm(1)
except (AttributeError, ValueError):
    pass


def _read_lock_paths() -> list:
    """Read all active lock paths from the locks directory."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return []

    logs_dir = os.path.join(project_dir, ".claude", "logs")
    paths = []

    # Directory-based locks (.context-locks/)
    locks_dir = os.path.join(logs_dir, ".context-locks")
    if os.path.isdir(locks_dir):
        for fname in os.listdir(locks_dir):
            if fname.startswith("."):
                continue
            fpath = os.path.join(locks_dir, fname)
            try:
                with open(fpath) as f:
                    p = f.read().strip()
                    if p:
                        paths.append(p)
            except (FileNotFoundError, PermissionError):
                continue

    # Backward compat: legacy single file
    legacy = os.path.join(logs_dir, ".context-lock-path")
    if os.path.isfile(legacy):
        try:
            with open(legacy) as f:
                p = f.read().strip()
                if p:
                    paths.append(p)
        except (FileNotFoundError, PermissionError):
            pass

    return paths


def _resolve_path(path: str) -> str:
    """Resolve a path to absolute, following symlinks."""
    return os.path.realpath(os.path.expanduser(path))


def _is_within(target: str, allowed_root: str) -> bool:
    """Check if target path is within the allowed root directory."""
    target = _resolve_path(target)
    allowed_root = _resolve_path(allowed_root)
    if not allowed_root.endswith("/"):
        allowed_root += "/"
    return target.startswith(allowed_root) or target == allowed_root.rstrip("/")


def _find_repo_root(path: str):
    """Find the git repo root by walking up from the given path."""
    resolved = _resolve_path(path)
    current = resolved
    while current != "/":
        if os.path.exists(os.path.join(current, ".git")):
            return current
        current = os.path.dirname(current)
    return None


def _is_allowed(target: str, lock_paths: list) -> bool:
    """Check if target path is allowed given ALL active locks.

    Allowed targets:
    1. Paths within ANY locked directory
    2. Paths within {CLAUDE_PROJECT_DIR}/.claude/ (framework files — always writable)
    3. Paths outside ALL known repo trees (temp files, /tmp, etc.)
    """
    resolved = _resolve_path(target)

    # Rule 1: Within any locked path
    for lp in lock_paths:
        if _is_within(resolved, lp):
            return True

    # Rule 2: Framework files (.claude/) are always writable
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        claude_dir = os.path.join(_resolve_path(project_dir), ".claude")
        if _is_within(resolved, claude_dir):
            return True

    # Rule 3: Outside ALL repo trees → safe (temp files, etc.)
    # If target is inside ANY repo that has a lock, it must be blocked
    for lp in lock_paths:
        repo_root = _find_repo_root(lp)
        if repo_root and _is_within(resolved, repo_root):
            # Target is inside a repo with an active lock but not in the locked path
            return False

    # Target is outside all known repos → safe (temp files, /tmp, etc.)
    return True


def _check_worktree_uncommitted(cmd: str) -> None:
    """S-009: 既存 worktree への合流時に未コミット変更を検出して警告する。

    git -C {worktree_path} で既存 worktree に対する操作が検出された場合、
    その worktree に未コミット変更がないか確認する。
    未コミット変更があれば stderr に警告を出力（ブロックはしない）。
    """
    # git -C <worktree_path> commit/push 等を検出
    m = re.search(r'git\s+-C\s+(\S+)', cmd)
    if not m:
        return

    worktree_path = m.group(1)
    if not os.path.isdir(worktree_path):
        return

    # 初回アクセスチェック（同一セッションで既にチェック済みなら再実行しない）
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        check_marker = os.path.join(
            project_dir, ".claude", "logs", ".uncommitted-checked"
        )
        if os.path.isfile(check_marker):
            try:
                with open(check_marker) as f:
                    checked_path = f.read().strip()
                if checked_path == os.path.realpath(worktree_path):
                    return  # 既にチェック済み
            except (FileNotFoundError, PermissionError):
                pass

    try:
        result = subprocess.run(
            ["git", "-C", worktree_path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            print(
                f"⚠ S-009 警告: worktree に前チャットの未コミット変更があります。\n"
                f"  パス: {worktree_path}\n"
                f"  未コミット変更: {len(lines)} ファイル\n"
                + "\n".join(f"    {line}" for line in lines[:10])
                + (f"\n    ... 他 {len(lines) - 10} ファイル" if len(lines) > 10 else "")
                + f"\n  → 作業開始前に確認してください。コンフリクトがあれば解消してから作業を続行。",
                file=sys.stderr,
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass  # フェイルオープン

    # チェック済みマーカーを記録
    if project_dir:
        try:
            marker_dir = os.path.dirname(check_marker)
            os.makedirs(marker_dir, exist_ok=True)
            with open(check_marker, "w") as f:
                f.write(os.path.realpath(worktree_path))
        except OSError:
            pass


def _extract_bash_write_paths(cmd: str) -> list:
    """Best-effort extraction of file paths from bash commands that write files."""
    paths = []

    # git worktree add <path>
    m = re.search(r'git\s+(?:-C\s+\S+\s+)?worktree\s+add\s+(\S+)', cmd)
    if m:
        paths.append(m.group(1))

    # git -C <path> commit/push/etc — the -C path itself is the working dir
    # Don't block git read commands (log, status, diff, fetch, branch, worktree list)
    read_cmds = r'(?:log|status|diff|fetch|branch|worktree\s+list|remote|show|rev-parse|merge-base)'
    m = re.search(r'git\s+-C\s+(\S+)\s+(?!' + read_cmds + r')', cmd)
    if m:
        paths.append(m.group(1))

    # cp/mv destination (last argument)
    for pattern in [r'\bcp\b.*\s(\S+)\s*$', r'\bmv\b.*\s(\S+)\s*$']:
        m = re.search(pattern, cmd)
        if m and not m.group(1).startswith('-'):
            paths.append(m.group(1))

    # mkdir -p <path>
    m = re.search(r'\bmkdir\b.*\s(\S+)\s*$', cmd)
    if m and not m.group(1).startswith('-'):
        paths.append(m.group(1))

    return paths


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)  # パース失敗はフェイルオープン

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})

    # Lock paths を読み込み（複数セッション対応）
    lock_paths = _read_lock_paths()
    if not lock_paths:
        # ロック未確立 → 検証スキップ
        sys.exit(0)

    # === ファイルパス抽出 ===
    target_paths: list = []

    if tool in ("Write", "Edit"):
        file_path = inp.get("file_path", "")
        if file_path:
            target_paths.append(file_path)

    elif tool == "Bash":
        cmd = inp.get("command", "")

        # S-009: 既存 worktree への合流時に未コミット変更を検出（警告のみ）
        _check_worktree_uncommitted(cmd)

        target_paths = _extract_bash_write_paths(cmd)
        # Bash のパス検出はベストエフォート — 検出できない場合は通過
        if not target_paths:
            sys.exit(0)

    else:
        sys.exit(0)

    # === パス検証（全ロックパスに対して統合的に判定） ===
    for target in target_paths:
        if not _is_allowed(target, lock_paths):
            print(
                f"⚠ GL-001 違反: コンテキストロック外への書き込みをブロックしました。\n"
                f"  有効ロック: {lock_paths}\n"
                f"  書き込み先: {target}\n"
                f"  → ロック先のworktree内のパスに変更してください。\n"
                f"  → 別のworktreeやmainで作業する場合は、新しいチャットを開始してください。",
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
        print(f"[Hook Warning] context_lock_guard.py error: {e}", file=sys.stderr)
        try:
            from hook_logger import log_hook_error
            log_hook_error("context_lock_guard.py", e)
        except Exception:
            pass
        sys.exit(0)
