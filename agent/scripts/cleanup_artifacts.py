#!/usr/bin/env python3
"""cleanup_artifacts.py — 一時成果物の機械的削除。

IMP-072: SKILL.md の手順に依存せず、1コマンドで一時成果物を削除する。
/cleanup, /merge スキルから呼び出される。

Usage:
    python3 .claude/scripts/cleanup_artifacts.py [--worktree PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# 削除対象の一時成果物パターン
ARTIFACTS = [
    # セッション状態ファイル
    ("logs/.context-locks", "dir"),
    ("logs/.ssot-impact-declared", "file"),
    ("logs/.workflow-active", "file"),
    ("logs/.workflow-expected", "file"),
    # ランタイムキャッシュ
    ("logs/.placement-rules-cache", "file"),
    ("logs/.agreement-hashes", "file"),
]


def cleanup(claude_dir: Path, worktree: Path | None = None, dry_run: bool = False) -> list[str]:
    """一時成果物を削除し、削除したパスのリストを返す。"""
    deleted: list[str] = []

    # 1. セッション状態ファイル + ランタイムキャッシュ
    for rel_path, kind in ARTIFACTS:
        target = claude_dir / rel_path
        if kind == "dir" and target.is_dir():
            for f in target.iterdir():
                if f.name.startswith("."):
                    continue
                if dry_run:
                    deleted.append(f"[dry-run] {f}")
                else:
                    f.unlink(missing_ok=True)
                    deleted.append(str(f))
        elif kind == "file" and target.exists():
            if dry_run:
                deleted.append(f"[dry-run] {target}")
            else:
                target.unlink(missing_ok=True)
                deleted.append(str(target))

    # 2. work-logs ディレクトリ内のファイル + 対応する worklog-locks（GL-004）
    work_logs = claude_dir / "logs" / "work-logs"
    worklog_locks = claude_dir / "logs" / ".worklog-locks"
    if work_logs.is_dir():
        for wl in work_logs.glob("*.md"):
            if dry_run:
                deleted.append(f"[dry-run] {wl}")
            else:
                wl.unlink(missing_ok=True)
                deleted.append(str(wl))
            # 対応する worklog-lock も削除
            lock = worklog_locks / wl.stem
            if lock.exists():
                if dry_run:
                    deleted.append(f"[dry-run] {lock}")
                else:
                    lock.unlink(missing_ok=True)
                    deleted.append(str(lock))

    # 3. worktree 内の .claude-session-lock
    if worktree and worktree.is_dir():
        lock = worktree / ".claude-session-lock"
        if lock.exists():
            if dry_run:
                deleted.append(f"[dry-run] {lock}")
            else:
                lock.unlink(missing_ok=True)
                deleted.append(str(lock))

    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="一時成果物を削除")
    parser.add_argument("--worktree", type=Path, help="worktree パス")
    parser.add_argument("--dry-run", action="store_true", help="削除せずに対象を表示")
    parser.add_argument(
        "--claude-dir", type=Path, default=None,
        help=".claude ディレクトリのパス（デフォルト: CWD/.claude）",
    )
    args = parser.parse_args()

    claude_dir = args.claude_dir or Path.cwd() / ".claude"
    if not claude_dir.is_dir():
        print(f"エラー: .claude ディレクトリが見つかりません: {claude_dir}", file=sys.stderr)
        return 1

    deleted = cleanup(claude_dir, args.worktree, args.dry_run)

    if deleted:
        print(f"削除{'予定' if args.dry_run else '完了'}: {len(deleted)}件")
        for d in deleted:
            print(f"  {d}")
    else:
        print("削除対象なし")

    return 0


if __name__ == "__main__":
    sys.exit(main())
