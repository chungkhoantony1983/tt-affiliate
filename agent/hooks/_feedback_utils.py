"""Shared utilities for auto_learn.py and auto_learn_lite.py.

Extracted to eliminate code duplication (IMP Phase 1, item #1).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def detect_origin_repo(cwd: str) -> str | None:
    """CWD から git remote を解析してリポ名を取得。"""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            return url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def detect_branch(cwd: str) -> str | None:
    """CWD のカレントブランチを取得。"""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def archive_overflow(pending_path: Path, overflow: list) -> None:
    """IMP-038: 10件あふれを archive に退避。"""
    if not overflow:
        return
    archive_path = pending_path.with_name(".pending-feedback-archive.json")
    archive: list = []
    if archive_path.exists():
        try:
            archive = json.loads(archive_path.read_text()).get("feedbacks", [])
        except (json.JSONDecodeError, KeyError):
            archive = []
    archive = overflow + archive
    archive_path.write_text(json.dumps(
        {"feedbacks": archive[:100], "count": min(len(archive), 100)},
        ensure_ascii=False, indent=2,
    ))
