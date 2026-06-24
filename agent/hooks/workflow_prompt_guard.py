#!/usr/bin/env python3
"""IMP-071: Workflow Prompt Guard — UserPromptSubmit hook.

Detects skill invocations (e.g., /task, /fix) in user prompts and writes
a `.workflow-expected` marker file. This marker is then checked by
workflow_enforce.py to ensure workflow_step.py init was actually called.

Also detects constraint patterns in user prompts (e.g., 「禁止」「必ず」「忘れないで」)
and writes a `.constraint-pending` marker. workflow_enforce.py checks that
the work-log was updated after the constraint was detected before allowing
git commit/push.

Flow (workflow):
  1. User types "/fix some bug" → this hook detects "/fix"
  2. Writes .workflow-expected with domain hint (e.g., "fix")
  3. AI reads SKILL.md and calls workflow_step.py init → creates .workflow-active
  4. workflow_enforce.py checks: if .workflow-expected exists but .workflow-active
     doesn't → blocks git commit/push

Flow (constraint):
  1. User types "〜は禁止" → this hook detects constraint pattern
  2. Writes .constraint-pending with timestamp
  3. AI should update work-log with the constraint
  4. workflow_enforce.py checks: if .constraint-pending exists and work-log
     mtime < marker mtime → blocks git commit/push

Non-infrastructure skills (e.g., /sync) are not matched.
Flow B-only skills (e.g., /ai-task, /ai-learn) write a flow_b_only marker
(IMP-074: context-lock exempt but work-log required).
Non-skill prompts (free text) are not matched (for workflow detection).
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys
import time

# 1秒タイムアウト（ハング防止）
try:
    signal.alarm(1)
except (AttributeError, ValueError):
    pass

# スキル名 → ドメインマッピング
# ステップコントローラー統合済みスキルのみ。
# 新スキル追加時にここに追加する。
_SKILL_DOMAIN_MAP: dict[str, str] = {
    # 統合済み（IMP-071）
    "task": "fix",
    "fix": "fix",
    "spec-update": "spec",
    "push": "ops",
    "comment": "ops",
    "cleanup": "ops",
    "merge": "ops",
    # 統合済み（IMP-071 Phase 2）
    "review": "code-review",
    "re-review": "code-review",
    "survey": "research",
    "test-error": "research",
    "export": "pm-export",
    "issues": "project-mgmt",
    "change-impact": "project-mgmt",
    "pm-planning": "pm-planning",
    "pj-init": "project-mgmt",
}

# IMP-074: Flow B-only スキル（context-lock 免除 but work-log 必須）
# これらのスキルは workflow_step.py init 不要だが、work-log 作成は強制する
_FLOW_B_ONLY_SKILLS: dict[str, str] = {
    "ai-task": "task",         # ドメインルーター
    "ai-learn": "learning",    # SSoT 直接編集
    "ai-slides": "slides",     # スライド生成
    "ai-review": "code-review",
    "ai-fix": "fix",
    "ai-spec-update": "spec",
    "ai-survey": "research",
    "ai-change-impact": "project-mgmt",
    "ai-pm-planning": "pm-planning",
}

# /skill パターン（行頭 or 空白後の /skill_name）
_SKILL_PATTERN = re.compile(
    r"(?:^|(?<=\s))/"
    r"("
    + "|".join(re.escape(s) for s in sorted(_SKILL_DOMAIN_MAP.keys(), key=len, reverse=True))
    + r")"
    r"(?:\s|$)",
)


# ユーザー発言中の制約パターン（日本語）
# 「〜は禁止」「〜しないで」「〜を忘れないで」「必ず〜して」「〜はやめて」等
_CONSTRAINT_PATTERNS = [
    # 日本語パターン（22パターン）
    re.compile(r"禁止"),
    re.compile(r"しないで"),
    re.compile(r"しないこと"),
    re.compile(r"忘れないで"),
    re.compile(r"忘れずに"),
    re.compile(r"必ず.+して"),
    re.compile(r"絶対に"),
    re.compile(r"やめて"),
    re.compile(r"してはいけない"),
    re.compile(r"してはならない"),
    re.compile(r"厳禁"),
    re.compile(r"不可"),
    re.compile(r"変更しない"),
    re.compile(r"触らない"),
    re.compile(r"いじらない"),
    re.compile(r"するな(?:[。！\s]|$)"),      # 命令形否定「〜するな」
    re.compile(r"常に.+して"),                 # 「常に〜して」（必ず と同義）
    re.compile(r"は避けて"),                   # 「〜は避けて」
    re.compile(r"はダメ"),                     # 「〜はダメ」
    re.compile(r"ないように"),                 # 「〜ないように」（予防的制約）
    re.compile(r"今後は.+こと"),               # 「今後は〜すること」（新ルール宣言）
    re.compile(r"を徹底"),                     # 「〜を徹底」（強制的プロセス）
    # 英語パターン（11パターン）
    re.compile(r"\bnever\b", re.IGNORECASE),
    re.compile(r"\bdo\s*n[o']t\b", re.IGNORECASE),
    re.compile(r"\bmust\s+not\b", re.IGNORECASE),
    re.compile(r"\balways\s+\w+", re.IGNORECASE),
    re.compile(r"\bforbidden\b", re.IGNORECASE),
    re.compile(r"\bprohibit", re.IGNORECASE),
    re.compile(r"\bdon't\s+forget\b", re.IGNORECASE),
    re.compile(r"\bnot\s+allowed\b", re.IGNORECASE),
    re.compile(r"\bshould\s*n[o']t\b", re.IGNORECASE),  # shouldn't
    re.compile(r"\bavoid\s+\w+", re.IGNORECASE),         # avoid doing
    re.compile(r"\bstop\s+\w+ing\b", re.IGNORECASE),     # stop doing
]


def _get_marker_path(name: str) -> str:
    """マーカーファイルのパスを返す。"""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return ""
    return os.path.join(project_dir, ".claude", "logs", f".workflow-{name}")


def _has_constraint_pattern(text: str) -> bool:
    """テキストに制約パターンが含まれるか判定する。"""
    for pattern in _CONSTRAINT_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _find_means_locked_work_logs() -> list[str]:
    """[MEANS-LOCKED] を含むオープンな work-log を検索する。"""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return []

    wl_dir = os.path.join(project_dir, ".claude", "logs", "work-logs")
    if not os.path.isdir(wl_dir):
        return []

    locked_logs = []
    try:
        for fname in os.listdir(wl_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(wl_dir, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    content = f.read(8192)  # 先頭8KBで十分
                if "[MEANS-LOCKED]" in content:
                    locked_logs.append(fpath)
            except (FileNotFoundError, PermissionError, UnicodeDecodeError):
                continue
    except OSError:
        pass
    return locked_logs


def _write_constraint_pending(prompt_snippet: str) -> None:
    """制約検知マーカーを書き込む。

    既存のマーカーがあれば制約を追記する（セッション中に複数回検知される場合）。
    S-005: [MEANS-LOCKED] 済み work-log がある場合は手段影響判定を警告する。
    """
    marker_path = _get_marker_path("constraint-pending")
    if not marker_path:
        return

    marker_dir = os.path.dirname(marker_path)
    os.makedirs(marker_dir, exist_ok=True)

    # 既存のマーカーを読み込み（追記モード）
    existing: list[dict] = []
    if os.path.isfile(marker_path):
        try:
            with open(marker_path) as f:
                data = json.load(f)
            if isinstance(data, dict):
                existing = data.get("constraints", [])
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            pass

    # 新しい制約を追加
    snippet = prompt_snippet[:200]  # 長すぎるプロンプトは切り詰め
    existing.append({
        "detected_at": time.time(),
        "snippet": snippet,
    })

    with open(marker_path, "w") as f:
        json.dump({
            "latest_detected_at": time.time(),
            "constraints": existing,
        }, f, ensure_ascii=False)

    # S-005: [MEANS-LOCKED] 済み work-log への手段影響判定を強制警告
    locked_logs = _find_means_locked_work_logs()
    if locked_logs:
        log_names = [os.path.basename(p) for p in locked_logs]
        print(
            f"⚠ S-005 制約影響判定が必要です。\n"
            f"  検知された制約: {snippet[:100]}\n"
            f"  [MEANS-LOCKED] 済み work-log: {', '.join(log_names)}\n"
            f"  → 以下を実施してください:\n"
            f"    1. work-log の「制約追加履歴」に制約を記録する\n"
            f"    2. 構造定義（フローチャート・データ定義）と矛盾がないか判定する\n"
            f"    3. 矛盾がある場合: ユーザーに報告し、構造定義を更新 → 再 approve\n"
            f"    4. 矛盾がない場合: 影響箇所を更新するが、再 approve は不要",
            file=sys.stderr,
        )


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    prompt = data.get("user_prompt", "")
    if not prompt:
        sys.exit(0)

    # --- 制約パターン検知 ---
    if _has_constraint_pattern(prompt):
        _write_constraint_pending(prompt)

    # --- GL-005: ユーザーインタラクションカウント ---
    # .workflow-expected が既に存在する場合、user_interactions をインクリメント。
    # workflow_state_gate.py が偽造防止に使用（resolve承認 + approve承認 = 最低2回）。
    expected_marker = _get_marker_path("expected")
    if expected_marker and os.path.isfile(expected_marker):
        try:
            with open(expected_marker) as f:
                existing_data = json.load(f)
            existing_data["user_interactions"] = existing_data.get("user_interactions", 0) + 1
            with open(expected_marker, "w") as f:
                json.dump(existing_data, f, ensure_ascii=False)
        except (json.JSONDecodeError, OSError, IOError):
            pass  # fail-open

    # --- スキル呼び出し検出 ---
    # Tier 1 スキル（フルワークフロー）
    m = _SKILL_PATTERN.search(prompt)
    if m:
        skill_name = m.group(1)
        domain = _SKILL_DOMAIN_MAP.get(skill_name, "")
        if domain:
            marker_path = _get_marker_path("expected")
            if marker_path:
                marker_dir = os.path.dirname(marker_path)
                os.makedirs(marker_dir, exist_ok=True)
                with open(marker_path, "w") as f:
                    json.dump({"skill": skill_name, "domain": domain}, f)
            sys.exit(0)

    # IMP-074: Flow B-only スキル（/ai-* 系）
    flow_b_match = re.search(
        r"(?:^|(?<=\s))/("
        + "|".join(re.escape(s) for s in sorted(_FLOW_B_ONLY_SKILLS.keys(), key=len, reverse=True))
        + r")(?:\s|$)",
        prompt,
    )
    if flow_b_match:
        skill_name = flow_b_match.group(1)
        domain = _FLOW_B_ONLY_SKILLS.get(skill_name, "")
        if domain:
            marker_path = _get_marker_path("expected")
            if marker_path:
                marker_dir = os.path.dirname(marker_path)
                os.makedirs(marker_dir, exist_ok=True)
                with open(marker_path, "w") as f:
                    json.dump({
                        "skill": skill_name,
                        "domain": domain,
                        "flow_b_only": True,
                    }, f)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # フェイルオープン: hook 自体のエラーでは通過
        print(f"[Hook Warning] workflow_prompt_guard.py error: {e}", file=sys.stderr)
        try:
            from hook_logger import log_hook_error
            log_hook_error("workflow_prompt_guard.py", e)
        except Exception:
            pass
        sys.exit(0)
