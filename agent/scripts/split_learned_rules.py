#!/usr/bin/env python3
"""learned-rules.yaml を domain 別 YAML ファイルに分割する。

IMP-072: ルール管理の構造的改善 — モノリシック YAML をドメイン別ファイルに分割。

Usage:
    python split_learned_rules.py [--dry-run]
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import yaml


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    rules_dir = Path(__file__).resolve().parent.parent / "references" / "rules"
    source = rules_dir / "learned-rules.yaml"

    if not source.exists():
        print(f"ERROR: {source} not found")
        sys.exit(1)

    with open(source) as f:
        data = yaml.safe_load(f) or {}

    rules = data.get("rules", [])
    style_configs = data.get("style_configs", {})

    # Classify rules by domain
    domain_rules: dict[str, list[dict]] = defaultdict(list)

    for rule in rules:
        binding = rule.get("binding", {})
        level = binding.get("level", "company")

        if level == "company":
            domain_rules["global"].append(rule)
        elif level == "domain":
            target = binding.get("target", "global")
            domain_rules[target].append(rule)
        elif level in ("skill", "persona", "phase"):
            # These go to global (v2.0 compat)
            domain_rules["global"].append(rule)
        else:
            domain_rules["global"].append(rule)

    # Map style_configs to domains
    domain_styles: dict[str, dict] = {}
    for name, sc in style_configs.items():
        domain_styles[name] = sc

    # Report
    total = 0
    for domain, dr in sorted(domain_rules.items()):
        print(f"  {domain}: {len(dr)} rules")
        total += len(dr)
    print(f"  TOTAL: {total} rules (original: {len(rules)})")

    if total != len(rules):
        print("ERROR: Rule count mismatch!")
        sys.exit(1)

    # Write domain files
    for domain in sorted(set(list(domain_rules.keys()) + list(domain_styles.keys()))):
        domain_data: dict = {
            "schema_version": "2.0",
            "domain": domain,
        }
        if domain in domain_rules:
            domain_data["rules"] = domain_rules[domain]
        if domain in domain_styles:
            domain_data["style_configs"] = {domain: domain_styles[domain]}

        filename = f"{domain}.yaml"
        target_path = rules_dir / filename

        if dry_run:
            rule_count = len(domain_rules.get(domain, []))
            has_style = domain in domain_styles
            print(f"  [DRY-RUN] Would write {target_path.name}: {rule_count} rules, style={has_style}")
        else:
            with open(target_path, "w") as f:
                yaml.dump(
                    domain_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    width=120,
                )
            rule_count = len(domain_rules.get(domain, []))
            print(f"  Wrote {target_path.name}: {rule_count} rules")

    if not dry_run:
        # Rename original file as backup
        backup = rules_dir / "learned-rules.yaml.bak"
        source.rename(backup)
        print(f"\n  Original backed up to {backup.name}")
        print("  Split complete!")


if __name__ == "__main__":
    main()
