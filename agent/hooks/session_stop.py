#!/usr/bin/env python3
"""Stop hook: セッション終了時の残存一時成果物検出。

IMP-072: セッション終了時に残存する一時成果物を検出して警告する。
cleanup/merge 未実行の検知にもなる。
"""

import json
import sys
from pathlib import Path


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    cwd = data.get("cwd", "")
    claude_dir = Path(cwd) / ".claude"
    warnings: list[str] = []

    # 1. context-locks 残存チェック
    locks_dir = claude_dir / "logs" / ".context-locks"
    if locks_dir.is_dir():
        locks = [f for f in locks_dir.iterdir() if not f.name.startswith(".")]
        if locks:
            warnings.append(f"context-locks が {len(locks)}件残存")

    # 2. work-logs 残存チェック
    work_logs = claude_dir / "logs" / "work-logs"
    if work_logs.is_dir():
        wl_files = list(work_logs.glob("*.md"))
        if wl_files:
            names = ", ".join(f.stem for f in wl_files[:3])
            suffix = f" 他{len(wl_files)-3}件" if len(wl_files) > 3 else ""
            warnings.append(f"work-log が {len(wl_files)}件残存: {names}{suffix}")

    # 3. ssot-impact-declared 残存チェック
    ssot_declared = claude_dir / "logs" / ".ssot-impact-declared"
    if ssot_declared.exists():
        warnings.append("ssot-impact-declared が残存")

    # 4. placement-rules-cache 残存チェック
    placement = claude_dir / "logs" / ".placement-rules-cache"
    if placement.exists():
        warnings.append("placement-rules-cache が残存")

    # 5. agreement-hashes 残存チェック
    agreement = claude_dir / "logs" / ".agreement-hashes"
    if agreement.exists():
        warnings.append("agreement-hashes が残存")

    if warnings:
        msg = (
            "セッション終了時の残存チェック:\n"
            + "\n".join(f"  - {w}" for w in warnings)
            + "\n→ 次回 /cleanup で削除するか、"
            "python3 .claude/scripts/cleanup_artifacts.py を実行してください。"
        )
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "Stop",
                        "systemMessage": msg,
                    }
                }
            )
        )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
