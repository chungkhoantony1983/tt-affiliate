#!/usr/bin/env python3
"""R-001: Placement Rule Guard — PreToolUse hook.

Validates that file write operations conform to placement rules
extracted from README.md and cached in .placement-rules-cache.

Initial mode: WARNING ONLY (exit 0). Does not block writes.
To enable blocking, change _BLOCK_MODE to True.

Performance target: <0.1s (cache read only, no file I/O beyond cache).
"""
import json
import os
import re
import signal
import sys

try:
    signal.alarm(1)
except (AttributeError, ValueError):
    pass

_BLOCK_MODE = True  # Block non-conforming writes (R-001)


def _read_cache() -> dict:
    """Read cached placement rules from .placement-rules-cache."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return {}

    cache_path = os.path.join(
        project_dir, ".claude", "logs", ".placement-rules-cache"
    )
    if not os.path.isfile(cache_path):
        return {}

    try:
        with open(cache_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return {}


def _check_naming(filename: str, rules: dict) -> bool:
    """Check if filename conforms to naming rules."""
    pattern = rules.get("naming_pattern", "")
    if not pattern:
        return True
    try:
        return bool(re.match(pattern, filename))
    except re.error:
        return True  # Invalid regex → fail open


def _check_directory(file_path: str, rules: dict) -> bool:
    """Check if file is in an allowed directory."""
    allowed_dirs = rules.get("allowed_directories", [])
    if not allowed_dirs:
        return True
    resolved = os.path.realpath(file_path)
    for d in allowed_dirs:
        d_resolved = os.path.realpath(d)
        if resolved.startswith(d_resolved):
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

    cache = _read_cache()
    if not cache:
        sys.exit(0)

    filename = os.path.basename(file_path)
    issues = []

    if not _check_naming(filename, cache):
        issues.append(
            f"  命名規則違反: '{filename}' はパターン '{cache.get('naming_pattern', '')}' に適合しません"
        )

    if not _check_directory(file_path, cache):
        issues.append(
            f"  配置先違反: '{file_path}' は許可ディレクトリ外です"
        )

    if issues:
        msg = "R-001 配置ルール警告:\n" + "\n".join(issues)
        print(msg, file=sys.stderr)
        if _BLOCK_MODE:
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"[Hook Warning] placement_guard.py error: {e}", file=sys.stderr)
        try:
            from hook_logger import log_hook_error
            log_hook_error("placement_guard.py", e)
        except Exception:
            pass
        sys.exit(0)
