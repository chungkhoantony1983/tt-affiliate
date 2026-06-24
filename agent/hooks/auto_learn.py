#!/usr/bin/env python3
"""Stop hook: セッション終了時の自動フィードバック抽出 + 昇格連鎖。

バックグラウンドで実行。learner.py でセッションログからフィードバックを抽出し、
bridge ルールとして保存 → 軽量昇格（hook/constraint/process）を自動実行。

IMP-071 Phase 1: 自動学習パイプライン。
IMP-045: 出自自動キャプチャ — origin_repo / origin_branch を自動付与。
IMP-038: pending-feedback アーカイブ — 10件あふれを退避。
"""
import json
import subprocess
import sys
from pathlib import Path

from _feedback_utils import archive_overflow, detect_branch, detect_origin_repo


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    transcript = data.get("transcript_path", "")
    cwd = data.get("cwd", "")
    if not transcript:
        sys.exit(0)

    # IMP-045: 出自情報を収集
    origin = {
        "origin_repo": detect_origin_repo(cwd),
        "origin_branch": detect_branch(cwd),
        "origin_cwd": cwd,
    }

    pending_path = Path(cwd) / ".claude" / "logs" / ".pending-feedback.json"
    pending_path.parent.mkdir(parents=True, exist_ok=True)

    # === Step 1: フィードバック抽出（既存） ===
    feedbacks_extracted = False
    try:
        result = subprocess.run(
            [
                "python3", "-m", "automation_engine", "preset", "learn",
                "--session", transcript, "--dry-run", "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            feedback = json.loads(result.stdout)
            if feedback.get("count", 0) > 0:
                feedbacks_extracted = True
                _merge_and_save_feedbacks(
                    pending_path, feedback, origin,
                )
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass  # フェイルサイレント

    # === Step 2: bridge 自動保存（IMP-071 Phase 1） ===
    if feedbacks_extracted:
        try:
            subprocess.run(
                [
                    "python3", "-m", "automation_engine", "preset", "learn",
                    "--session", transcript, "--auto",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # bridge 保存失敗は silent

    # === Step 3: 軽量昇格（IMP-071 Phase 1） ===
    # hook/constraint/process のみ自動実行。phase は手動 /ai-learn が必要。
    try:
        subprocess.run(
            [
                "python3", "-m", "automation_engine", "preset", "promote",
                "--auto",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # 昇格失敗は silent（bridge が残るだけ）

    sys.exit(0)


def _merge_and_save_feedbacks(
    pending_path: Path,
    feedback: dict,
    origin: dict,
) -> None:
    """フィードバックを既存データとマージして保存。"""
    # 既存のフィードバックとマージ
    existing: list = []
    if pending_path.exists():
        try:
            existing = json.loads(pending_path.read_text()).get(
                "feedbacks", []
            )
        except (json.JSONDecodeError, KeyError):
            existing = []

    # IMP-026: 重複排除（同一テキストは除外）
    new_items = feedback.get("feedbacks", [])
    existing_texts = {item.get("text", "") for item in existing}
    deduped = [
        item for item in new_items
        if item.get("text", "") not in existing_texts
    ]

    # IMP-045: 出自情報を各フィードバックに付与
    for fb in deduped:
        if "origin" not in fb:
            fb["origin"] = origin

    all_feedbacks = deduped + existing

    # IMP-038: あふれをアーカイブに退避
    archive_overflow(pending_path, all_feedbacks[10:])

    feedback["feedbacks"] = all_feedbacks[:10]
    feedback["count"] = len(feedback["feedbacks"])
    pending_path.write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
