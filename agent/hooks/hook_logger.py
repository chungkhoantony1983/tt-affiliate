"""Hook 共通エラーログユーティリティ。

全 hook のフェイルオープン例外を永続ログに記録する。
stderr 出力だけではセッション終了後に消えるため、
.claude/logs/.hook-errors.log にも追記する。

ログローテーション: 100KB 超で自動切り詰め（最新50行を残す）。
"""
from __future__ import annotations

import os
import time
import traceback


def log_hook_error(hook_name: str, error: Exception) -> None:
    """hook エラーを永続ログに記録する。

    Args:
        hook_name: hook ファイル名（例: "workflow_enforce.py"）
        error: 発生した例外
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return

    log_dir = os.path.join(project_dir, ".claude", "logs")
    log_path = os.path.join(log_dir, ".hook-errors.log")

    try:
        os.makedirs(log_dir, exist_ok=True)

        # ログローテーション（100KB 超で切り詰め）
        try:
            if os.path.isfile(log_path) and os.path.getsize(log_path) > 100_000:
                with open(log_path) as f:
                    lines = f.readlines()
                with open(log_path, "w") as f:
                    f.writelines(lines[-50:])
        except (OSError, PermissionError):
            pass

        # エラーログ追記
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb_str = "".join(tb).strip()

        with open(log_path, "a") as f:
            f.write(f"[{timestamp}] {hook_name}: {error}\n")
            f.write(f"  {tb_str}\n\n")

    except (OSError, PermissionError):
        pass  # ログ書き込み自体が失敗してもフェイルオープン
