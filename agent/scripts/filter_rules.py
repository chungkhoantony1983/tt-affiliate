#!/usr/bin/env python3
"""IMP-035: learned-rules.yaml のリポ向けフィルタリング。

sync.sh から呼ばれ、scope.repos ベースでルールを配信先リポにフィルタする。
ドメインフィルタは行わない（scope.repos のみ判定）。

Usage:
    python3 filter_rules.py \
        --input /path/to/learned-rules.yaml \
        --registry /path/to/repo-registry.md \
        --repo ea \
        --output /path/to/filtered-learned-rules.yaml \
        --manifest /path/to/.filter-manifest.yaml
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    # sync.sh 環境で yaml がない場合はフィルタなしでコピー
    print("WARNING: PyYAML not installed. Copying without filtering.", file=sys.stderr)
    sys.exit(2)


def normalize_scope(scope: Any) -> dict[str, Any] | None:
    """scope フィールドを v1.3 構造化形式に正規化。"""
    if scope is None:
        return None
    if isinstance(scope, str):
        return {"project": scope}
    if isinstance(scope, dict):
        return scope
    return None


def parse_registry(registry_path: Path) -> tuple[set[str], dict[str, str]]:
    """repo-registry.md からリポ短縮名セットとディレクトリ名→短縮名マッピングを取得。

    Returns:
        (short_names, dir_to_short) — dir_to_short はディレクトリ名から短縮名への辞書
    """
    repos: set[str] = set()
    dir_to_short: dict[str, str] = {}
    text = registry_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = re.match(r"^\|\s*([\w-]+)\s*\|\s*(\S+)\s*\|", line)
        if m and m.group(1) not in ("短縮名",):
            short_name = m.group(1)
            repo_path = m.group(2)  # e.g., "org/platform-functions"
            repos.add(short_name)
            # ディレクトリ名 = GitHub パスの最後のコンポーネント
            dir_name = repo_path.rstrip("/").rsplit("/", 1)[-1]
            dir_to_short[dir_name] = short_name
            dir_to_short[short_name] = short_name  # 短縮名自体もマッピング
    return repos, dir_to_short


def _filter_rule_list(
    rules: list[dict[str, Any]],
    repo_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """ルールリストをフィルタし、(kept, excluded) を返す。"""
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for rule in rules:
        scope = normalize_scope(rule.get("scope"))
        repos = scope.get("repos") if scope else None

        if repos and isinstance(repos, list) and repo_name not in repos:
            excluded.append({
                "id": rule.get("id", "?"),
                "reason": f"scope.repos={repos}, current={repo_name}",
            })
        else:
            kept.append(rule)

    return kept, excluded


def filter_rules(
    input_yaml: dict[str, Any],
    repo_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """scope.repos でルールをフィルタリング。

    v1.x（global/domains 構造）と v2.0（flat rules[] 構造）の両方に対応。

    Returns:
        (filtered_yaml, excluded_rules)
    """
    filtered = copy.deepcopy(input_yaml)
    all_excluded: list[dict[str, Any]] = []

    # v2.0: flat rules[] 構造
    if "rules" in filtered and isinstance(filtered["rules"], list):
        kept, excluded = _filter_rule_list(filtered["rules"], repo_name)
        filtered["rules"] = kept
        all_excluded.extend(excluded)
        return filtered, all_excluded

    # v1.x: Global section
    global_section = filtered.get("global", {})
    if isinstance(global_section, dict):
        for key in ("constraints", "processes"):
            rules = global_section.get(key, [])
            if isinstance(rules, list):
                kept, excluded = _filter_rule_list(rules, repo_name)
                global_section[key] = kept
                all_excluded.extend(excluded)

    # v1.x: Domains section
    domains = filtered.get("domains", {})
    if isinstance(domains, dict):
        for domain_name, domain_data in domains.items():
            if not isinstance(domain_data, dict):
                continue
            for key in ("constraints", "processes"):
                rules = domain_data.get(key, [])
                if isinstance(rules, list):
                    kept, excluded = _filter_rule_list(rules, repo_name)
                    domain_data[key] = kept
                    all_excluded.extend(excluded)

    return filtered, all_excluded


def write_manifest(
    manifest_path: Path,
    repo_name: str,
    source_count: int,
    delivered_count: int,
    excluded: list[dict[str, Any]],
) -> None:
    """フィルタマニフェストを YAML で書き出す。"""
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": repo_name,
        "source_rules_count": source_count,
        "delivered_rules_count": delivered_count,
        "excluded_count": len(excluded),
        "excluded": excluded,
    }
    manifest_path.write_text(
        yaml.dump(manifest, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _count_rules(data: dict[str, Any]) -> int:
    """YAML 内の全ルール数をカウント。v1.x と v2.0 の両方に対応。"""
    # v2.0: flat rules[]
    if "rules" in data and isinstance(data["rules"], list):
        return len(data["rules"])
    # v1.x
    count = 0
    global_section = data.get("global", {})
    if isinstance(global_section, dict):
        count += len(global_section.get("constraints", []))
        count += len(global_section.get("processes", []))
    domains = data.get("domains", {})
    if isinstance(domains, dict):
        for d in domains.values():
            if isinstance(d, dict):
                count += len(d.get("constraints", []))
                count += len(d.get("processes", []))
    return count


def _load_input(input_path: Path) -> dict[str, Any] | None:
    """入力を読み込む。ファイルまたはディレクトリ（IMP-072）に対応。"""
    if input_path.is_dir():
        # ディレクトリ: 全 *.yaml をマージして v2.0 形式で返す
        all_rules: list[dict] = []
        all_style_configs: dict[str, Any] = {}
        for yf in sorted(input_path.glob("*.yaml")):
            if yf.name == "improvement-backlog.yaml" or yf.name.endswith(".bak"):
                continue
            with open(yf, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if isinstance(data, dict):
                all_rules.extend(data.get("rules", []))
                sc = data.get("style_configs", {})
                if isinstance(sc, dict):
                    all_style_configs.update(sc)
        merged = {"schema_version": "2.0", "rules": all_rules}
        if all_style_configs:
            merged["style_configs"] = all_style_configs
        return merged
    elif input_path.is_file():
        with open(input_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return raw if isinstance(raw, dict) else None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="learned-rules リポ向けフィルタ")
    parser.add_argument("--input", "-i", required=True, help="SSoT learned-rules.yaml またはルールディレクトリ")
    parser.add_argument("--registry", "-r", required=True, help="repo-registry.md")
    parser.add_argument("--repo", required=True, help="配信先リポ短縮名")
    parser.add_argument("--output", "-o", required=True, help="フィルタ済み出力先")
    parser.add_argument("--manifest", "-m", help="フィルタマニフェスト出力先")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 1

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"ERROR: registry not found: {registry_path}", file=sys.stderr)
        return 1

    # 入力読み込み（IMP-072: ディレクトリ対応）
    raw = _load_input(input_path)
    if raw is None:
        print("ERROR: input is not a valid YAML dict or directory", file=sys.stderr)
        return 1

    # リポ名検証（ディレクトリ名→短縮名の解決を含む）
    known_repos, dir_to_short = parse_registry(registry_path)
    repo_name = dir_to_short.get(args.repo, args.repo)  # ディレクトリ名→短縮名に解決

    if repo_name not in known_repos:
        print(f"WARNING: repo '{args.repo}' not in registry. Copying without filter.", file=sys.stderr)
        # フィルタなしでそのままコピー
        Path(args.output).write_text(
            yaml.dump(raw, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        return 0

    source_count = _count_rules(raw)

    # フィルタ実行
    filtered, excluded = filter_rules(raw, repo_name)
    delivered_count = _count_rules(filtered)

    # 出力
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        yaml.dump(filtered, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    # マニフェスト
    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        write_manifest(manifest_path, repo_name, source_count, delivered_count, excluded)

    # サマリ出力
    if excluded:
        print(f"  filtered: {source_count} → {delivered_count} rules ({len(excluded)} excluded)")
    else:
        print(f"  delivered: {delivered_count} rules (no exclusions)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
