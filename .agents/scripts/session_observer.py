#!/usr/bin/env python3
"""Antigravity SessionStart hook wrapper for scripts/branch_observer.py."""
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    # Working directory of hooks.json is .agents/
    repo_root = Path(__file__).resolve().parents[2]
    observer = repo_root / "scripts" / "branch_observer.py"
    if not observer.is_file():
        print("{}")
        return 0

    cwd = payload.get("cwd") or str(repo_root)
    proc = subprocess.run(
        [sys.executable, str(observer), "session"],
        input=json.dumps({"cwd": cwd}),
        capture_output=True,
        text=True,
        timeout=12,
    )
    out = (proc.stdout or "").strip()
    if not out:
        print("{}")
        return 0

    try:
        data = json.loads(out)
        msg = data.get("systemMessage", "")
    except Exception:
        msg = ""

    if msg:
        print(
            json.dumps(
                {
                    "injectSteps": [
                        {
                            "systemMessage": {
                                "systemMessage": msg
                            }
                        }
                    ]
                }
            )
        )
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("{}")
        sys.exit(0)
