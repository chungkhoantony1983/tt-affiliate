#!/usr/bin/env python3
"""IMP-071: Workflow Phase Enforcement — PreToolUse hook.

Prevents git commit/push/gh pr operations when workflow phases are incomplete.
Also enforces Git safety rules (S-001~S-003):
  - S-001: Block git push to base branches (main/master/development)
  - S-002: Block git checkout/switch in repo root (must use worktree)
  - S-003: Block git worktree add without -b (detached HEAD prevention)

This is the enforcement layer that makes workflow_step.py mandatory rather than
voluntary.

How it works:
  1. workflow_prompt_guard.py (UserPromptSubmit) detects /skill invocations
     and writes .workflow-expected with domain hint.
  2. workflow_step.py init writes .workflow-active with state.json path.
  3. This hook fires on Bash commands containing git commit/push/gh pr.
  4. Enforcement checks:
     S-001. git push to main/master/development → block (must use PR)
     S-002. git checkout/switch in repo root → block (must use worktree)
     S-003. git worktree add without -b → block (detached HEAD prevention)
     a. .workflow-expected exists AND .workflow-active missing
        → AI skipped init → block
     b. .workflow-active exists AND phases incomplete
        → phases not done → block
     c. Neither marker exists → pass (non-skill execution)
     d. git push + ssot_impact declared → verify SSoT files changed (block)
     e. .workflow-active exists AND work-log missing → block
     f. git commit/push + .constraint-pending exists → verify work-log updated (block)
     g. git push + ssot_impact="none" BUT diff contains SSoT files → block (undeclared)
     h. git push + code-review domain → verify 3 consecutive review passes (block)
     i. git push + review phase completed → verify files_read covers git diff (block)
     j. git push + lateral-check completed → verify grep patterns have non-zero hits (block)
     k. git push + code-review discuss completed → verify dismiss integrity (block)
     l. git push + review completed → verify files_read has line count info (block)
     m. git push + work-log has done subgoals → verify [VERIFIED] markers (block)
     n. git push + ssot_impact != none → verify .agreement-hashes non-empty (block)

Markers are deleted when:
  - .workflow-active: workflow_step.py advance returns status: "done"
  - .workflow-expected: cleaned up alongside .workflow-active on completion
  - Session ends (C-IMP071-4: state.json deleted on session end)
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time

# 1秒タイムアウト（ハング防止）
try:
    signal.alarm(1)
except (AttributeError, ValueError):
    pass

# git commit/push/gh pr を検出するパターン
_GATE_PATTERNS = [
    re.compile(r"\bgit\b.*\bcommit\b"),
    re.compile(r"\bgit\b.*\bpush\b"),
    re.compile(r"\bgh\b.*\bpr\b.*\bcreate\b"),
    re.compile(r"\bgh\b.*\bpr\b.*\bmerge\b"),
]

# 安全なコマンド（ブロック対象外）
_SAFE_PATTERNS = [
    re.compile(r"\bgit\b.*\bcommit\b.*--allow-empty-message"),  # hook テスト用
    re.compile(r"\bgit\b.*\bpush\b.*--dry-run"),
]

# S-001: ベースブランチへの直push検出パターン
_BASE_BRANCHES = {"main", "master", "development"}

# S-002: リポ本体での checkout/switch 検出パターン
_CHECKOUT_PATTERNS = [
    re.compile(r"\bgit\s+checkout\b(?!\s+--\s)(?!\s+-b\b)"),
    re.compile(r"\bgit\s+switch\b(?!\s+-c\b)"),
]

# S-003: detached HEAD worktree 検出（-b なしの worktree add）
_WORKTREE_ADD_PATTERN = re.compile(r"\bgit\b.*\bworktree\s+add\b")
_WORKTREE_ADD_WITH_BRANCH = re.compile(r"\bgit\b.*\bworktree\s+add\b.*\s-b\s")


def _check_git_safety(cmd: str) -> tuple[bool, str]:
    """S-001~S-003: Git操作の安全弁チェック。

    ワークフロー状態に関係なく、全 Bash コマンドで実行される。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    # S-001: ベースブランチへの直push検出
    push_match = re.search(r"\bgit\b.*\bpush\b", cmd)
    if push_match:
        # "git push origin main", "git push origin main:main" 等を検出
        # ただし "git push -u origin feat/xxx" は許可
        for branch in _BASE_BRANCHES:
            # パターン: push ... {branch}, push ... origin {branch}
            if re.search(
                rf"\bgit\b.*\bpush\b.*\b{branch}\b", cmd
            ):
                # "--delete" は除外（ブランチ削除は別問題）
                if "--delete" not in cmd and "-d" not in cmd.split():
                    return False, (
                        f"⚠ S-001 違反: ベースブランチ '{branch}' への直接 push は禁止です。\n"
                        f"  コマンド: {cmd}\n"
                        f"  → 必ず PR 経由で変更を反映してください。\n"
                        f"  → git push -u origin {{feature-branch}} でフィーチャーブランチを push し、\n"
                        f"    gh pr create で PR を作成してください。"
                    )

    # S-002: リポ本体での git checkout/switch 検出
    # worktree 内からの checkout は許可（パス文脈で判定）
    for pattern in _CHECKOUT_PATTERNS:
        if pattern.search(cmd):
            # "git -C {worktree} checkout" は許可
            if re.search(r"\bgit\s+-C\s+\S*\.worktrees?\S*", cmd):
                continue
            # "git checkout -- file" (ファイル復元) は許可
            if re.search(r"\bgit\s+checkout\s+--\s", cmd):
                continue
            # ブランチ切り替え目的の checkout/switch を検出
            return False, (
                f"⚠ S-002 違反: リポジトリ本体での git checkout/switch は禁止です。\n"
                f"  コマンド: {cmd}\n"
                f"  → worktree を使用してください:\n"
                f"    git worktree add .worktrees/{{name}} -b {{branch}} origin/main"
            )

    # S-003: detached HEAD worktree 作成検出
    if _WORKTREE_ADD_PATTERN.search(cmd):
        if not _WORKTREE_ADD_WITH_BRANCH.search(cmd):
            # "git worktree add path origin/branch" は detached HEAD ではない
            # （リモートトラッキングブランチからのローカルブランチ自動作成）
            # ただし "git worktree add path HEAD" や "git worktree add path {hash}" はNG
            # 安全パターン: "origin/" を含む場合はリモート追跡 → 許可
            if "origin/" in cmd:
                pass  # リモートブランチからのworktree作成は許可
            else:
                return False, (
                    f"⚠ S-003 違反: detached HEAD での worktree 作成は禁止です。\n"
                    f"  コマンド: {cmd}\n"
                    f"  → -b オプションでブランチを指定してください:\n"
                    f"    git worktree add {{path}} -b {{branch}} origin/main\n"
                    f"  → 既存リモートブランチの場合:\n"
                    f"    git worktree add {{path}} origin/{{branch}}"
                )

    return True, ""


def _get_marker_path(name: str = "active") -> str:
    """マーカーファイルのパスを返す。"""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return ""
    return os.path.join(project_dir, ".claude", "logs", f".workflow-{name}")


def _read_workflow_state() -> dict | None:
    """アクティブなワークフロー状態を読み込む。

    Returns:
        state dict or None (マーカー/状態ファイルが存在しない場合)
    """
    marker_path = _get_marker_path("active")
    if not marker_path or not os.path.isfile(marker_path):
        return None

    try:
        with open(marker_path) as f:
            state_file = f.read().strip()
    except (FileNotFoundError, PermissionError):
        return None

    if not state_file or not os.path.isfile(state_file):
        # state.json が削除済み（セッション終了等）→ マーカーも掃除
        try:
            os.remove(marker_path)
        except OSError:
            pass
        return None

    try:
        with open(state_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return None


def _is_gate_command(cmd: str) -> bool:
    """コマンドがゲート対象（git commit/push 等）か判定する。"""
    # 安全なコマンドは除外
    for pattern in _SAFE_PATTERNS:
        if pattern.search(cmd):
            return False

    for pattern in _GATE_PATTERNS:
        if pattern.search(cmd):
            return True
    return False


def _check_workflow_complete(state: dict) -> tuple[bool, str]:
    """ワークフローが完了しているかチェックする。

    Returns:
        (is_complete, message)
    """
    phases = state.get("workflow_phases", [])
    current_idx = state.get("current_phase_index", 0)
    prereq_done = state.get("prereq_done", False)
    config_loaded = state.get("config_loaded", False)
    domain = state.get("domain", "unknown")

    if not config_loaded:
        return False, (
            f"ドメイン '{domain}' の設定読み込み（config_loaded）が未完了です。\n"
            f"  workflow_step.py init が teams.yaml + learned-rules.yaml を\n"
            f"  読み込んでいない状態です。init を再実行してください。"
        )

    if not prereq_done:
        return False, (
            f"ドメイン '{domain}' の前提ステップ（prereq）が未完了です。\n"
            f"  → python .claude/scripts/workflow_step.py prereq-done --state {{state_file}} を実行してください。"
        )

    if current_idx < len(phases):
        completed = phases[:current_idx]
        remaining = phases[current_idx:]
        return False, (
            f"ドメイン '{domain}' のワークフローが未完了です。\n"
            f"  完了済み: {completed or '（なし）'}\n"
            f"  未完了:   {remaining}\n"
            f"  現在:     {remaining[0]}（{current_idx + 1}/{len(phases)}）\n"
            f"  → 各フェーズを advance で完了させてからコミット/プッシュしてください。"
        )

    return True, ""


def _is_push_command(cmd: str) -> bool:
    """git push コマンドか判定する。"""
    return bool(re.search(r"\bgit\b.*\bpush\b", cmd))


def _check_ssot_impact_fulfilled(state: dict) -> tuple[bool, str]:
    """ssot_impact で宣言された SSoT ファイルが実際に変更されているか検証する。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    ssot_impact = state.get("ssot_impact", "none")
    if not ssot_impact or ssot_impact == "none":
        return True, ""

    # ssot_impact からファイル名を抽出（カンマ区切りまたは YAML リスト形式）
    files = [
        f.strip().strip("[]\"'")
        for f in re.split(r"[,\n]", ssot_impact)
        if f.strip() and f.strip() not in ("none", "-")
    ]
    if not files:
        return True, ""

    # git diff で変更ファイルを取得（0.5秒タイムアウト）
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=0.5,
        )
        changed = set(result.stdout.strip().splitlines()) if result.returncode == 0 else set()
        # staged も確認
        result2 = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=0.5,
        )
        if result2.returncode == 0:
            changed |= set(result2.stdout.strip().splitlines())
        # コミット済みの変更も確認（origin/main..HEAD）
        result3 = subprocess.run(
            ["git", "log", "--name-only", "--pretty=format:", "origin/main..HEAD"],
            capture_output=True, text=True, timeout=0.5,
        )
        if result3.returncode == 0:
            changed |= set(
                line for line in result3.stdout.strip().splitlines() if line.strip()
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return True, ""  # タイムアウト時はフェイルオープン

    # 宣言ファイルと変更ファイルを照合
    missing = []
    for f in files:
        # パス末尾マッチ（相対パス / ファイル名のみ の両方に対応）
        found = any(c.endswith(f) or f.endswith(c) for c in changed)
        if not found:
            missing.append(f)

    if missing:
        return False, (
            f"ssot_impact で宣言された SSoT ファイルが変更されていません:\n"
            f"  未変更: {', '.join(missing)}\n"
            f"  宣言値: {ssot_impact}\n"
            f"  → 宣言した SSoT ファイルを更新してから push してください。\n"
            f"  → SSoT 変更が不要になった場合は resolve に戻って ssot_impact を更新してください。"
        )

    return True, ""


def _check_work_log_exists(state: dict) -> tuple[bool, str]:
    """work-log の存在を検証する。

    スキル実行中（workflow-active あり）に commit/push しようとした場合、
    work-log が存在しなければブロックする。
    work-log はセッションの目的・制約・進捗を記録する必須文書。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    wl_path = state.get("work_log_path", "")
    domain = state.get("domain", "unknown")

    if wl_path and os.path.isfile(wl_path):
        return True, ""

    # work-log パスが state にない場合、work-logs/ ディレクトリを探索
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        wl_dir = os.path.join(project_dir, ".claude", "logs", "work-logs")
        if os.path.isdir(wl_dir):
            wl_files = [f for f in os.listdir(wl_dir) if f.endswith(".md")]
            if wl_files:
                return True, ""  # いずれかの work-log が存在すればOK

    return False, (
        f"ドメイン '{domain}' のワークフロー実行中ですが、work-log が見つかりません。\n"
        f"  work-log はセッションの統合目的・制約・進捗を記録する必須文書です。\n"
        f"  → CLAUDE.md Step 7（resolve）に従い、work-log を作成してからコミットしてください。\n"
        f"  → 配置先: .claude/logs/work-logs/{{goal-slug}}.md"
    )


def _check_constraint_acknowledged(state: dict) -> tuple[bool, str]:
    """制約検知マーカーと work-log の更新状態を構造的に検証する。

    workflow_prompt_guard.py が UserPromptSubmit で制約パターン（「禁止」「必ず」等）を
    検知すると `.constraint-pending` マーカーを書き込む。このチェックは:
      - マーカーが存在しない → OK（制約検知なし）
      - マーカーが存在 + work-log の mtime がマーカーの検知時刻より後 → OK（反映済み）
      - マーカーが存在 + work-log の mtime がマーカーの検知時刻より前 → BLOCK

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return True, ""

    marker_path = os.path.join(
        project_dir, ".claude", "logs", ".workflow-constraint-pending",
    )
    if not os.path.isfile(marker_path):
        return True, ""

    # マーカーを読み込み
    try:
        with open(marker_path) as f:
            marker_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return True, ""  # フェイルオープン

    latest_detected = marker_data.get("latest_detected_at", 0)
    if not latest_detected:
        return True, ""

    # work-log の mtime を確認
    wl_path = state.get("work_log_path", "")
    if not wl_path or not os.path.isfile(wl_path):
        # work-log 自体がない場合もブロック（制約を記録する場所がない）
        constraints = marker_data.get("constraints", [])
        snippets = [c.get("snippet", "")[:80] for c in constraints[-3:]]
        return False, (
            f"セッション中に制約が検知されましたが、work-log が見つかりません。\n"
            f"  検知された制約（直近）:\n"
            + "\n".join(f"    - {s}" for s in snippets)
            + f"\n  → work-log を作成し、制約を記録してからコミットしてください。"
        )

    try:
        wl_mtime = os.path.getmtime(wl_path)
    except OSError:
        return True, ""  # フェイルオープン

    if wl_mtime >= latest_detected:
        # work-log がマーカーより後に更新されている → OK
        return True, ""

    # work-log が制約検知後に更新されていない → BLOCK
    constraints = marker_data.get("constraints", [])
    snippets = [c.get("snippet", "")[:80] for c in constraints[-3:]]
    return False, (
        f"セッション中にユーザーから制約が追加されましたが、work-log に反映されていません。\n"
        f"  検知された制約（直近）:\n"
        + "\n".join(f"    - {s}" for s in snippets)
        + f"\n  work-log: {wl_path}\n"
        f"  → work-log の「制約追加履歴」セクションに制約を記録してからコミットしてください。"
    )


def _load_ssot_patterns() -> list:
    """ssot-file-patterns.json から SSoT ファイルパターンを動的読み込み。

    パターン定義は .claude/references/config/ssot-file-patterns.json（sync で全リポに配信）。
    ファイル不在・パースエラー時はフェイルオープン（空リスト → Check g スキップ）。
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return []

    patterns_path = os.path.join(
        project_dir, ".claude", "references", "config", "ssot-file-patterns.json",
    )
    try:
        with open(patterns_path) as f:
            data = json.load(f)
        raw_patterns = data.get("patterns", [])
        exclude_patterns = data.get("exclude", [])
        compiled = []
        for p in raw_patterns:
            compiled.append(("include", re.compile(p)))
        for p in exclude_patterns:
            compiled.append(("exclude", re.compile(p)))
        return compiled
    except (FileNotFoundError, json.JSONDecodeError, PermissionError, re.error):
        return []  # フェイルオープン


def _check_ssot_undeclared_changes(state: dict) -> tuple[bool, str]:
    """ssot_impact="none" だが diff に SSoT ファイルが含まれている場合をブロック。

    push 時に git diff から変更ファイルを取得し、SSoT パターンに一致するものがあれば
    ssot_impact の宣言漏れとして検出する。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    ssot_impact = state.get("ssot_impact", "none")
    if ssot_impact and ssot_impact != "none":
        return True, ""  # 既に宣言済み → Check d で検証済み

    # git diff で変更ファイルを取得
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=0.5,
        )
        changed = set(result.stdout.strip().splitlines()) if result.returncode == 0 else set()
        result2 = subprocess.run(
            ["git", "log", "--name-only", "--pretty=format:", "origin/main..HEAD"],
            capture_output=True, text=True, timeout=0.5,
        )
        if result2.returncode == 0:
            changed |= set(
                line for line in result2.stdout.strip().splitlines() if line.strip()
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return True, ""  # フェイルオープン

    if not changed:
        return True, ""

    # SSoT パターン: ssot-file-patterns.json から動的読み込み
    ssot_patterns = _load_ssot_patterns()

    detected_ssot = []
    for f in changed:
        is_ssot = False
        for kind, pattern in ssot_patterns:
            if kind == "include" and pattern.search(f):
                is_ssot = True
            elif kind == "exclude" and pattern.search(f):
                is_ssot = False
                break  # exclude が優先
        if is_ssot:
            detected_ssot.append(f)

    if not detected_ssot:
        return True, ""

    return False, (
        f"ssot_impact が 'none' ですが、SSoT ファイルが変更されています:\n"
        f"  検出ファイル:\n"
        + "\n".join(f"    - {f}" for f in detected_ssot[:10])
        + f"\n  → resolve に戻り ssot_impact を更新してから push してください。\n"
        f"  → SSoT 変更が意図的な場合: work-log の ssot_impact を更新し prereq-done を再実行。"
    )


def _check_review_convergence(state: dict) -> tuple[bool, str]:
    """code-review ドメインでの3連続パス収束判定。

    .review-cycle-state.json を読み込み、連続パス数が3未満ならブロック。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    domain = state.get("domain", "")
    if domain != "code-review":
        return True, ""

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return True, ""

    cycle_path = os.path.join(
        project_dir, ".claude", "logs", ".review-cycle-state.json",
    )
    if not os.path.isfile(cycle_path):
        return False, (
            "code-review ドメインですが、レビューサイクル記録がありません。\n"
            "  → /ai-review で最低3サイクル連続全軸 Pass を達成してから push してください。\n"
            "  → workflow_step.py record-review-cycle で結果を記録してください。"
        )

    try:
        with open(cycle_path) as f:
            cycle_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return True, ""  # フェイルオープン

    consecutive = cycle_data.get("consecutive_passes", 0)
    required = cycle_data.get("required_passes", 3)

    if consecutive >= required:
        return True, ""

    history = cycle_data.get("history", [])
    recent = history[-5:] if history else []
    history_parts = []
    for h in recent:
        label = "PASS" if h.get("pass") else f"FAIL({h.get('findings', '?')})"
        cycle = h.get("cycle", "?")
        history_parts.append(f"{label}({cycle})")
    history_str = " → ".join(history_parts) or "（記録なし）"

    return False, (
        f"code-review の収束条件（3サイクル連続全軸 Pass — RV-001）を満たしていません。\n"
        f"  現在の連続パス: {consecutive}/{required}\n"
        f"  直近履歴: {history_str}\n"
        f"  → /ai-review を実行し、指摘がゼロになるまでレビュー/修正を繰り返してください。"
    )


def _check_review_evidence_integrity(state: dict) -> tuple[bool, str]:
    """review フェーズの files_read 証跡と git diff の突合検証。

    review フェーズが完了している場合、提出された files_read リストが
    git diff --name-only の変更ファイルを全てカバーしているかを検証する。
    カバレッジ不足があれば push をブロックする。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    # review フェーズの結果を取得
    context = state.get("context", {})
    review_result = context.get("phase_review_result")
    if not review_result:
        return True, ""  # review フェーズ未完了または未実行 → パス

    files_read_raw = review_result.get("files_read", "")
    if not files_read_raw:
        return True, ""  # files_read 自体は gate で検証済み

    # git diff で変更ファイル一覧を取得
    try:
        result = subprocess.run(
            ["git", "log", "--name-only", "--pretty=format:", "origin/main..HEAD"],
            capture_output=True, text=True, timeout=0.5,
        )
        if result.returncode != 0:
            return True, ""  # フェイルオープン

        diff_files = set(
            line.strip()
            for line in result.stdout.strip().splitlines()
            if line.strip()
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return True, ""  # フェイルオープン

    if not diff_files:
        return True, ""

    # files_read を正規化（文字列 or リスト対応）
    if isinstance(files_read_raw, list):
        files_read_entries = files_read_raw
    else:
        # 文字列の場合: 改行・カンマ区切りを分割
        files_read_entries = re.split(r"[\n,]", str(files_read_raw))

    # ファイル名部分を抽出（"path/to/file.py:123行" → "path/to/file.py"）
    files_read_normalized = set()
    for entry in files_read_entries:
        cleaned = entry.strip().strip("-・ ")
        if not cleaned:
            continue
        # "filename:行数" や "filename (123行)" パターンからファイル名を抽出
        fname = re.split(r"[:(\s]", cleaned)[0].strip()
        if fname:
            files_read_normalized.add(fname)

    # diff ファイルが files_read でカバーされているか検証
    uncovered = []
    for df in diff_files:
        # 完全一致 or 末尾一致（相対パス対応）
        covered = any(
            df == fr or df.endswith(fr) or fr.endswith(df)
            for fr in files_read_normalized
        )
        if not covered:
            uncovered.append(df)

    if not uncovered:
        return True, ""

    coverage_pct = ((len(diff_files) - len(uncovered)) / len(diff_files)) * 100

    return False, (
        f"review フェーズの files_read 証跡が git diff をカバーしていません（Check i）。\n"
        f"  カバレッジ: {coverage_pct:.0f}% ({len(diff_files) - len(uncovered)}/{len(diff_files)})\n"
        f"  未カバーファイル:\n"
        + "\n".join(f"    - {f}" for f in uncovered[:15])
        + (f"\n    ... 他 {len(uncovered) - 15} ファイル" if len(uncovered) > 15 else "")
        + f"\n  → review フェーズで全変更ファイルを Read ツールで読み込んでから push してください。"
    )


def _check_files_read_depth(state: dict) -> tuple[bool, str]:
    """review フェーズの files_read 証跡に行数情報が含まれるか検証（Check l）。

    Read ツールで実際にファイルを読んだ場合、行数情報（":123行" や "(456行)"）
    が含まれるはず。全エントリに行数情報がない場合、ファイル名だけ列挙した
    「読んだフリ」の可能性が高いとして警告する。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    context = state.get("context", {})
    review_result = context.get("phase_review_result")
    if not review_result:
        return True, ""

    files_read_raw = review_result.get("files_read", "")
    if not files_read_raw:
        return True, ""

    # files_read をエントリに分割
    if isinstance(files_read_raw, list):
        entries = files_read_raw
    else:
        entries = re.split(r"[\n,]", str(files_read_raw))

    entries = [e.strip() for e in entries if e.strip()]
    if not entries:
        return True, ""

    # 行数情報のパターン: "file.py:123行", "file.py (456行)", "file.py: 789 lines"
    _LINE_INFO_PATTERN = re.compile(r"\d+\s*(?:行|lines?|L)\b", re.IGNORECASE)

    with_line_info = sum(1 for e in entries if _LINE_INFO_PATTERN.search(e))
    without_line_info = len(entries) - with_line_info

    # 全エントリに行数情報がない場合のみブロック
    if with_line_info == 0 and len(entries) >= 3:
        return False, (
            f"review フェーズの files_read に行数情報が一切含まれていません（Check l）。\n"
            f"  エントリ数: {len(entries)}\n"
            f"  行数情報あり: 0\n"
            f"  サンプル: {', '.join(entries[:3])}\n"
            f"  → Read ツールで実際にファイルを読み込んだ場合、行数が分かるはずです。\n"
            f"    files_read には「ファイル名:行数」形式で記載してください。"
        )

    return True, ""


def _check_lateral_evidence_integrity(state: dict) -> tuple[bool, str]:
    """lateral-check フェーズの grep_commands_executed 証跡を検証（Check j）。

    提出された grep コマンドを実際に再実行し、ヒット数が0でないことを確認する。
    全コマンドがヒット0の場合、形骸化した証跡と判定してブロックする。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    context = state.get("context", {})
    lateral_result = context.get("phase_lateral-check_result")
    if not lateral_result:
        return True, ""  # lateral-check 未実行 → パス

    grep_raw = lateral_result.get("grep_commands_executed", "")
    if not grep_raw:
        return True, ""  # フィールド自体は gate で検証済み

    # grep コマンドからパターン文字列を抽出
    if isinstance(grep_raw, list):
        patterns = grep_raw
    else:
        patterns = [
            line.strip()
            for line in re.split(r"[\n,]", str(grep_raw))
            if line.strip()
        ]

    if not patterns:
        return True, ""

    # 各パターンを git grep で再検証（最大10個）
    verified_count = 0
    zero_hit_patterns = []
    for pattern in patterns[:10]:
        # パターンからgrepキーワードを抽出（"grep 'xxx' path" → "xxx"）
        keyword = pattern.strip()
        # "grep -r 'pattern' path" 形式の場合、パターン部分を抽出
        m = re.search(r"""(?:grep|rg)\s+.*?['"](.+?)['"]""", keyword)
        if m:
            keyword = m.group(1)
        else:
            # パス形式やコマンド形式でない純粋なパターンはそのまま使用
            # ただし空白を含む場合は最初の単語のみ
            keyword = keyword.split("→")[0].strip()
            keyword = keyword.split(":")[0].strip()
            if not keyword or len(keyword) < 2:
                continue

        try:
            result = subprocess.run(
                ["git", "grep", "-c", "--no-color", keyword],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                verified_count += 1
            else:
                zero_hit_patterns.append(keyword)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            verified_count += 1  # フェイルオープン

    total_checked = verified_count + len(zero_hit_patterns)
    if total_checked == 0:
        return True, ""  # パターン抽出できなかった → フェイルオープン

    # 全パターンがヒット0の場合のみブロック（一部ヒットなしは許容）
    if verified_count == 0 and zero_hit_patterns:
        return False, (
            f"lateral-check の grep 証跡が全てヒット0です（Check j）。\n"
            f"  検証パターン数: {total_checked}\n"
            f"  ヒット0のパターン:\n"
            + "\n".join(f"    - {p}" for p in zero_hit_patterns[:10])
            + f"\n  → lateral-check フェーズで実際に grep/検索を実行し、"
            f"結果をレビューしてから push してください。"
        )

    # diff 関連性チェック: パターンが diff 内容と関連しているか
    # 全パターンが diff に一切出現しない場合は警告（ブロックではない）
    if verified_count > 0:
        try:
            diff_result = subprocess.run(
                ["git", "diff", "--cached", "--no-color", "-U0"],
                capture_output=True, text=True, timeout=2,
            )
            if diff_result.returncode != 0:
                diff_result = subprocess.run(
                    ["git", "log", "--pretty=format:", "-p", "-1"],
                    capture_output=True, text=True, timeout=2,
                )
            diff_text = diff_result.stdout.lower() if diff_result.returncode == 0 else ""

            if diff_text:
                # パターンキーワードを小文字化して diff に出現するか確認
                all_extracted = []
                for p in patterns[:10]:
                    kw = p.strip().split("→")[0].strip().split(":")[0].strip().lower()
                    m2 = re.search(r"""(?:grep|rg)\s+.*?['"](.+?)['"]""", p)
                    if m2:
                        kw = m2.group(1).lower()
                    if kw and len(kw) >= 2:
                        all_extracted.append(kw)

                if all_extracted:
                    related = sum(1 for kw in all_extracted if kw in diff_text)
                    if related == 0:
                        # 警告のみ（ブロックしない — 関連パターンが diff 外にある正当なケースもある）
                        import sys as _sys
                        print(
                            f"⚠ Check j 警告: lateral-check の grep パターンが "
                            f"git diff に一切出現しません。\n"
                            f"  検証パターン: {', '.join(all_extracted[:5])}\n"
                            f"  → 横展開チェックが変更内容と関連しているか確認してください。",
                            file=_sys.stderr,
                        )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass  # フェイルオープン

    return True, ""


def _check_subgoal_verification(state: dict) -> tuple[bool, str]:
    """GP-029: サブゴールの完了がユーザー承認済みか検証する（Check m）。

    work-log の分解目的セクションに「完了」「done」等がマークされたサブゴールが
    あるにも関わらず、対応する [VERIFIED] マーカーがない場合をブロックする。

    AI が技術基準（数値PASS、テスト通過）のみで完了と判定することを防止する。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    wl_path = state.get("work_log_path", "")
    if not wl_path or not os.path.isfile(wl_path):
        return True, ""  # work-log なし → Check e で検証済み

    try:
        with open(wl_path, encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return True, ""  # フェイルオープン

    # 「完了」マーカーパターン: テーブル行で「完了」「done」「✅」を含む
    _DONE_PATTERNS = re.compile(
        r"^\|.*(?:完了|done|✅|✓).*\|", re.MULTILINE | re.IGNORECASE
    )
    done_lines = _DONE_PATTERNS.findall(content)
    if not done_lines:
        return True, ""  # 完了マーク済みサブゴールなし → 検証不要

    # [VERIFIED] マーカーの存在チェック
    verified_count = content.count("[VERIFIED]")
    done_count = len(done_lines)

    if verified_count < done_count:
        unverified = done_count - verified_count
        return False, (
            f"GP-029: サブゴールの完了マークに対してユーザー承認（[VERIFIED]）が不足しています（Check m）。\n"
            f"  完了マーク済み: {done_count} 件\n"
            f"  [VERIFIED] 済み: {verified_count} 件\n"
            f"  未承認: {unverified} 件\n"
            f"  → 各サブゴールの完了判定をユーザーに提示し、承認を得てから [VERIFIED] を記録してください。\n"
            f"  → 技術基準（テスト通過・数値一致）だけでなく、ユーザーの品質確認が必要です。"
        )

    return True, ""


def _check_dismiss_integrity(state: dict) -> tuple[bool, str]:
    """discuss フェーズの platform dismiss 整合性検証（Check k）。

    code-review ドメインで discuss フェーズが完了している場合、
    dismissed_findings の数と recheck_result の整合性を検証する。
    棄却した指摘があるのに recheck していない場合はブロックする。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    context = state.get("context", {})
    discuss_result = context.get("phase_discuss_result")
    if not discuss_result:
        return True, ""  # discuss 未実行 → パス

    # ドメインチェック: code-review のみ
    domain = state.get("domain", "")
    if domain != "code-review":
        return True, ""

    open_findings = discuss_result.get("automation_engine_open_findings", "0")
    dismissed_raw = discuss_result.get("automation_engine_dismissed_findings", "")
    recheck = discuss_result.get("automation_engine_recheck_result", "")

    # platform 未使用チェック
    if str(recheck).strip().lower() in ("platform未使用", "platform not used", "n/a"):
        # platform 未使用の場合は open_findings が 0 であることを確認
        try:
            if int(str(open_findings).strip()) > 0:
                return False, (
                    f"platform 未使用と宣言されていますが、未解決指摘が {open_findings} 件あります（Check k）。\n"
                    f"  → platform CLI を実行してレビューを完了するか、指摘数を修正してください。"
                )
        except (ValueError, TypeError):
            pass
        return True, ""

    # 棄却件数の解析
    dismissed_count = 0
    if isinstance(dismissed_raw, list):
        dismissed_count = len(dismissed_raw)
    elif isinstance(dismissed_raw, str) and dismissed_raw.strip():
        # JSON 配列文字列の場合
        try:
            parsed = json.loads(dismissed_raw)
            if isinstance(parsed, list):
                dismissed_count = len(parsed)
        except (json.JSONDecodeError, TypeError):
            # カンマ区切りなどの場合は行数をカウント
            dismissed_count = len([
                line for line in dismissed_raw.strip().splitlines()
                if line.strip() and line.strip() != "[]"
            ])

    # 棄却あり + recheck なし → ブロック
    if dismissed_count > 0:
        recheck_str = str(recheck).strip()
        if not recheck_str or recheck_str in ("", "未実施", "not done"):
            return False, (
                f"platform 指摘を {dismissed_count} 件棄却していますが、"
                f"platform への再確認（recheck）が未実施です（Check k — CR-004）。\n"
                f"  → 棄却理由を含むコンテキストを platform に --review-log 経由で再送し、\n"
                f"    platform が同一指摘を出さなくなることを確認してください。"
            )

        # recheck 結果に re-raised > 0 が含まれていないか確認
        re_raised_match = re.search(r"re-raised:\s*(\d+)", recheck_str)
        if re_raised_match:
            re_raised = int(re_raised_match.group(1))
            if re_raised > 0:
                return False, (
                    f"platform が棄却した指摘のうち {re_raised} 件を再提出しました（Check k — CR-004）。\n"
                    f"  recheck 結果: {recheck_str}\n"
                    f"  → 再提出された指摘を解決してから push してください。"
                )

    return True, ""


def _check_agreement_hashes_for_ssot_impact() -> tuple[bool, str]:
    """P-006: ssot_impact 宣言時に合意ハッシュ（Step 8d）が完了しているか検証する（Check n）。

    ssot_impact != none の場合、approve の Step 8d で .agreement-hashes に
    SHA256 ハッシュが登録されていなければ push をブロックする。

    Returns:
        (is_ok, message) — is_ok=False でブロック
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        return True, ""  # フェイルオープン

    # .ssot-impact-declared を読む
    impact_path = os.path.join(project_dir, ".claude", "logs", ".ssot-impact-declared")
    if not os.path.isfile(impact_path):
        return True, ""  # 宣言なし → チェック不要

    try:
        with open(impact_path, encoding="utf-8") as f:
            impact_value = f.read().strip()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return True, ""  # フェイルオープン

    if not impact_value or impact_value == "none":
        return True, ""  # ssot_impact == none → チェック不要

    # ssot_impact != none → .agreement-hashes が存在し、中身が非空であること
    hashes_path = os.path.join(project_dir, ".claude", "logs", ".agreement-hashes")
    if not os.path.isfile(hashes_path):
        return False, (
            f"ssot_impact='{impact_value}' が宣言されていますが、"
            f".agreement-hashes が存在しません。\n"
            f"  → approve Step 8d（合意ハッシュ登録）が未完了です。\n"
            f"  → 3案 vote → ユーザー投票 → DR 起票 → 合意ハッシュ登録を完了してから push してください。"
        )

    try:
        with open(hashes_path, encoding="utf-8") as f:
            hashes_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError, UnicodeDecodeError):
        return False, (
            f"ssot_impact='{impact_value}' が宣言されていますが、"
            f".agreement-hashes の読み取りに失敗しました。\n"
            f"  → approve Step 8d（合意ハッシュ登録）を再実行してください。"
        )

    if not hashes_data or not isinstance(hashes_data, dict) or len(hashes_data) == 0:
        return False, (
            f"ssot_impact='{impact_value}' が宣言されていますが、"
            f".agreement-hashes が空です。\n"
            f"  → approve Step 8d（合意ハッシュ登録）が未完了です。\n"
            f"  → 3案 vote → ユーザー投票 → DR 起票 → 合意ハッシュ登録を完了してから push してください。"
        )

    return True, ""


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)  # パース失敗はフェイルオープン

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})

    if tool != "Bash":
        sys.exit(0)

    cmd = inp.get("command", "")
    if not cmd:
        sys.exit(0)

    # --- S-001~S-003: Git 安全弁チェック（ワークフロー状態に依存しない） ---
    git_safe, git_msg = _check_git_safety(cmd)
    if not git_safe:
        print(git_msg, file=sys.stderr)
        sys.exit(2)

    # ゲート対象コマンドか判定
    if not _is_gate_command(cmd):
        sys.exit(0)

    # チェック a: .workflow-expected あり + .workflow-active なし → init スキップ
    expected_path = _get_marker_path("expected")
    active_path = _get_marker_path("active")
    if expected_path and os.path.isfile(expected_path) and not os.path.isfile(active_path):
        try:
            with open(expected_path) as f:
                expected = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            expected = {}
        skill = expected.get("skill", "?")
        domain = expected.get("domain", "?")

        # IMP-074: Flow B-only スキル（context-lock 免除 but work-log 必須）
        if expected.get("flow_b_only"):
            # workflow_step.py init は不要だが、work-log は必須
            project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
            has_work_log = False
            if project_dir:
                wl_dir = os.path.join(project_dir, ".claude", "logs", "work-logs")
                if os.path.isdir(wl_dir):
                    wl_files = [f for f in os.listdir(wl_dir) if f.endswith(".md")]
                    if wl_files:
                        has_work_log = True
            if not has_work_log:
                print(
                    f"⚠ IMP-074 違反: /{skill}（ドメイン: {domain}）の work-log が見つかりません。\n"
                    f"  Flow A（コンテキストロック）は免除ですが、Flow B（resolve/approve）は必須です。\n"
                    f"  → CLAUDE.md Flow B Step 7 に従い、work-log を作成してからコミットしてください。\n"
                    f"  → 配置先: .claude/logs/work-logs/{{goal-slug}}.md",
                    file=sys.stderr,
                )
                sys.exit(2)
            # work-log あり → パススルー（Flow B-only スキルは workflow_step.py init 不要）
            sys.exit(0)

        print(
            f"⚠ IMP-071 違反: /{skill}（ドメイン: {domain}）のワークフローが初期化されていません。\n"
            f"  workflow_step.py init が呼ばれていません。\n"
            f"  → SKILL.md の Step 0 に従って init を実行してください。",
            file=sys.stderr,
        )
        sys.exit(2)

    # ワークフロー状態を読み込み（チェック b/c）
    state = _read_workflow_state()
    if state is None:
        # ワークフロー未初期化かつ expected もなし → 非スキル実行
        sys.exit(0)

    # 完了チェック
    is_complete, message = _check_workflow_complete(state)
    if not is_complete:
        print(
            f"⚠ IMP-071 違反: ワークフローフェーズが未完了のため、操作をブロックしました。\n"
            f"  {message}\n"
            f"  → SKILL.md のフェーズ順序に従って作業を完了してください。",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- チェック d: ssot_impact で宣言された SSoT ファイルの変更検証 ---
    if _is_push_command(cmd):
        ssot_ok, ssot_msg = _check_ssot_impact_fulfilled(state)
        if not ssot_ok:
            print(
                f"⚠ ssot_impact 検証失敗: {ssot_msg}",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- チェック e: work-log 存在検証（ブロック） ---
    wl_exists_ok, wl_exists_msg = _check_work_log_exists(state)
    if not wl_exists_ok:
        print(
            f"⚠ work-log 未作成: {wl_exists_msg}",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- チェック f: 制約検知後の work-log 更新検証（ブロック） ---
    constraint_ok, constraint_msg = _check_constraint_acknowledged(state)
    if not constraint_ok:
        print(
            f"⚠ 制約反映検証失敗: {constraint_msg}",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- チェック g: ssot_impact 宣言漏れ検出（push 時のみ） ---
    if _is_push_command(cmd):
        undeclared_ok, undeclared_msg = _check_ssot_undeclared_changes(state)
        if not undeclared_ok:
            print(
                f"⚠ ssot_impact 宣言漏れ: {undeclared_msg}",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- チェック h: code-review 収束判定（push 時のみ） ---
    if _is_push_command(cmd):
        review_ok, review_msg = _check_review_convergence(state)
        if not review_ok:
            print(
                f"⚠ レビュー収束未達: {review_msg}",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- チェック i: review 証跡の git diff 突合検証（push 時のみ） ---
    if _is_push_command(cmd):
        evidence_ok, evidence_msg = _check_review_evidence_integrity(state)
        if not evidence_ok:
            print(
                f"⚠ 証跡形骸化検出: {evidence_msg}",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- チェック l: review files_read の行数情報検証（push 時のみ） ---
    if _is_push_command(cmd):
        depth_ok, depth_msg = _check_files_read_depth(state)
        if not depth_ok:
            print(
                f"⚠ 証跡品質不足: {depth_msg}",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- チェック j: lateral-check 証跡の grep 突合検証（push 時のみ） ---
    if _is_push_command(cmd):
        lateral_ok, lateral_msg = _check_lateral_evidence_integrity(state)
        if not lateral_ok:
            print(
                f"⚠ 横展開証跡形骸化検出: {lateral_msg}",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- チェック k: discuss フェーズの dismiss 整合性検証（push 時のみ） ---
    if _is_push_command(cmd):
        dismiss_ok, dismiss_msg = _check_dismiss_integrity(state)
        if not dismiss_ok:
            print(
                f"⚠ CR-004 違反（dismiss 整合性）: {dismiss_msg}",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- チェック m: サブゴール完了のユーザー承認検証（push 時のみ） ---
    if _is_push_command(cmd):
        subgoal_ok, subgoal_msg = _check_subgoal_verification(state)
        if not subgoal_ok:
            print(
                f"⚠ サブゴール承認不足: {subgoal_msg}",
                file=sys.stderr,
            )
            sys.exit(2)

    # --- チェック n: ssot_impact 宣言時の合意ハッシュ検証（push 時のみ） ---
    # P-006: ssot_impact != none なら Step 8d（合意ハッシュ登録）が完了していること
    if _is_push_command(cmd):
        agree_ok, agree_msg = _check_agreement_hashes_for_ssot_impact()
        if not agree_ok:
            print(
                f"⚠ P-006 approve 不完全: {agree_msg}",
                file=sys.stderr,
            )
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # フェイルオープン: hook 自体のエラーでは通過
        print(f"[Hook Warning] workflow_enforce.py error: {e}", file=sys.stderr)
        try:
            from hook_logger import log_hook_error
            log_hook_error("workflow_enforce.py", e)
        except Exception:
            pass
        sys.exit(0)
