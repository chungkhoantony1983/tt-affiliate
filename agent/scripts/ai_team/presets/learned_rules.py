"""LearnedRulesConfig — learned-rules.yaml の読み込み・検証・ルール合成。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .discovery import _find_learned_rules_dir, _find_learned_rules_yaml, normalize_scope


@dataclass
class DomainRules:
    """learned-rules.yaml の各ドメインルール。"""

    constraints: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    style_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class LearnedRulesConfig:
    """learned-rules.yaml — 全社横断の学習ルール SSoT。

    sync.sh で全リポの .claude/references/ にコピーされ、
    各スキルの Step 0 で自動参照される。
    """

    schema_version: str = "1.0"
    global_constraints: list[dict[str, Any]] = field(default_factory=list)
    global_processes: list[dict[str, Any]] = field(default_factory=list)
    domain_rules: dict[str, DomainRules] = field(default_factory=dict)
    _path: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, path: str | Path | None = None) -> LearnedRulesConfig:
        """learned-rules.yaml またはドメイン別 YAML ディレクトリを読み込む。

        IMP-072: ドメイン別分割対応。以下の優先順位で読み込む:
        1. path が明示指定 → そのファイル/ディレクトリを読む
        2. 単一 learned-rules.yaml が存在 → 従来通り読む（後方互換）
        3. rules/ ディレクトリにドメイン別 YAML が存在 → マージして読む
        4. いずれもなし → 空デフォルト
        """
        if path:
            p = Path(path)
            if p.is_dir():
                return cls._load_from_dir(p)
            if p.exists():
                return cls._load_single_file(p)
            return cls()

        # 1. 単一ファイル（後方互換）
        single = _find_learned_rules_yaml()
        if single and single.exists():
            return cls._load_single_file(single)

        # 2. ドメイン別ディレクトリ
        rules_dir = _find_learned_rules_dir()
        if rules_dir:
            return cls._load_from_dir(rules_dir)

        return cls()

    @classmethod
    def _load_single_file(cls, config_path: Path) -> LearnedRulesConfig:
        """単一 YAML ファイルからの読み込み（従来の load ロジック）。"""
        with open(config_path) as f:
            try:
                raw: dict[str, Any] = yaml.safe_load(f) or {}
            except yaml.YAMLError:
                return cls()

        if not isinstance(raw, dict):
            return cls()

        return cls._load_v2(raw, config_path)

    @classmethod
    def _load_from_dir(cls, rules_dir: Path) -> LearnedRulesConfig:
        """ドメイン別 YAML ディレクトリからマージ読み込み。

        IMP-072: rules/ 内の全 *.yaml を読み込み、単一 LearnedRulesConfig に合成する。
        各ファイルは v2.0 フォーマット（domain, rules[], style_configs）。
        """
        all_rules: list[dict[str, Any]] = []
        all_style_configs: dict[str, Any] = {}

        yamls = sorted(
            f for f in rules_dir.glob("*.yaml")
            if f.name != "improvement-backlog.yaml"
            and not f.name.endswith(".bak")
        )

        for yf in yamls:
            try:
                with open(yf) as f:
                    raw = yaml.safe_load(f) or {}
            except yaml.YAMLError:
                continue
            if not isinstance(raw, dict):
                continue
            all_rules.extend(raw.get("rules", []))
            sc = raw.get("style_configs", {})
            if isinstance(sc, dict):
                all_style_configs.update(sc)

        merged: dict[str, Any] = {
            "schema_version": "2.0",
            "rules": all_rules,
            "style_configs": all_style_configs,
        }
        return cls._load_v2(merged, rules_dir)

    @classmethod
    def _load_v2(cls, raw: dict[str, Any], config_path: Path) -> LearnedRulesConfig:
        """v2.0 フォーマットのロード。flat rules[] → v1.x 互換構造に変換。

        変換ルール:
        - binding.level==company → global_constraints（全ルール）
        - binding.level==domain → domain_rules[target].constraints
        - binding.level==skill → global_constraints（スキル実行時にフィルタ。v1互換で保持）
        - binding.level==persona → global_constraints（ペルソナ参照時にフィルタ）
        - binding.level==phase → global_constraints（フェーズレベル、ドメイン横断で共有）
        - style_configs → domain_rules[name].style_config
        """
        global_constraints: list[dict[str, Any]] = []
        domain_map: dict[str, DomainRules] = {}

        for rule in raw.get("rules", []):
            if not isinstance(rule, dict):
                continue
            binding = rule.get("binding", {})
            level = binding.get("level", "company")

            if level in ("company", "skill", "persona", "phase"):
                global_constraints.append(rule)
            elif level == "domain":
                target = binding.get("target", "")
                if target not in domain_map:
                    domain_map[target] = DomainRules()
                domain_map[target].constraints.append(rule)

        # style_configs → domain_rules[name].style_config
        style_configs = raw.get("style_configs", {})
        if not isinstance(style_configs, dict):
            style_configs = {}
        for name, sc in style_configs.items():
            if name not in domain_map:
                domain_map[name] = DomainRules()
            domain_map[name].style_config = sc

        lr = cls(
            schema_version=raw.get("schema_version", "2.0"),
            global_constraints=global_constraints,
            global_processes=[],  # v2.0 では constraint/process 区別なし
            domain_rules=domain_map,
        )
        lr._path = config_path
        return lr

    def get_rules_for_domain(
        self, domain: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        """指定ドメインの (constraints, processes, style_config) を返す。

        Global ルールとドメイン固有ルールをマージして返す。
        style_config に ``inherit`` キーがある場合は参照先ドメインの
        style_config を解決してマージする。
        """
        dr = self.domain_rules.get(domain, DomainRules())
        constraints = self.global_constraints + dr.constraints
        processes = self.global_processes + dr.processes
        style = self._resolve_style_config(dr.style_config)
        return constraints, processes, style

    def resolve_rules(
        self, domain: str, phase: str,
    ) -> dict[str, Any]:
        """4レベルルール合成: company → phase → domain → domain×phase。

        WorkflowEngine が各フェーズ実行時に呼び出す。
        binding モデル (v2.0) に基づき、該当するルールのみをフィルタして合成する。

        Returns:
            {"constraints": [...], "processes": [...], "style_config": {...}}
        """
        # Level 1: company（全ドメイン共通）
        company_rules = [
            r for r in self.global_constraints
            if r.get("binding", {}).get("level") == "company"
        ]

        # Level 2: phase（ドメイン横断のフェーズ共通）
        phase_rules = [
            r for r in self.global_constraints
            if r.get("binding", {}).get("level") == "phase"
            and r.get("binding", {}).get("target") == phase
        ]

        # Level 3 & 4: domain (phase なし) + domain×phase
        dr = self.domain_rules.get(domain, DomainRules())
        domain_only = []
        domain_phase = []
        for r in dr.constraints:
            binding = r.get("binding", {})
            bound_phase = binding.get("phase")
            if bound_phase is None:
                # Level 3: domain（フェーズ指定なし）
                domain_only.append(r)
            elif bound_phase == phase:
                # Level 4: domain×phase
                domain_phase.append(r)
            # else: 別フェーズ向け → スキップ

        # 合成（優先順位: company < phase < domain < domain×phase）
        constraints = company_rules + phase_rules + domain_only + domain_phase

        # processes は get_rules_for_domain 互換（全マージ）
        processes = self.global_processes + dr.processes

        # style_config は inherit 解決済み
        style = self._resolve_style_config(dr.style_config)

        return {
            "constraints": constraints,
            "processes": processes,
            "style_config": style,
        }

    def _resolve_style_config(
        self, style: dict[str, Any], _visited: set[str] | None = None,
    ) -> dict[str, Any]:
        """style_config の inherit を解決し、inherit キーを除去して返す。

        循環参照を検出した場合は inherit を無視して自身のスタイルのみ返す。
        """
        if not style:
            return style
        inherit_from = style.get("inherit")
        if not inherit_from:
            return style
        if _visited is None:
            _visited = set()
        if inherit_from in _visited:
            # 循環検出: inherit を無視して自身のスタイルのみ返す
            return {k: v for k, v in style.items() if k != "inherit"}
        _visited.add(inherit_from)
        # inherit 先のドメインから style_config を取得
        parent_dr = self.domain_rules.get(inherit_from, DomainRules())
        parent_style = self._resolve_style_config(parent_dr.style_config, _visited)
        # 親のスタイルに自身の値を上書きマージ（inherit キーは除去）
        merged = {**parent_style}
        for k, v in style.items():
            if k != "inherit":
                merged[k] = v
        return merged

    def get_constraints_for_prompt(
        self,
        domain: str,
        *,
        exclude_scoped: bool = True,
    ) -> str:
        """プロンプト注入用に Global + ドメイン constraints を整形テキストで返す。"""
        constraints, _, _ = self.get_rules_for_domain(domain)
        if exclude_scoped:
            constraints = [r for r in constraints if not r.get("scope")]
        if not constraints:
            return ""
        return "\n".join(
            f"- [{r.get('id', '?')}] {r.get('rule', '')}" for r in constraints
        )

    def get_processes_for_prompt(self, domain: str) -> str:
        """プロンプト注入用に Global + ドメイン processes を整形テキストで返す。"""
        _, processes, _ = self.get_rules_for_domain(domain)
        if not processes:
            return ""
        return "\n".join(
            f"- [{r.get('id', '?')}] {r.get('rule', '')}" for r in processes
        )

    def get_enforced_rules_for_system_prompt(self, domain: str) -> str:
        """hook_strict / hook_fuzzy ルールをシステムプロンプト注入用テキストで返す。

        AI が自主的に読み込まなくてもシステムプロンプトに強制埋め込みされるため、
        ルール忘れ・スキップを防止する。
        """
        constraints, processes, _ = self.get_rules_for_domain(domain)
        enforced = []
        for r in constraints + processes:
            enforcement = r.get("enforcement_type", "prose_gate")
            if enforcement in ("hook_strict", "hook_fuzzy"):
                level = "MUST" if enforcement == "hook_strict" else "SHOULD"
                enforced.append(f"- [{r.get('id', '?')}][{level}] {r.get('rule', '')}")
        if not enforced:
            return ""
        header = "=== 強制ルール（自動注入 — 違反時はエラー） ==="
        return header + "\n" + "\n".join(enforced)

    def validate(
        self, *, known_repos: set[str] | None = None,
        known_domains: set[str] | None = None,
    ) -> list["ValidationError"]:
        """learned-rules.yaml のスキーマを検証。

        Args:
            known_repos: 既知のリポ短縮名セット。指定時に scope.repos を検証する。
            known_domains: teams.yaml で定義済みのドメイン名セット。
                指定時に learned-rules.yaml のドメインが teams.yaml に存在するか検証する。
        """
        from .teams_config import ValidationError

        errors: list[ValidationError] = []

        # IMP-046: improvement-backlog.yaml から完了済み改善計画を取得
        _done_improvements: set[str] = set()
        if self._path:
            # _path はファイルまたはディレクトリ（IMP-072 分割後）
            base = self._path if self._path.is_dir() else self._path.parent
            backlog_path = base / "improvement-backlog.yaml"
            if backlog_path.exists():
                try:
                    import yaml as _yaml
                    with open(backlog_path, encoding="utf-8") as _f:
                        backlog_data = _yaml.safe_load(_f) or {}
                    for item in backlog_data.get("items", []):
                        if isinstance(item, dict) and item.get("status") == "done":
                            _done_improvements.add(item.get("id", ""))
                except Exception:
                    pass  # backlog 読み込み失敗はバリデーション本体に影響させない

        def _validate_rule(rule: dict, path: str, *, is_global: bool) -> None:
            if "id" not in rule:
                errors.append(ValidationError(path, "'id' フィールドが必須"))
            if "rule" not in rule:
                errors.append(ValidationError(path, "'rule' フィールドが必須"))

            # IMP-046: scope 検証（v1.3 構造化 + v1.2 文字列の後方互換）
            raw_scope = rule.get("scope")
            scope = normalize_scope(raw_scope)
            # v2.0: binding.level==company のルールの scope チェック
            binding = rule.get("binding", {})
            is_company = is_global or binding.get("level") == "company"
            if is_company and scope:
                errors.append(ValidationError(
                    path,
                    f"Global ルール '{rule.get('id', '?')}' に scope が設定されています。"
                    " Global ルールは全リポに適用されるため scope は不要です",
                ))
            if scope and known_repos:
                repos = scope.get("repos", [])
                if isinstance(repos, list):
                    for repo in repos:
                        if repo not in known_repos:
                            errors.append(ValidationError(
                                path,
                                f"scope.repos に未知のリポ '{repo}' が指定されています。"
                                f" 既知のリポ: {', '.join(sorted(known_repos))}",
                            ))

            # IMP-046: bridge ルールの linked_improvement チェック
            if rule.get("type") == "bridge":
                imp_id = rule.get("linked_improvement")
                if not imp_id:
                    errors.append(ValidationError(
                        path,
                        f"bridge ルール '{rule.get('id', '?')}' に linked_improvement がありません。"
                        " bridge ルールは改善計画と紐付けが必須です",
                    ))
                elif imp_id in _done_improvements:
                    errors.append(ValidationError(
                        path,
                        f"bridge ルール '{rule.get('id', '?')}' の改善計画 {imp_id} は完了済みです。"
                        " このルールを削除してください",
                    ))

            # enforcement_type 検証
            etype = rule.get("enforcement_type")
            valid_types = {"hook_strict", "hook_fuzzy", "phase_py", "prose_gate"}
            if etype and etype not in valid_types:
                errors.append(ValidationError(
                    path,
                    f"'{rule.get('id', '?')}' の enforcement_type '{etype}' は無効です。"
                    f" 有効値: {', '.join(sorted(valid_types))}",
                ))
            if etype is None:
                errors.append(ValidationError(
                    path,
                    f"'{rule.get('id', '?')}' に enforcement_type が未設定です。"
                    " hook_strict→hook_fuzzy→phase_py→prose_gate のデシジョンツリーで判定してください",
                ))

        # Global constraints
        for i, c in enumerate(self.global_constraints):
            _validate_rule(c, f"global.constraints[{i}]", is_global=True)

        # Global processes
        for i, p in enumerate(self.global_processes):
            _validate_rule(p, f"global.processes[{i}]", is_global=True)

        # Domain rules
        for name, dr in self.domain_rules.items():
            for i, c in enumerate(dr.constraints):
                _validate_rule(c, f"domains.{name}.constraints[{i}]", is_global=False)
            for i, p in enumerate(dr.processes):
                _validate_rule(p, f"domains.{name}.processes[{i}]", is_global=False)

        # ドメイン存在チェック（learned-rules.yaml のドメインが teams.yaml に定義されているか）
        if known_domains:
            for name in self.domain_rules:
                if name not in known_domains:
                    errors.append(ValidationError(
                        f"domains.{name}",
                        f"ドメイン '{name}' は teams.yaml に定義されていません。"
                        f" 既知のドメイン: {', '.join(sorted(known_domains))}",
                    ))

        # ID 重複チェック
        all_ids: list[tuple[str, str]] = []
        for c in self.global_constraints:
            all_ids.append((c.get("id", ""), "global.constraints"))
        for p in self.global_processes:
            all_ids.append((p.get("id", ""), "global.processes"))
        for name, dr in self.domain_rules.items():
            for c in dr.constraints:
                all_ids.append((c.get("id", ""), f"domains.{name}.constraints"))
            for p in dr.processes:
                all_ids.append((p.get("id", ""), f"domains.{name}.processes"))
        seen: dict[str, str] = {}
        for rule_id, location in all_ids:
            if not rule_id:
                continue
            if rule_id in seen:
                errors.append(ValidationError(
                    location,
                    f"ID '{rule_id}' が重複 (先行: {seen[rule_id]})",
                ))
            else:
                seen[rule_id] = location

        # enforcement 統計（警告レベル: error ではなく info）
        enforcement_stats: dict[str, int] = {}
        for c in self.global_constraints:
            et = c.get("enforcement_type", "none")
            enforcement_stats[et] = enforcement_stats.get(et, 0) + 1
        for p in self.global_processes:
            et = p.get("enforcement_type", "none")
            enforcement_stats[et] = enforcement_stats.get(et, 0) + 1
        for dr in self.domain_rules.values():
            for c in dr.constraints:
                et = c.get("enforcement_type", "none")
                enforcement_stats[et] = enforcement_stats.get(et, 0) + 1
            for p in dr.processes:
                et = p.get("enforcement_type", "none")
                enforcement_stats[et] = enforcement_stats.get(et, 0) + 1
        self._enforcement_stats = enforcement_stats

        return errors
