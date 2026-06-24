#!/usr/bin/env python3
"""validate_skill_workflow.py — SKILL.md ↔ teams.yaml Phase 対応検証。

T1（SKILL.md）と T2（teams.yaml workflow）の乖離を検出する CI ゲート。

検証内容:
  S1: skill_mapping の非 null エントリごとに SKILL.md が存在すること
  S2: SKILL.md の Phase セクションが teams.yaml の workflow phases をカバーすること
  S3: null マッピング（ルーター）の SKILL.md にルーティングセクションがあること
  S4: 全スキルに Step 0 コンテキスト解決があること
  S5: 旧形式（Phase N:）が残存していないこと

Usage:
    python3 validate_skill_workflow.py
    python3 validate_skill_workflow.py --teams-yaml PATH --skills-dir PATH

Exit codes:
    0  All checks PASS (WARN is acceptable)
    1  One or more checks FAIL
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0


def _pass(check_id: str, msg: str) -> None:
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"[PASS] {check_id}: {msg}")


def _fail(check_id: str, msg: str) -> None:
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"[FAIL] {check_id}: {msg}")


def _warn(check_id: str, msg: str) -> None:
    global WARN_COUNT
    WARN_COUNT += 1
    print(f"[WARN] {check_id}: {msg}")


# ---------------------------------------------------------------------------
# Phase detection in SKILL.md
# ---------------------------------------------------------------------------

# Patterns that indicate a Phase section in SKILL.md
# Matches: "### Phase: plan", "## Phase: implement", "Phase: review" etc.
PHASE_PATTERN = re.compile(r"^#{1,4}\s*Phase:\s*(\S+)", re.MULTILINE)

# Alternative: Step-based naming that maps to phases
# Matches: "### Step 3: 実装（implement）" or similar
STEP_PHASE_PATTERN = re.compile(
    r"^#{1,4}\s*Step\s+\d+.*?[（(](\w+)[）)]",
    re.MULTILINE,
)


def extract_phases_from_skill(skill_path: Path) -> set[str]:
    """SKILL.md から Phase セクション名を抽出する。"""
    text = skill_path.read_text(encoding="utf-8")
    phases: set[str] = set()

    # Phase: xxx パターン
    for m in PHASE_PATTERN.finditer(text):
        phases.add(m.group(1).strip().lower())

    # Step N: ... (phase_name) パターン
    for m in STEP_PHASE_PATTERN.finditer(text):
        phases.add(m.group(1).strip().lower())

    return phases


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_skill_exists(
    skill_mapping: dict[str, str | None],
    skills_dir: Path,
) -> None:
    """S1: 全 skill_mapping エントリに SKILL.md が存在すること。"""
    missing: list[str] = []
    for skill_name in skill_mapping:
        skill_md = skills_dir / skill_name / "SKILL.md"
        if not skill_md.exists():
            missing.append(skill_name)

    if missing:
        _fail("S1", f"SKILL.md が存在しないスキル: {missing}")
    else:
        _pass("S1", f"全 {len(skill_mapping)} スキルに SKILL.md が存在")


def check_phase_coverage(
    skill_mapping: dict[str, str | None],
    domains: dict[str, Any],
    skills_dir: Path,
) -> None:
    """S2: 非 null スキルの SKILL.md が、ドメインの workflow phases をカバーすること。"""
    for skill_name, domain_name in skill_mapping.items():
        if domain_name is None:
            continue  # ルーターはスキップ

        skill_md = skills_dir / skill_name / "SKILL.md"
        if not skill_md.exists():
            continue  # S1 で検出済み

        domain_def = domains.get(domain_name, {})
        workflow = domain_def.get("workflow", [])
        if not workflow:
            continue

        skill_phases = extract_phases_from_skill(skill_md)

        # Phase セクションが 0 個の場合は「まだ Phase セクション化されていない」
        if not skill_phases:
            _fail(
                "S2",
                f"{skill_name} (→{domain_name}): SKILL.md に Phase セクションなし"
                f"（Phase セクション化が必要）",
            )
            continue

        # workflow にあって SKILL.md にない phases
        missing = set(workflow) - skill_phases
        if missing:
            _fail(
                "S2",
                f"{skill_name} (→{domain_name}): workflow にある Phase が SKILL.md に未定義:"
                f" {sorted(missing)}",
            )
        else:
            _pass(
                "S2",
                f"{skill_name} (→{domain_name}): 全 {len(workflow)} phases カバー",
            )


def check_router_skills(
    skill_mapping: dict[str, str | None],
    skills_dir: Path,
) -> None:
    """S3: null マッピング（ルーター）の SKILL.md にルーティングセクションがあること。"""
    router_skills = [s for s, d in skill_mapping.items() if d is None]
    for skill_name in router_skills:
        skill_md = skills_dir / skill_name / "SKILL.md"
        if not skill_md.exists():
            continue

        text = skill_md.read_text(encoding="utf-8")
        has_routing = (
            "ドメインルーティング" in text
            or "domain routing" in text.lower()
            or "ルーター" in text
        )
        if has_routing:
            _pass("S3", f"{skill_name}: ルータースキルにルーティングセクションあり")
        else:
            _warn("S3", f"{skill_name}: ルータースキルにルーティングセクションなし")


def check_step0_context_resolve(
    skill_mapping: dict[str, str | None],
    skills_dir: Path,
) -> None:
    """S4: 全スキルの SKILL.md に Step 0 のコンテキスト解決（Step b'）が含まれること。"""
    # sync と slides-export は除外（CLAUDE.md で明示的に免除）
    exempt = {"sync", "slides-export"}
    errors: list[str] = []

    for skill_name in skill_mapping:
        if skill_name in exempt:
            continue
        skill_md = skills_dir / skill_name / "SKILL.md"
        if not skill_md.exists():
            continue

        text = skill_md.read_text(encoding="utf-8")
        has_step0 = "Step 0" in text or "step 0" in text.lower()
        has_context_resolve = (
            "コンテキスト解決" in text
            or "teams.yaml" in text
        )
        if not has_step0:
            errors.append(f"{skill_name}: Step 0 なし")
        elif not has_context_resolve:
            errors.append(f"{skill_name}: Step 0 にコンテキスト解決（teams.yaml 参照）なし")

    if errors:
        _warn("S4", f"Step 0 コンテキスト解決の問題: {'; '.join(errors[:5])}" +
              (f" ... and {len(errors)-5} more" if len(errors) > 5 else ""))
    else:
        _pass("S4", f"全スキルに Step 0 コンテキスト解決あり（{len(skill_mapping) - len(exempt)} 件）")


# Top-level Phase N only (###) — sub-phase headers (####) within Phase sections are OK
OLD_PHASE_PATTERN = re.compile(r"^###\s+Phase\s+\d+", re.MULTILINE)


def check_no_legacy_format(
    skill_mapping: dict[str, str | None],
    skills_dir: Path,
) -> None:
    """S5: 旧形式 '### Phase N:' が残存していないこと。"""
    legacy_skills: list[str] = []

    for skill_name in skill_mapping:
        skill_md = skills_dir / skill_name / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8")
        if OLD_PHASE_PATTERN.search(text):
            legacy_skills.append(skill_name)

    if legacy_skills:
        for s in legacy_skills:
            _fail("S5", f"{s}: 旧形式 'Phase N' が残存 — 'Phase: {{name}}' 形式に移行してください")
    else:
        _pass("S5", f"全 {len(skill_mapping)} スキルに旧形式 Phase N なし")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate SKILL.md ↔ teams.yaml Phase correspondence",
    )
    script_dir = Path(__file__).resolve().parent
    default_refs = script_dir.parent / "references"
    default_skills = script_dir.parent / "skills"

    parser.add_argument(
        "--teams-yaml", type=Path, default=default_refs / "teams.yaml",
        help="Path to teams.yaml",
    )
    parser.add_argument(
        "--skills-dir", type=Path, default=default_skills,
        help="Path to skills/ directory",
    )
    args = parser.parse_args()

    print("=== validate_skill_workflow.py ===")
    print(f"  teams.yaml:  {args.teams_yaml}")
    print(f"  skills/:     {args.skills_dir}")
    print()

    # Load teams.yaml
    try:
        with open(args.teams_yaml) as f:
            teams = yaml.safe_load(f)
    except Exception as e:
        print(f"[FAIL] LOAD: Cannot load teams.yaml: {e}")
        return 1

    skill_mapping: dict[str, str | None] = teams.get("skill_mapping", {})
    domains: dict[str, Any] = teams.get("domains", {})

    # --- S1: SKILL.md existence ---
    check_skill_exists(skill_mapping, args.skills_dir)

    # --- S2: Phase coverage ---
    check_phase_coverage(skill_mapping, domains, args.skills_dir)

    # --- S3: Router skills ---
    check_router_skills(skill_mapping, args.skills_dir)

    # --- S4: Step 0 context resolve ---
    check_step0_context_resolve(skill_mapping, args.skills_dir)

    # --- S5: No legacy Phase N format ---
    check_no_legacy_format(skill_mapping, args.skills_dir)

    # --- Summary ---
    print()
    print(f"=== Result: {PASS_COUNT} PASS, {WARN_COUNT} WARN, {FAIL_COUNT} FAIL ===")

    return 1 if FAIL_COUNT > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
