#!/usr/bin/env python3
"""GL-005: Workflow State Gate — PreToolUse hook for Write|Edit.

Blocks non-work-log file writes when a skill is active but approve
(Flow B Step 8) has not been completed. This ensures the AI cannot
skip the resolve→approve workflow and jump directly to implementation.

Anti-forgery: Requires at least 2 user interactions since skill
invocation (tracked by workflow_prompt_guard.py) to prevent the AI
from self-approving by writing [MEANS-LOCKED] to the work-log
without actual user consent.

Checks (in order):
1. .workflow-expected exists? No → ALLOW (no active skill)
2. Target is work-log or .claude/logs/ state file? → ALLOW
3. [MEANS-LOCKED] in owned work-log? No → BLOCK
4. user_interactions >= 2 in .workflow-expected? No → BLOCK
5. ALLOW (approve completed with user consent)
"""
from __future__ import annotations

import json
import os
import signal
import sys

# 1秒タイムアウト（ハング防止）
try:
    signal.alarm(1)
except (AttributeError, ValueError):
    pass


def _get_project_dir() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR", "")


def _get_marker_path(name: str) -> str:
    pd = _get_project_dir()
    if not pd:
        return ""
    return os.path.join(pd, ".claude", "logs", f".workflow-{name}")


def _get_my_pid() -> str:
    """Get session PID from context-locks (same logic as worklog_guard.py)."""
    pd = _get_project_dir()
    if not pd:
        return str(os.getppid())
    locks_dir = os.path.join(pd, ".claude", "logs", ".context-locks")
    if os.path.isdir(locks_dir):
        for fname in os.listdir(locks_dir):
            try:
                int(fname)
                return fname
            except ValueError:
                continue
    return str(os.getppid())


def _is_worklog_or_state_file(file_path: str) -> bool:
    """Check if target is a work-log or framework state/log file.

    Always-writable paths:
    - .claude/logs/work-logs/*.md (work-logs themselves)
    - .claude/logs/.* (state markers, locks, caches)
    """
    pd = _get_project_dir()
    if not pd:
        return False
    logs_dir = os.path.join(pd, ".claude", "logs")
    abs_path = os.path.abspath(file_path)
    abs_logs = os.path.abspath(logs_dir)
    if abs_path.startswith(abs_logs + os.sep) or abs_path == abs_logs:
        return True
    # Also allow worktree work-logs (docs/decision-records/*/work-logs/)
    if "/work-logs/" in abs_path or "\\work-logs\\" in abs_path:
        return True
    return False


def _find_owned_worklog_with_means_locked() -> bool:
    """Check if any work-log owned by this session has [MEANS-LOCKED].

    Uses GL-004 worklog-locks to identify owned work-logs.
    """
    pd = _get_project_dir()
    if not pd:
        return False

    my_pid = _get_my_pid()
    locks_dir = os.path.join(pd, ".claude", "logs", ".worklog-locks")
    worklogs_dir = os.path.join(pd, ".claude", "logs", "work-logs")

    if not os.path.isdir(locks_dir):
        return False

    for lock_name in os.listdir(locks_dir):
        lock_path = os.path.join(locks_dir, lock_name)
        try:
            with open(lock_path) as f:
                pid = f.read().strip()
        except (OSError, IOError):
            continue

        if pid != my_pid:
            continue

        # Found owned work-log — check for [MEANS-LOCKED]
        wl_path = os.path.join(worklogs_dir, lock_name + ".md")
        if os.path.isfile(wl_path):
            try:
                with open(wl_path) as f:
                    content = f.read()
                if "[MEANS-LOCKED]" in content:
                    return True
            except (OSError, IOError):
                continue

    # Also check worktree work-logs via context-lock
    context_locks_dir = os.path.join(pd, ".claude", "logs", ".context-locks")
    if not os.path.isdir(context_locks_dir):
        return False

    for fname in os.listdir(context_locks_dir):
        ctx_lock_path = os.path.join(context_locks_dir, fname)
        try:
            with open(ctx_lock_path) as f:
                worktree_path = f.read().strip()
        except (OSError, IOError):
            continue

        if not os.path.isdir(worktree_path):
            continue

        # Scan docs/decision-records/*/work-logs/ in worktree (bounded depth)
        dr_base = os.path.join(worktree_path, "docs", "decision-records")
        if not os.path.isdir(dr_base):
            continue

        try:
            for pr_dir in os.listdir(dr_base):
                wl_dir = os.path.join(dr_base, pr_dir, "work-logs")
                if not os.path.isdir(wl_dir):
                    continue
                for wl_file in os.listdir(wl_dir):
                    if not wl_file.endswith(".md"):
                        continue
                    wl_path = os.path.join(wl_dir, wl_file)
                    try:
                        with open(wl_path) as f:
                            content = f.read()
                        if "[MEANS-LOCKED]" in content:
                            return True
                    except (OSError, IOError):
                        continue
        except OSError:
            continue

    return False


def _get_user_interactions() -> int:
    """Get user interaction count from .workflow-expected marker."""
    marker = _get_marker_path("expected")
    if not marker or not os.path.isfile(marker):
        return 0
    try:
        with open(marker) as f:
            data = json.load(f)
        return data.get("user_interactions", 0)
    except (json.JSONDecodeError, OSError):
        return 0


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool = data.get("tool_name", "")
    if tool not in ("Write", "Edit"):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    # --- Check 1: No active skill → ALLOW ---
    expected_marker = _get_marker_path("expected")
    if not expected_marker or not os.path.isfile(expected_marker):
        sys.exit(0)

    # --- Check 2: Target is work-log or state file → ALLOW ---
    if _is_worklog_or_state_file(file_path):
        sys.exit(0)

    # --- Check 3: [MEANS-LOCKED] in owned work-log ---
    if not _find_owned_worklog_with_means_locked():
        print(json.dumps({
            "decision": "block",
            "reason": (
                "GL-005: approve 未完了 — work-log に [MEANS-LOCKED] がありません。\n"
                "Flow B Step 8 を完了してください:\n"
                "  1. 手段（フローチャート + データ定義）をユーザーに提示\n"
                "  2. ユーザーの OK を得る\n"
                "  3. work-log に [MEANS-LOCKED] を記録\n"
                "その後、実装ファイルへの書き込みが許可されます。"
            ),
        }))
        sys.exit(2)

    # --- Check 4: Anti-forgery — user interaction count ---
    interactions = _get_user_interactions()
    if interactions < 2:
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"GL-005: ユーザー承認不足（{interactions}/2回）。\n"
                "[MEANS-LOCKED] が記録されていますが、スキル呼び出し後の"
                "ユーザー応答が2回未満です。\n"
                "resolve 承認（[PURPOSE-LOCKED]）と approve 承認（[MEANS-LOCKED]）の"
                "両方でユーザーの明示的な OK が必要です。"
            ),
        }))
        sys.exit(2)

    # --- All checks passed → ALLOW ---
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # フェイルオープン: hook 自体のエラーでは通過
        print(
            f"[Hook Warning] workflow_state_gate.py error: {e}",
            file=sys.stderr,
        )
        try:
            from hook_logger import log_hook_error
            log_hook_error("workflow_state_gate.py", e)
        except Exception:
            pass
        sys.exit(0)
