#!/usr/bin/env python3
"""IMP-044: CLI不要のlightweight版フィードバック検出。

platform CLIがない環境（リポ単体）のStop Hookとして動作。
regex パターンでフィードバックを検出し、.pending-feedback.json に保存。

IMP-045 統合: origin_repo / origin_branch / 会話コンテキスト(±5ターン)を自動キャプチャ。
IMP-038 統合: 10件あふれを archive に退避。

精度ゲート: テストコーパスで precision >= 80% を検証してから配備すること。
"""
import json
import re
import sys
from pathlib import Path

from _feedback_utils import archive_overflow, detect_branch, detect_origin_repo

# フィードバック検出パターン（カテゴリ付き）
FEEDBACK_PATTERNS: list[tuple[str, str]] = [
    (r"(?:修正|変更|直|やり直)し(?:て|ろ|なさい)", "fix"),
    (r"(?:ではな(?:い|く)|じゃな(?:い|く)|違(?:う|い))", "correction"),
    (r"(?:横展開|他にも|同様の|同じ問題)", "lateral"),
    (r"(?:必ず|絶対に|常に|全て)(?:.{1,20})(?:して|する)", "mandatory"),
    (r"(?:デグレ|リグレ|壊れ|消え|なくな|失われ)", "regression"),
    (r"(?:間違|誤|エラー|error|wrong|incorrect)", "error"),
    (r"(?:再発|繰り返|また同じ|前も)", "recurring"),
    (r"(?:禁止|しないで|するな|やめて|使わないで)", "prohibition"),
    (r"(?:今後は|以降は|次回から)(?:.{1,20})(?:して|する|こと|ように)", "future_rule"),
]

# コンテキストウィンドウ: 前後何ターンの会話を保存するか
CONTEXT_WINDOW = 5

# システムメタデータ除外パターン
_NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p)
    for p in [
        r"^This session is being continued",
        r"^<ide_opened_file>",
        r"^<ide_selection>",
        r"^<task-notification>",
        r"^Base directory for this skill:",
        r"^### Step 0:",
        r"^Note: .+ was read before",
    ]
]


def _is_noise(text: str) -> bool:
    """システムメタデータやセッション継続要約を検知。"""
    return any(p.search(text) for p in _NOISE_PATTERNS)


def _extract_user_messages(log_path: Path) -> list[tuple[int, str]]:
    """セッションログからユーザーメッセージを抽出。"""
    messages: list[tuple[int, str]] = []
    idx = 0
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "user":
                continue
            msg = obj.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, list):
                texts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                text = " ".join(texts)
            elif isinstance(content, str):
                text = content
            else:
                text = str(content)
            text = text.strip()
            if text:
                messages.append((idx, text))
                idx += 1
    return messages


def _detect_feedback(
    messages: list[tuple[int, str]],
) -> list[dict]:
    """メッセージリストからフィードバックを検出（コンテキスト付き）。"""
    feedbacks: list[dict] = []
    compiled = [(re.compile(p), cat) for p, cat in FEEDBACK_PATTERNS]

    for i, (idx, text) in enumerate(messages):
        if len(text) < 10:
            continue
        if _is_noise(text):
            continue

        matched = [(cat, pat.pattern[:40]) for pat, cat in compiled if pat.search(text)]
        if not matched:
            continue

        # 前後 ±CONTEXT_WINDOW ターンのコンテキストを保存 (REQ-15)
        start = max(0, i - CONTEXT_WINDOW)
        end = min(len(messages), i + CONTEXT_WINDOW + 1)
        context_messages = [
            {"index": m[0], "text": m[1][:300]}
            for m in messages[start:end]
        ]

        feedbacks.append({
            "text": text[:200],
            "categories": list({cat for cat, _ in matched}),
            "pattern_count": len(matched),
            "context": context_messages,
        })

    return feedbacks


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    transcript = data.get("transcript_path", "")
    cwd = data.get("cwd", "")
    if not transcript or not Path(transcript).exists():
        sys.exit(0)

    # platform CLI が利用可能なら auto_learn.py に委譲（重複検出を防止）
    import importlib.util
    if importlib.util.find_spec("automation_engine") is not None:
        sys.exit(0)

    # セッションログからユーザーメッセージを抽出
    messages = _extract_user_messages(Path(transcript))
    if not messages:
        sys.exit(0)

    # フィードバック検出
    feedbacks = _detect_feedback(messages)
    if not feedbacks:
        sys.exit(0)

    # IMP-045: 出自情報の自動キャプチャ
    origin = {
        "origin_repo": detect_origin_repo(cwd),
        "origin_branch": detect_branch(cwd),
        "origin_cwd": cwd,
    }
    for fb in feedbacks:
        fb["origin"] = origin

    # pending-feedback.json に保存
    pending_path = Path(cwd) / ".claude" / "logs" / ".pending-feedback.json"
    pending_path.parent.mkdir(parents=True, exist_ok=True)

    existing: list = []
    if pending_path.exists():
        try:
            existing = json.loads(pending_path.read_text()).get("feedbacks", [])
        except (json.JSONDecodeError, KeyError):
            existing = []

    # 重複排除
    existing_texts = {item.get("text", "") for item in existing}
    deduped = [f for f in feedbacks if f["text"] not in existing_texts]

    all_feedbacks = deduped + existing

    # IMP-038: あふれをアーカイブに退避
    archive_overflow(pending_path, all_feedbacks[10:])

    pending_path.write_text(json.dumps(
        {"feedbacks": all_feedbacks[:10], "count": min(len(all_feedbacks), 10)},
        ensure_ascii=False, indent=2,
    ))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
