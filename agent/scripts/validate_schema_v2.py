#!/usr/bin/env python3
"""validate_schema_v2.py — teams.yaml + learned-rules.yaml v2.0 schema integrity gate.

Standalone validation (no platform dependency). Uses only yaml + standard lib.

Usage:
    python3 validate_schema_v2.py
    python3 validate_schema_v2.py --teams-yaml PATH --rules-yaml PATH
    python3 validate_schema_v2.py --domains-dir PATH

Exit codes:
    0  All checks PASS (WARN is acceptable)
    1  One or more checks FAIL
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Helpers
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
# A. Basic Schema Checks
# ---------------------------------------------------------------------------

def check_a1(teams: dict[str, Any]) -> None:
    """A1: company.principles - no duplicate IDs."""
    principles = teams.get("company", {}).get("principles")
    if not principles:
        _fail("A1", "company.principles not found or empty")
        return
    ids = [p.get("id") for p in principles if p.get("id")]
    dupes = [pid for pid, cnt in Counter(ids).items() if cnt > 1]
    if dupes:
        _fail("A1", f"company.principles - duplicate IDs: {dupes}")
    else:
        _pass("A1", f"company.principles - no duplicate IDs ({len(ids)} entries)")


def check_a2(teams: dict[str, Any]) -> None:
    """A2: All personas have phase_affinity field (list)."""
    personas = teams.get("personas", {})
    if not personas:
        _fail("A2", "personas registry not found or empty")
        return
    missing = [pid for pid, p in personas.items() if not isinstance(p.get("phase_affinity"), list)]
    if missing:
        _fail("A2", f"personas missing phase_affinity (list): {missing}")
    else:
        _pass("A2", f"all personas have phase_affinity field ({len(personas)} entries)")


def check_a3(teams: dict[str, Any]) -> None:
    """A3: All personas have domains field (list)."""
    personas = teams.get("personas", {})
    if not personas:
        _fail("A3", "personas registry not found or empty")
        return
    missing = [pid for pid, p in personas.items() if not isinstance(p.get("domains"), list)]
    if missing:
        _fail("A3", f"personas missing domains (list): {missing}")
    else:
        _pass("A3", f"all personas have domains field ({len(personas)} entries)")


def check_a4(teams: dict[str, Any]) -> None:
    """A4: common_phases list exists at top level."""
    cp = teams.get("common_phases")
    if not isinstance(cp, list) or len(cp) == 0:
        _fail("A4", "common_phases not found or not a non-empty list")
    else:
        _pass("A4", f"common_phases exists ({len(cp)} phases: {cp})")


def check_a5(teams: dict[str, Any]) -> None:
    """A5: skill_mapping dict exists at top level."""
    sm = teams.get("skill_mapping")
    if not isinstance(sm, dict) or len(sm) == 0:
        _fail("A5", "skill_mapping not found or not a non-empty dict")
    else:
        _pass("A5", f"skill_mapping exists ({len(sm)} entries)")


# ---------------------------------------------------------------------------
# B. Bidirectional Reference Check
# ---------------------------------------------------------------------------

def check_b6_b7(teams: dict[str, Any]) -> None:
    """B6/B7: persona.domains <-> domain.persona_refs bidirectional consistency."""
    personas = teams.get("personas", {})
    domains = teams.get("domains", {})

    errors_b6: list[str] = []
    errors_b7: list[str] = []

    # B6: For each persona, every domain in persona.domains must list persona in persona_refs
    for pid, pdata in personas.items():
        for dname in pdata.get("domains", []):
            if dname not in domains:
                errors_b6.append(f"persona '{pid}' references non-existent domain '{dname}'")
                continue
            prefs = domains[dname].get("persona_refs", [])
            if pid not in prefs:
                errors_b6.append(f"persona '{pid}' lists domain '{dname}' but '{dname}'.persona_refs does not include '{pid}'")

    if errors_b6:
        _fail("B6", f"persona->domain reference mismatches ({len(errors_b6)}): {'; '.join(errors_b6[:5])}" +
              (f" ... and {len(errors_b6)-5} more" if len(errors_b6) > 5 else ""))
    else:
        _pass("B6", "bidirectional check (persona->domain) - all consistent")

    # B7: For each domain, every persona in persona_refs must list that domain in persona.domains
    for dname, ddata in domains.items():
        for pid in ddata.get("persona_refs", []):
            if pid not in personas:
                errors_b7.append(f"domain '{dname}' references non-existent persona '{pid}'")
                continue
            pdomains = personas[pid].get("domains", [])
            if dname not in pdomains:
                errors_b7.append(f"domain '{dname}'.persona_refs includes '{pid}' but persona '{pid}'.domains does not include '{dname}'")

    if errors_b7:
        _fail("B7", f"domain->persona reference mismatches ({len(errors_b7)}): {'; '.join(errors_b7[:5])}" +
              (f" ... and {len(errors_b7)-5} more" if len(errors_b7) > 5 else ""))
    else:
        _pass("B7", "bidirectional check (domain->persona) - all consistent")


# ---------------------------------------------------------------------------
# C. skill_mapping <-> domains Consistency
# ---------------------------------------------------------------------------

def check_c9_c10_c11_c12_c13(teams: dict[str, Any]) -> None:
    """C9-C13: skill_mapping <-> domains.skills consistency."""
    skill_mapping = teams.get("skill_mapping", {})
    domains = teams.get("domains", {})

    # Build reverse map: domain_name -> set of skills
    domain_skills: dict[str, set[str]] = {}
    for dname, ddata in domains.items():
        domain_skills[dname] = set(ddata.get("skills", []))

    # C9: Non-null skill_mapping entries must map to an existing domain
    errors_c9: list[str] = []
    for skill, domain in skill_mapping.items():
        if domain is not None and domain not in domains:
            errors_c9.append(f"'{skill}' -> '{domain}' (domain not found)")
    if errors_c9:
        _fail("C9", f"skill_mapping references non-existent domains: {errors_c9}")
    else:
        _pass("C9", "all non-null skill_mapping entries map to existing domains")

    # C10: Non-null: skill name must appear in that domain's skills list
    errors_c10: list[str] = []
    for skill, domain in skill_mapping.items():
        if domain is not None and domain in domains:
            if skill not in domain_skills.get(domain, set()):
                errors_c10.append(f"'{skill}' mapped to '{domain}' but not in {domain}.skills")
    if errors_c10:
        _fail("C10", f"skill_mapping entries not in domain.skills: {errors_c10}")
    else:
        _pass("C10", "all non-null skill_mapping entries appear in their domain.skills")

    # C11: Reverse - every skill in every domain's skills list must appear in skill_mapping
    errors_c11: list[str] = []
    for dname, skills in domain_skills.items():
        for s in skills:
            if s not in skill_mapping:
                errors_c11.append(f"'{s}' in {dname}.skills but not in skill_mapping")
            elif skill_mapping[s] != dname:
                errors_c11.append(f"'{s}' in {dname}.skills but skill_mapping['{s}'] = '{skill_mapping[s]}'")
    if errors_c11:
        _fail("C11", f"domain.skills entries not matching skill_mapping: {errors_c11}")
    else:
        _pass("C11", "all domain.skills entries have matching skill_mapping entries")

    # C12: null mappings (task, ai-task) must NOT appear in any domain's skills
    errors_c12: list[str] = []
    null_skills = {s for s, d in skill_mapping.items() if d is None}
    for dname, skills in domain_skills.items():
        for s in skills:
            if s in null_skills:
                errors_c12.append(f"null-mapped skill '{s}' found in {dname}.skills")
    if errors_c12:
        _fail("C12", f"null-mapped skills appear in domain.skills: {errors_c12}")
    else:
        _pass("C12", f"null-mapped skills ({null_skills}) not in any domain.skills")

    # C13: Domains with T2 skills (ai- prefix in skills list) must have orchestration.tier2 non-null
    errors_c13: list[str] = []
    for dname, ddata in domains.items():
        has_t2 = any(s.startswith("ai-") for s in ddata.get("skills", []))
        orch = ddata.get("orchestration", {})
        tier2 = orch.get("tier2") if orch else None
        if has_t2 and tier2 is None:
            errors_c13.append(f"domain '{dname}' has T2 skills but orchestration.tier2 is null")
    if errors_c13:
        _fail("C13", f"domains with T2 skills missing orchestration.tier2: {errors_c13}")
    else:
        _pass("C13", "all domains with T2 skills have orchestration.tier2 defined")


# ---------------------------------------------------------------------------
# D. resolve_actors Verification
# ---------------------------------------------------------------------------

def check_d14(teams: dict[str, Any]) -> None:
    """D14: For each domain+phase, at least 1 actor (except 'approve')."""
    personas = teams.get("personas", {})
    domains = teams.get("domains", {})

    errors: list[str] = []
    for dname, ddata in domains.items():
        prefs = ddata.get("persona_refs", [])
        workflow = ddata.get("workflow", [])
        for phase in workflow:
            actors = [p for p in prefs if phase in personas.get(p, {}).get("phase_affinity", [])]
            if len(actors) == 0 and phase != "approve":
                errors.append(f"{dname}.{phase}: 0 actors (persona_refs={prefs})")

    if errors:
        _fail("D14", f"phases with 0 actors: {'; '.join(errors)}")
    else:
        _pass("D14", "all domain phases have >=1 actors (approve exempt)")


# ---------------------------------------------------------------------------
# E. Rule Binding Checks (learned-rules.yaml)
# ---------------------------------------------------------------------------

def check_e15(rules_list: list[dict[str, Any]]) -> None:
    """E15: No rules with binding.level == 'skill' (abolished)."""
    bad = [r["id"] for r in rules_list if r.get("binding", {}).get("level") == "skill"]
    if bad:
        _fail("E15", f"found {len(bad)} rules with binding.level=='skill': {bad}")
    else:
        _pass("E15", "no rules with abolished binding.level=='skill'")


def check_e16(rules_list: list[dict[str, Any]], common_phases: list[str]) -> None:
    """E16: Rules with binding.level=='phase' must have target in common_phases."""
    errors: list[str] = []
    for r in rules_list:
        b = r.get("binding", {})
        if b.get("level") == "phase":
            target = b.get("target")
            if target not in common_phases:
                errors.append(f"{r['id']}: binding.target='{target}' not in common_phases")
    # Also check domain-level rules with phase field
    for r in rules_list:
        b = r.get("binding", {})
        if b.get("phase"):
            phase = b["phase"]
            # Phase binding validation: phase must be either in common_phases OR
            # in the domain's workflow (domain-specific phases are allowed)
            # Per spec, only phase-level binding.target must be in common_phases
            if b.get("level") == "phase" and phase not in common_phases:
                # Already handled above
                pass
    if errors:
        _fail("E16", f"phase-level binding targets not in common_phases: {errors}")
    else:
        _pass("E16", "all phase-level binding targets are in common_phases")


def check_e17(rules_list: list[dict[str, Any]], domain_names: set[str]) -> None:
    """E17: Rules with binding.level=='domain' must have target in domains."""
    errors: list[str] = []
    for r in rules_list:
        b = r.get("binding", {})
        if b.get("level") == "domain":
            target = b.get("target")
            if target not in domain_names:
                errors.append(f"{r['id']}: binding.target='{target}' not in domains")
    if errors:
        _fail("E17", f"domain-level binding targets not in domains: {errors}")
    else:
        _pass("E17", "all domain-level binding targets are in domains")


# ---------------------------------------------------------------------------
# F. Governance Checks
# ---------------------------------------------------------------------------

def check_f18(teams: dict[str, Any]) -> None:
    """F18: Each common_phase must appear in >=2 domains' workflows.

    'resolve' is exempt: it runs automatically outside the workflow (REQ-002).
    """
    common_phases = teams.get("common_phases", [])
    domains = teams.get("domains", {})

    # resolve は workflow 外で自動実行されるため除外
    workflow_phases = [p for p in common_phases if p != "resolve"]

    phase_usage: dict[str, list[str]] = {p: [] for p in workflow_phases}
    for dname, ddata in domains.items():
        for phase in ddata.get("workflow", []):
            if phase in phase_usage:
                phase_usage[phase].append(dname)

    violations = {p: doms for p, doms in phase_usage.items() if len(doms) < 2}
    if violations:
        details = "; ".join(f"'{p}' used in {len(d)} domain(s): {d}" for p, d in violations.items())
        _warn("F18", f"common_phases used in <2 domains (may be domain-specific): {details}")
    else:
        _pass("F18", f"all common_phases appear in >=2 domains' workflows (resolve exempt: auto-executed)")


def check_f19(teams: dict[str, Any]) -> None:
    """F19: WARN if persona's phase_affinity includes phases not in any of its domains' workflows."""
    personas = teams.get("personas", {})
    domains = teams.get("domains", {})

    warnings: list[str] = []
    for pid, pdata in personas.items():
        pa = set(pdata.get("phase_affinity", []))
        pdomains = pdata.get("domains", [])
        # Collect all phases from persona's domains' workflows
        domain_phases: set[str] = set()
        for dname in pdomains:
            if dname in domains:
                domain_phases.update(domains[dname].get("workflow", []))
        orphan = pa - domain_phases
        if orphan:
            warnings.append(f"persona '{pid}' has phase_affinity {orphan} not in any domain workflow ({pdomains})")

    if warnings:
        for w in warnings:
            _warn("F19", w)
    else:
        _pass("F19", "all persona phase_affinity phases found in their domains' workflows")


# ---------------------------------------------------------------------------
# G. Workflow Format Checks
# ---------------------------------------------------------------------------

def check_g20(teams: dict[str, Any]) -> None:
    """G20: All domain workflows must be lists of strings (not objects)."""
    domains = teams.get("domains", {})
    errors: list[str] = []
    for dname, ddata in domains.items():
        wf = ddata.get("workflow")
        if wf is None:
            errors.append(f"domain '{dname}' has no workflow")
            continue
        if not isinstance(wf, list):
            errors.append(f"domain '{dname}'.workflow is not a list")
            continue
        non_str = [i for i, item in enumerate(wf) if not isinstance(item, str)]
        if non_str:
            errors.append(f"domain '{dname}'.workflow has non-string items at indices {non_str}")
    if errors:
        _fail("G20", f"workflow format errors: {'; '.join(errors)}")
    else:
        _pass("G20", f"all domain workflows are lists of strings ({len(domains)} domains)")


# ---------------------------------------------------------------------------
# H. Domain Package Cross-Validation (domains/ <-> teams.yaml)
# ---------------------------------------------------------------------------

# teams.yaml domain name -> Python package name mapping
_DOMAIN_PKG_MAP: dict[str, str] = {
    "code-review": "code_review",
    "pm-export": "pm_export",
    "pm-planning": "pm_planning",
    "project-mgmt": "project_mgmt",
}


def _domain_to_pkg(domain_name: str) -> str:
    """Convert teams.yaml domain name to Python package directory name."""
    return _DOMAIN_PKG_MAP.get(domain_name, domain_name.replace("-", "_"))


def _extract_phase_handlers_from_init(init_path: Path) -> tuple[set[str] | None, bool]:
    """Parse __init__.py and extract PHASE_HANDLERS keys or inline handler keys.

    Returns:
        (phase_keys, has_domain_executor)
        phase_keys: set of phase name strings, or None if not extractable
        has_domain_executor: True if DOMAIN_EXECUTOR is assigned at module level
    """
    try:
        source = init_path.read_text(encoding="utf-8")
    except OSError:
        return None, False

    tree = ast.parse(source, filename=str(init_path))

    has_domain_executor = False
    phase_keys: set[str] | None = None

    for node in ast.walk(tree):
        # Check for DOMAIN_EXECUTOR = ... at module level
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DOMAIN_EXECUTOR":
                    has_domain_executor = True

        # Check for PHASE_HANDLERS = { ... } at module level
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PHASE_HANDLERS":
                    if isinstance(node.value, ast.Dict):
                        keys = set()
                        for k in node.value.keys:
                            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                keys.add(k.value)
                        phase_keys = keys

    # If no explicit PHASE_HANDLERS, try to extract from inline handlers dict
    # inside execute_phase method
    if phase_keys is None:
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "execute_phase":
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name) and target.id == "handlers":
                                if isinstance(child.value, ast.Dict):
                                    keys = set()
                                    for k in child.value.keys:
                                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                            keys.add(k.value)
                                    phase_keys = keys

    return phase_keys, has_domain_executor


def check_h21(teams: dict[str, Any], domains_dir: Path) -> None:
    """H21: Every domain in teams.yaml has a corresponding package in domains/."""
    domains = teams.get("domains", {})
    internal_dirs = {"_common", "_generic", "__pycache__"}

    errors: list[str] = []
    warnings: list[str] = []

    for dname in domains:
        pkg_name = _domain_to_pkg(dname)
        pkg_path = domains_dir / pkg_name
        if pkg_path.is_dir() and (pkg_path / "__init__.py").exists():
            pass  # OK — migrated domain
        elif (domains_dir / "_generic").is_dir():
            warnings.append(f"domain '{dname}' has no dedicated package (using _generic)")
        else:
            errors.append(f"domain '{dname}' — no package '{pkg_name}/' and no _generic/ fallback")

    if errors:
        _fail("H21", f"domain package missing: {'; '.join(errors)}")
    elif warnings:
        for w in warnings:
            _warn("H21", w)
        _pass("H21", f"domain packages present for migrated domains ({len(domains) - len(warnings)}/{len(domains)})")
    else:
        _pass("H21", f"all {len(domains)} domains have dedicated packages")


# Gate phases: inline-validated by WorkflowStepCore._validate_gate_phase_result()
# These don't need dedicated .py handler files.
_GATE_PHASES = {"lateral-check", "source-verify", "discuss", "phase-complete"}


def check_h22(teams: dict[str, Any], domains_dir: Path) -> None:
    """H22: Each migrated domain has .py files for every workflow phase."""
    domains = teams.get("domains", {})

    errors: list[str] = []
    skipped: list[str] = []

    for dname, ddata in domains.items():
        pkg_name = _domain_to_pkg(dname)
        pkg_path = domains_dir / pkg_name
        if not pkg_path.is_dir() or not (pkg_path / "__init__.py").exists():
            skipped.append(dname)
            continue

        workflow = ddata.get("workflow", [])
        for phase in workflow:
            if phase in _GATE_PHASES:
                continue  # gate phases are inline-validated, no .py needed
            # Phase file: either {phase}.py or {phase}_phase.py (for 'export' collision)
            # Also check underscore variant: phase-complete -> phase_complete.py
            phase_under = phase.replace("-", "_")
            candidates = [
                pkg_path / f"{phase}.py",
                pkg_path / f"{phase}_phase.py",
                pkg_path / f"{phase_under}.py",
                pkg_path / f"{phase_under}_phase.py",
            ]
            if not any(c.exists() for c in candidates):
                errors.append(f"{dname}/{phase}.py")

    if errors:
        _fail("H22", f"missing phase files: {'; '.join(errors)}")
    else:
        migrated = len(domains) - len(skipped)
        _pass("H22", f"all migrated domains ({migrated}) have phase files for their workflows")


def check_h23(teams: dict[str, Any], domains_dir: Path) -> None:
    """H23: Each migrated domain __init__.py exports DOMAIN_EXECUTOR."""
    domains = teams.get("domains", {})

    errors: list[str] = []
    skipped: list[str] = []

    for dname in domains:
        pkg_name = _domain_to_pkg(dname)
        init_path = domains_dir / pkg_name / "__init__.py"
        if not init_path.exists():
            skipped.append(dname)
            continue

        _, has_executor = _extract_phase_handlers_from_init(init_path)
        if not has_executor:
            errors.append(f"domain '{dname}' ({pkg_name}/__init__.py) missing DOMAIN_EXECUTOR")

    if errors:
        _fail("H23", f"missing DOMAIN_EXECUTOR: {'; '.join(errors)}")
    else:
        migrated = len(domains) - len(skipped)
        _pass("H23", f"all migrated domains ({migrated}) export DOMAIN_EXECUTOR")


def check_h24(teams: dict[str, Any], domains_dir: Path) -> None:
    """H24: PHASE_HANDLERS / inline handlers dict keys match workflow phases.

    Missing handler keys (workflow phases not in handlers) -> FAIL
    Extra handler keys (handlers not in workflow) -> WARN (surplus code, not a runtime error)
    """
    domains = teams.get("domains", {})

    errors: list[str] = []
    warnings: list[str] = []
    skipped: list[str] = []

    for dname, ddata in domains.items():
        pkg_name = _domain_to_pkg(dname)
        init_path = domains_dir / pkg_name / "__init__.py"
        if not init_path.exists():
            skipped.append(dname)
            continue

        phase_keys, _ = _extract_phase_handlers_from_init(init_path)
        if phase_keys is None:
            skipped.append(dname)
            continue

        # Normalize: phase-complete -> phase_complete for comparison
        workflow_raw = set(ddata.get("workflow", [])) - _GATE_PHASES
        workflow_norm = {p.replace("-", "_") for p in workflow_raw}
        phase_keys_norm = {p.replace("-", "_") for p in phase_keys}
        missing = workflow_norm - phase_keys_norm
        extra = phase_keys_norm - workflow_norm - {g.replace("-", "_") for g in _GATE_PHASES}
        if missing:
            errors.append(f"{dname}: workflow phases missing from handlers: {missing}")
        if extra:
            warnings.append(f"{dname}: extra handler keys not in workflow: {sorted(extra)}")

    for w in warnings:
        _warn("H24", w)

    if errors:
        _fail("H24", f"handler/workflow mismatch: {'; '.join(errors)}")
    else:
        validated = len(domains) - len(skipped)
        _pass("H24", f"all workflow phases covered by handlers for {validated} domains")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate teams.yaml + learned-rules.yaml v2.0 schema")
    script_dir = Path(__file__).resolve().parent
    default_refs = script_dir.parent / "references"
    # Default domains dir: projects/platform/automation_engine/domains/
    default_domains_dir = script_dir.parents[1] / "platform" / "automation_engine" / "domains"

    parser.add_argument("--teams-yaml", type=Path, default=default_refs / "config" / "teams.yaml",
                        help="Path to teams.yaml")
    parser.add_argument("--rules-yaml", type=Path, default=default_refs / "rules" / "learned-rules.yaml",
                        help="Path to learned-rules.yaml (or directory of domain YAMLs)")
    parser.add_argument("--domains-dir", type=Path, default=default_domains_dir,
                        help="Path to automation_engine/domains/ directory")
    args = parser.parse_args()

    print("=== validate_schema_v2.py ===")
    print(f"  teams.yaml:   {args.teams_yaml}")
    print(f"  rules.path:   {args.rules_yaml}")
    print(f"  domains.dir:  {args.domains_dir}")
    print()

    # Load files
    try:
        with open(args.teams_yaml) as f:
            teams = yaml.safe_load(f)
    except Exception as e:
        print(f"[FAIL] LOAD: Cannot load teams.yaml: {e}")
        return 1

    try:
        rules_path = args.rules_yaml
        if rules_path.is_file():
            with open(rules_path) as f:
                rules_data = yaml.safe_load(f)
            rules_list: list[dict[str, Any]] = rules_data.get("rules", [])
        elif rules_path.is_dir() or rules_path.parent.is_dir():
            # ドメイン分割: references/rules/ ディレクトリの全 YAML を結合
            rules_dir = rules_path if rules_path.is_dir() else rules_path.parent
            rules_list = []
            for yaml_file in sorted(rules_dir.glob("*.yaml")):
                if yaml_file.name in ("improvement-backlog.yaml",):
                    continue
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                if data and isinstance(data.get("rules"), list):
                    rules_list.extend(data["rules"])
            if not rules_list:
                print(f"[FAIL] LOAD: No rules found in {rules_dir}")
                return 1
            print(f"  rules.loaded: {len(rules_list)} rules from {rules_dir}")
        else:
            print(f"[FAIL] LOAD: Cannot find rules at {rules_path}")
            return 1
    except Exception as e:
        print(f"[FAIL] LOAD: Cannot load learned-rules: {e}")
        return 1
    common_phases: list[str] = teams.get("common_phases", [])
    domain_names: set[str] = set(teams.get("domains", {}).keys())

    # --- A. Basic Schema Checks ---
    check_a1(teams)
    check_a2(teams)
    check_a3(teams)
    check_a4(teams)
    check_a5(teams)

    # --- B. Bidirectional Reference Check ---
    check_b6_b7(teams)

    # --- C. skill_mapping <-> domains Consistency ---
    check_c9_c10_c11_c12_c13(teams)

    # --- D. resolve_actors Verification ---
    check_d14(teams)

    # --- E. Rule Binding Checks ---
    check_e15(rules_list)
    check_e16(rules_list, common_phases)
    check_e17(rules_list, domain_names)

    # --- F. Governance Checks ---
    check_f18(teams)
    check_f19(teams)

    # --- G. Workflow Format Checks ---
    check_g20(teams)

    # --- H. Domain Package Cross-Validation ---
    if args.domains_dir.is_dir():
        check_h21(teams, args.domains_dir)
        check_h22(teams, args.domains_dir)
        check_h23(teams, args.domains_dir)
        check_h24(teams, args.domains_dir)
    else:
        _warn("H21-H24", f"domains directory not found: {args.domains_dir} — skipping domain package checks")

    # --- Summary ---
    print()
    print(f"=== Result: {PASS_COUNT} PASS, {WARN_COUNT} WARN, {FAIL_COUNT} FAIL ===")

    return 1 if FAIL_COUNT > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
