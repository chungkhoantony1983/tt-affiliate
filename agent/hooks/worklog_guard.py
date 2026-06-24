#!/usr/bin/env python3
"""GL-004 + GL-009 + GL-011: Work-Log Ownership Guard + Phase Completion Gate + Session ID Verification — PreToolUse hook.

GL-004: Prevents a chat session from writing to a work-log owned by another session.
Each session claims ownership of its work-log by writing its PID to:
    .claude/logs/.worklog-locks/{goal-slug}

GL-011: Session ID based work-log identity verification.
Prevents context compression from causing AI to misidentify work-log ownership.
session_id in work-log frontmatter must match .claude/logs/.session-id.
Session ID immutability is enforced (cannot change existing session_id).

On Write/Edit to .claude/logs/work-logs/*.md or {repo}/docs/**/work-logs/*.md:
  1. Extract the goal-slug from the filename
  2. Check if .worklog-locks/{goal-slug} exists
  3. If it does and PID doesn't match → block (exit 2)
  4. If no lock exists → allow (first write claims it)
  5. GL-011: Verify session_id in frontmatter matches .session-id file

GL-009: Phase Completion Gate — blocks "Phase N 完了" in progress table
if "## Phase N 完了検証" section doesn't exist in the work-log.
Ensures sub-goal status updates and verification evidence are recorded
before declaring Phase completion.

Ownership transfer:
  Writing to .worklog-locks/ itself is always allowed (explicit claim action).
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys

# 1秒タイムアウト（ハング防止）
try:
    signal.alarm(1)
except (AttributeError, ValueError):
    pass


def _get_my_pid() -> str:
    """Get the current session's PID identifier.

    Uses the context-lock PID file if available (consistent with GL-001),
    otherwise falls back to PPID (Claude Code's shell PID).
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        locks_dir = os.path.join(project_dir, ".claude", "logs", ".context-locks")
        if os.path.isdir(locks_dir):
            for fname in os.listdir(locks_dir):
                if fname.startswith("."):
                    continue
                # The filename IS the PID
                return fname
    # Fallback: use PPID
    return str(os.getppid())


def _get_my_session_id(project_dir: str) -> str:
    """Get the current session's session_id from .claude/logs/.session-id."""
    if not project_dir:
        return ""
    sid_file = os.path.join(project_dir, ".claude", "logs", ".session-id")
    try:
        with open(sid_file) as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def _extract_frontmatter_session_id(content: str) -> str:
    """Extract session_id from work-log frontmatter."""
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return ""
    fm = fm_match.group(1)
    sid_match = re.search(r'^session_id:\s*"?([a-f0-9A-F]+)"?', fm, re.MULTILINE)
    return sid_match.group(1) if sid_match else ""


def _check_session_id(
    file_path: str, tool_input: dict, project_dir: str,
) -> tuple[bool, str]:
    """GL-011: Session ID based work-log identity verification.

    Checks:
    1. Immutability: If existing work-log has session_id, it cannot be changed
       to a different value (prevents accidental overwrites after compression).
    2. Ownership: session_id in work-log must match .session-id file.

    Returns (True, "") if OK, (False, error_message) if blocked.
    Backward compatible: skips check if work-log has no session_id field.
    """
    my_sid = _get_my_session_id(project_dir)
    if not my_sid:
        return True, ""  # fail-open: no .session-id file

    # Read existing file content for immutability check
    try:
        with open(file_path, encoding="utf-8") as f:
            existing_content = f.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return True, ""  # New file or unreadable → allow

    existing_sid = _extract_frontmatter_session_id(existing_content)
    if not existing_sid:
        return True, ""  # Backward compat: no session_id in work-log → skip

    # Check ownership: existing session_id must match current session
    if existing_sid != my_sid:
        goal = os.path.basename(file_path)
        return False, (
            f"⚠ GL-011 違反: セッションIDが一致しない work-log への書き込みをブロックしました。\n"
            f"  対象: {goal}\n"
            f"  work-log の session_id: {existing_sid}\n"
            f"  現在セッション ID: {my_sid}\n"
            f"  → この work-log を引き継ぐ場合:\n"
            f"    1. .claude/logs/.worklog-locks/ の所有権を取得\n"
            f"    2. echo {my_sid} > .claude/logs/.session-id で session_id を設定\n"
            f"    3. work-log frontmatter の session_id を {my_sid} に更新"
        )

    # Check immutability: new content must not change session_id to different value
    new_string = tool_input.get("new_string", "")
    content = tool_input.get("content", "")
    text_to_check = content or new_string
    if text_to_check:
        new_sid_match = re.search(
            r'session_id:\s*"?([a-f0-9]+)"?', text_to_check
        )
        if new_sid_match:
            new_sid = new_sid_match.group(1)
            if new_sid != existing_sid:
                return False, (
                    f"⚠ GL-011 違反: work-log の session_id を変更することはできません。\n"
                    f"  既存 session_id: {existing_sid}\n"
                    f"  変更先 session_id: {new_sid}\n"
                    f"  → session_id は不変です。所有権移転は手動で行ってください。"
                )

    return True, ""


def _check_phase_completion_gate(
    file_path: str, tool_input: dict
) -> tuple[bool, str]:
    """GL-009: Phase 完了を作業進捗に記載する前に検証セクションの存在を確認する。

    作業進捗テーブルに「Phase N」+「完了」を含む行を追加しようとした場合、
    同一 work-log に「## Phase N 完了検証」セクションが存在するか検証する。
    未存在ならブロック。
    """
    # Extract the text being added
    new_string = tool_input.get("new_string", "")
    content = tool_input.get("content", "")
    text_to_check = new_string or content
    if not text_to_check:
        return True, ""

    # Detect "Phase N" + "完了" pattern in the text being written
    # Match: "Phase 1 ... 完了" or "Phase1...完了" or "Phase 1...complete"
    phase_pattern = re.compile(
        r"Phase\s*(\d+).*?(?:完了|complete|COMPLETE)", re.IGNORECASE | re.DOTALL
    )
    match = phase_pattern.search(text_to_check)
    if not match:
        return True, ""

    phase_num = match.group(1)

    # Check if this is being written to a progress table (## 作業進捗)
    # Heuristic: progress entries contain "|" table separators
    if "|" not in text_to_check:
        return True, ""  # Not a table entry, allow (might be the verification section itself)

    # Read the current file content
    try:
        with open(file_path, encoding="utf-8") as f:
            current_content = f.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return True, ""  # fail-open

    # For Write tool, check the content being written instead of current file
    if content:
        current_content = content

    # Check for Phase completion verification section
    # Must match: "## Phase N 完了検証" or "### Phase N 完了検証"
    verification_pattern = re.compile(
        rf"##\s*Phase\s*{phase_num}\s*完了検証", re.IGNORECASE
    )
    section_match = verification_pattern.search(current_content)
    if not section_match:
        return False, (
            f"⚠ GL-009 違反: Phase {phase_num} 完了の記載をブロックしました。\n"
            f"  '{file_path}' に '## Phase {phase_num} 完了検証' セクションが存在しません。\n"
            f"  → Phase 完了プロトコル（CLAUDE.md GL-009 参照）に従い、以下を先に実施してください:\n"
            f"    1. Phase {phase_num} の全 sub-goal ステータスを pending から更新\n"
            f"    2. '## Phase {phase_num} 完了検証' セクションを work-log に作成\n"
            f"       （各 sub-goal の検証方法・結果 + 検証エビデンスを記録）\n"
            f"    3. 制約ステータスサマリがあれば影響を受けた項目を更新\n"
            f"    4. 上記完了後に作業進捗に Phase 完了を記載"
        )

    # --- GL-010: Decision Table structure check (BLOCK) ---
    dt_ok, dt_msg = _check_decision_table(current_content, section_match.start(), phase_num)
    if not dt_ok:
        return False, dt_msg

    # --- GL-009 Layer 2: Evidence quality check (warning, not block) ---
    quality_warning = _check_evidence_quality(current_content, section_match.start(), phase_num)
    if quality_warning:
        print(quality_warning, file=sys.stderr)

    return True, ""


def _check_decision_table(
    content: str, section_start: int, phase_num: str,
) -> tuple[bool, str]:
    """GL-010: Phase 完了検証セクション内にデシジョンテーブル構造が存在するか検証する。

    必須構成要素:
      1. シナリオ/前提条件（DT-xxx または シナリオID）
      2. 期待値（具体的な数値。「> 0」は不可）
      3. 実測値/テスト結果
    全て揃っていなければブロック（exit 2）。
    """
    # Extract the verification section content (until next ## heading or EOF)
    next_heading = re.search(r"\n##\s", content[section_start + 1:])
    if next_heading:
        section_text = content[section_start:section_start + 1 + next_heading.start()]
    else:
        section_text = content[section_start:]

    # Check 1: Scenario/precondition structure
    has_scenarios = bool(re.search(
        r"(?:DT[-_]\d|シナリオ\s*ID|シナリオ一覧|前提条件.*?\|)", section_text
    ))

    # Check 2: Expected values (concrete numbers, not just "> 0")
    has_expected = bool(re.search(
        r"期待値", section_text
    ))

    # Check 3: Actual results / judgment
    has_results = bool(re.search(
        r"(?:実測値|テスト結果|判定.*?(?:PASS|FAIL|OK|NG))", section_text
    ))

    # Check 4: Concrete values (not just "> 0" or "存在する")
    has_concrete_values = bool(re.search(
        r"(?:¥[\d,]+|\d+[件行列個]|\d+\.\d+%|[\d,]+円)", section_text
    ))

    # Check 5: Evidence / coverage summary
    has_evidence = bool(re.search(
        r"(?:エビデンス|カバレッジ|Layer\s*[23]|総シナリオ)", section_text
    ))

    if has_scenarios and has_expected and has_results and has_concrete_values:
        return True, ""

    missing = []
    if not has_scenarios:
        missing.append("シナリオ/前提条件（DT-xxx 形式のシナリオ一覧）")
    if not has_expected:
        missing.append("期待値（具体的な数値による期待出力）")
    if not has_results:
        missing.append("実測値/テスト結果（期待値との照合判定）")
    if not has_concrete_values:
        missing.append("具体的な数値（¥金額、件数+単位、比率% — 「> 0」「存在する」は不可）")

    return False, (
        f"⚠ GL-010 違反: Phase {phase_num} 完了検証にデシジョンテーブル構造が不足しています。\n"
        f"  不足要素: {', '.join(missing)}\n"
        f"  → デシジョンテーブル駆動テスト（CLAUDE.md GL-010 参照）に従い、以下を検証セクションに記載してください:\n"
        f"    Step 1: シナリオ一覧（前提条件の組み合わせ）\n"
        f"    Step 2: 各シナリオの期待値（具体的な数値 — 「> 0」は不可）\n"
        f"    Step 3: 実測値と期待値の照合結果（PASS/FAIL）\n"
        f"    Step 4: エビデンス（Layer 2/3 品質基準準拠）"
    )


def _check_evidence_quality(
    content: str, section_start: int, phase_num: str,
) -> str:
    """GL-009 Layer 2: 検証セクション内の証跡品質をチェックする。

    ブロックはせず警告のみ。存在確認だけ（"> 0"、「存在する」）で
    具体的な数値がない場合に警告する。
    """
    # Extract the verification section content (until next ## heading or EOF)
    next_heading = re.search(r"\n##\s", content[section_start + 1:])
    if next_heading:
        section_text = content[section_start:section_start + 1 + next_heading.start()]
    else:
        section_text = content[section_start:]

    warnings = []

    # Check Layer 2: Concrete values (numbers with units, currency, expected vs actual)
    # Look for patterns like: ¥123, 123円, 123件, 123行, 期待値, 実測値
    concrete_value_patterns = [
        r"¥[\d,]+",                    # Currency: ¥12,345
        r"[\d,]+円",                    # Currency: 12,345円
        r"\d+[件行列個]",              # Count with unit: 150行
        r"期待値.*?実測値|実測値.*?期待値",  # Expected vs actual comparison
        r"\d+\.\d+%",                  # Percentage: 30.0%
        r"合計.*?[\d,]+",             # Total with number
    ]
    has_concrete_values = any(
        re.search(p, section_text) for p in concrete_value_patterns
    )

    if not has_concrete_values:
        warnings.append(
            "Layer 2 不足: 検証セクションに具体的な数値（¥金額、件数+単位、期待値vs実測値）が見つかりません。"
            "「> 0」「存在する」だけでは検証として不十分です。"
        )

    # Check Layer 3: Source cross-reference
    source_patterns = [
        r"ソース[突照]合|ソースデータ",
        r"入力.*?出力.*?一致|出力.*?入力.*?一致",
        r"エンドツーエンド",
        r"Layer\s*3",
    ]
    has_source_check = any(
        re.search(p, section_text) for p in source_patterns
    )

    if not has_source_check:
        warnings.append(
            "Layer 3 不足: ソースデータとの突合（エンドツーエンド検証）が見つかりません。"
            "入力→出力の値一致を最低1件検証してください。"
        )

    # Check GL-010: Calculation basis (CALC vs PASS-THRU ratio)
    # Warn if no calculation formulas found (×, ÷, =, 計算式)
    calc_formula_patterns = [
        r"[×÷]",                          # Multiplication/division symbols
        r"\d+\s*[*×]\s*\d+",             # Number × number
        r"計算[式根]拠",                   # Calculation basis marker
        r"CALC",                          # Explicit CALC classification
        r"\d+\s*[/÷]\s*\d+",             # Division
    ]
    has_calc_formulas = any(
        re.search(p, section_text) for p in calc_formula_patterns
    )

    if not has_calc_formulas:
        warnings.append(
            "計算根拠不足（GL-010 パススルー偏重の疑い）: 検証セクションに計算式（×, ÷, 計算根拠）が見つかりません。"
            "入力値をそのまま期待値にコピーする「パススルー検証」は変換ロジックの正しさを検証しません。"
            "期待値は入力値に計算ルールを適用して独立に導出してください。"
        )

    # Check constraint→test traceability (only if constraints exist in the file)
    has_constraints = bool(re.search(r"制約.*?[A-Z]-\d{4}", content))
    if has_constraints:
        constraint_test_patterns = [
            r"制約.*?テスト|テスト.*?制約",
            r"[A-Z]-\d{4}.*?\|",  # Constraint ID in a table
            r"制約→テスト|制約.*?対応",
        ]
        has_constraint_traceability = any(
            re.search(p, section_text) for p in constraint_test_patterns
        )
        if not has_constraint_traceability:
            warnings.append(
                "制約→テスト対応不足: 制約が定義されていますが、検証セクションに制約IDとテスト観点の対応が見つかりません。"
            )

    if not warnings:
        return ""

    return (
        f"⚠ GL-009 品質警告: Phase {phase_num} 完了検証セクションの証跡品質に懸念があります。\n"
        + "\n".join(f"  - {w}" for w in warnings)
        + "\n  → Phase 完了は許可しますが、検証品質の改善を推奨します（CLAUDE.md GL-009 3層エビデンス参照）。"
    )


def _is_worklog_path(file_path: str) -> str | None:
    """Check if the path is a work-log file. Returns goal-slug or None."""
    # Normalize
    norm = os.path.normpath(file_path)

    # Pattern 1: .claude/logs/work-logs/{slug}.md (SSoT work-logs)
    if "/work-logs/" in norm and norm.endswith(".md"):
        basename = os.path.basename(norm)
        return basename[:-3]  # strip .md

    return None


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

    # Allow writes to .worklog-locks/ itself (ownership claim)
    if "/.worklog-locks/" in file_path:
        sys.exit(0)

    # Check if this is a work-log file
    goal_slug = _is_worklog_path(file_path)
    if not goal_slug:
        sys.exit(0)

    # Check ownership
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        sys.exit(0)

    lock_file = os.path.join(
        project_dir, ".claude", "logs", ".worklog-locks", goal_slug
    )

    if not os.path.isfile(lock_file):
        # No lock exists → auto-claim and allow (first writer)
        try:
            os.makedirs(os.path.dirname(lock_file), exist_ok=True)
            my_pid = _get_my_pid()
            with open(lock_file, "w") as f:
                f.write(my_pid + "\n")
        except OSError:
            pass  # fail-open: allow even if lock creation fails
        sys.exit(0)

    try:
        with open(lock_file) as f:
            owner_pid = f.read().strip()
    except (FileNotFoundError, PermissionError):
        sys.exit(0)

    my_pid = _get_my_pid()

    if owner_pid and my_pid and owner_pid != my_pid:
        print(
            f"⚠ GL-004 違反: 他セッションが所有する work-log への書き込みをブロックしました。\n"
            f"  対象: {os.path.basename(file_path)}\n"
            f"  所有セッション PID: {owner_pid}\n"
            f"  現在セッション PID: {my_pid}\n"
            f"  → この work-log を引き継ぐ場合は、まず所有権を取得してください:\n"
            f"    echo {my_pid} > .claude/logs/.worklog-locks/{goal_slug}",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- GL-011: Session ID Verification ---
    sid_ok, sid_msg = _check_session_id(file_path, inp, project_dir)
    if not sid_ok:
        print(sid_msg, file=sys.stderr)
        sys.exit(2)

    # --- GL-009: Phase Completion Gate ---
    phase_ok, phase_msg = _check_phase_completion_gate(file_path, inp)
    if not phase_ok:
        print(phase_msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # フェイルオープン
        print(f"[Hook Warning] worklog_guard.py error: {e}", file=sys.stderr)
        sys.exit(0)
