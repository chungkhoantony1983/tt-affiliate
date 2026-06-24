"""TeamsConfig — teams.yaml の読み込み・検証・フィードバック管理。"""

from __future__ import annotations

import fcntl
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from .discovery import _find_teams_yaml

VALID_WORKFLOW_TYPES = frozenset({"consensus", "vote", "pipeline", "specialty"})


@dataclass
class DomainPreset:
    """ビジネスドメイン（業務領域）のプリセット定義。"""

    label: str
    workflow_type: str = ""
    description: str = ""
    personas: list[dict[str, Any]] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    dimension_leads: dict[str, list[str]] = field(default_factory=dict)
    workflows: dict[str, dict[str, Any]] = field(default_factory=dict)
    quality_rules: list[dict[str, Any]] = field(default_factory=list)
    # 構造化フィールド（quality_rules を性質別に分離）
    constraints: list[dict[str, Any]] = field(default_factory=list)
    style_config: dict[str, Any] = field(default_factory=dict)
    processes: list[dict[str, Any]] = field(default_factory=list)
    # v2.0 フィールド（後方互換: デフォルトは空）
    persona_refs: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    workflow_phases: list[str] = field(default_factory=list)
    orchestration: dict[str, Any] = field(default_factory=dict)

    def get_constraints_for_prompt(
        self, *, exclude_scoped: bool = True,
    ) -> str:
        """プロンプト注入用に constraints を整形テキストで返す。

        Args:
            exclude_scoped: True の場合、scope タグ付き（PJ固有）ルールを除外。
        """
        rules = self.constraints
        if exclude_scoped:
            rules = [r for r in rules if not r.get("scope")]
        if not rules:
            return ""
        return "\n".join(
            f"- [{r.get('id', '?')}] {r.get('rule', '')}" for r in rules
        )

    def get_style_config_section(self) -> str:
        """プロンプト注入用に style_config を YAML テキストで返す。"""
        if not self.style_config:
            return ""
        return yaml.dump(
            self.style_config, default_flow_style=False, allow_unicode=True,
        )


@dataclass
class ValidationError:
    """スキーマ検証エラー。"""

    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.path}] {self.message}"


@dataclass
class TeamsConfig:
    """teams.yaml の全体構造。"""

    domains: dict[str, DomainPreset] = field(default_factory=dict)
    routing: dict[str, str] = field(default_factory=dict)
    voters: list[str] = field(default_factory=list)
    pipelines: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    themes: dict[str, dict[str, Any]] = field(default_factory=dict)
    feedback: list[dict[str, Any]] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    # v2.0 top-level fields（後方互換: デフォルトは空）
    company: dict[str, Any] = field(default_factory=dict)
    personas_registry: dict[str, dict[str, Any]] = field(default_factory=dict)
    common_phases: list[str] = field(default_factory=list)
    skill_mapping: dict[str, str | None] = field(default_factory=dict)
    _path: Path | None = field(default=None, repr=False)

    @classmethod
    def load(cls, path: str | Path | None = None) -> TeamsConfig:
        """teams.yaml を読み込む。存在しなければ空のデフォルトを返す。"""
        config_path = Path(path) if path else _find_teams_yaml()
        if not config_path or not config_path.exists():
            return cls()

        with open(config_path) as f:
            raw: dict[str, Any] = yaml.safe_load(f) or {}

        tc = cls._from_dict(raw)
        tc._path = config_path
        return tc

    @classmethod
    def _from_dict(cls, raw: dict[str, Any]) -> TeamsConfig:
        domains: dict[str, DomainPreset] = {}
        for name, d in raw.get("domains", {}).items():
            # v2: workflow フィールドが list の場合は workflow_phases として読む
            raw_workflow = d.get("workflow")
            workflow_phases: list[str] = (
                raw_workflow if isinstance(raw_workflow, list) else []
            )

            domains[name] = DomainPreset(
                label=d.get("label", name),
                workflow_type=d.get("workflow_type", ""),
                description=d.get("description", ""),
                personas=d.get("personas", []),
                dimensions=d.get("dimensions", []),
                dimension_leads=d.get("dimension_leads", {}),
                workflows=d.get("workflows", {}),
                quality_rules=d.get("quality_rules", []),
                constraints=d.get("constraints", []),
                style_config=d.get("style_config", {}),
                processes=d.get("processes", []),
                # v2.0 domain fields
                persona_refs=d.get("persona_refs", []),
                skills=d.get("skills", []),
                workflow_phases=workflow_phases,
                orchestration=d.get("orchestration", {}),
            )

        return cls(
            domains=domains,
            routing=raw.get("routing", {}),
            voters=raw.get("voters", []),
            pipelines=raw.get("pipelines", {}),
            themes=raw.get("themes", {}),
            feedback=raw.get("feedback", []),
            metrics=raw.get("metrics", []),
            # v2.0 top-level fields
            company=raw.get("company", {}),
            personas_registry=raw.get("personas", {}),
            common_phases=raw.get("common_phases", []),
            skill_mapping=raw.get("skill_mapping", {}),
        )

    def get_domain(self, name: str) -> DomainPreset | None:
        """ドメインプリセットを取得。"""
        return self.domains.get(name)

    def get_workflow_config(self, domain: str, workflow: str) -> dict[str, Any]:
        """ドメイン × ワークフロー のプリセットを取得。"""
        d = self.domains.get(domain)
        if d and workflow in d.workflows:
            return d.workflows[workflow]
        return {}

    # ------------------------------------------------------------------
    # v2.0: ペルソナ・ドメイン解決
    # ------------------------------------------------------------------

    def resolve_actors(self, domain: str, phase: str) -> list[dict[str, Any]]:
        """指定ドメイン・フェーズに適合するペルソナを personas_registry から解決。

        resolve_actors(domain, phase) = persona_refs ∩ {p | phase ∈ p.phase_affinity}

        v2 personas_registry が空の場合は空リストを返す（呼び出し側でフォールバック処理）。
        """
        domain_preset = self.domains.get(domain)
        if not domain_preset:
            return []
        actors = []
        for ref in domain_preset.persona_refs:
            persona = self.personas_registry.get(ref, {})
            if not persona:
                continue
            if phase in persona.get("phase_affinity", []):
                actors.append({"id": ref, **persona})
        return actors

    def resolve_rules(self, domain: str, phase: str) -> dict[str, Any]:
        """4レベルルール合成: company → phase → domain → domain×phase。

        teams.yaml が保持するドメインレベルの制約・プロセス・スタイル設定を合成する。
        company レベル（learned-rules.yaml global）と phase レベルのルールは
        LearnedRulesConfig.resolve_rules() が担当するため、ここでは Level 3/4 を返す。

        Returns:
            {
                "phase": str | None,           # common_phases に含まれるフェーズ名（検証済み）
                "constraints": [...],          # Level 3: ドメイン制約
                "processes": [...],            # Level 3: ドメインプロセス
                "style_config": {...},         # Level 3: ドメインスタイル設定
                "actors": [{"id": ..., ...}],  # フェーズ担当ペルソナ
            }
        """
        result: dict[str, Any] = {
            "phase": None,
            "constraints": [],
            "processes": [],
            "style_config": {},
            "actors": [],
        }

        # Phase validation: common_phases に含まれるフェーズのみ有効
        if self.common_phases and phase in self.common_phases:
            result["phase"] = phase

        # Level 3: Domain (constraints + processes + style_config)
        domain_preset = self.get_domain(domain)
        if domain_preset:
            result["constraints"] = list(domain_preset.constraints)
            result["processes"] = list(domain_preset.processes)
            result["style_config"] = dict(domain_preset.style_config)

        # Actors: persona_refs ∩ phase_affinity
        result["actors"] = self.resolve_actors(domain, phase)

        return result

    def resolve_domain(self, skill_name: str) -> str | None:
        """skill_mapping からスキルに対応するドメインを解決。

        - skill_mapping に存在し値が文字列 → そのドメイン名を返す
        - skill_mapping に存在し値が None/null → None を返す（ルーター）
        - skill_mapping に存在しない → None を返す
        """
        return self.skill_mapping.get(skill_name)

    # ------------------------------------------------------------------
    # バリデーション
    # ------------------------------------------------------------------

    def validate(self) -> list[ValidationError]:
        """teams.yaml のスキーマを検証し、エラーリストを返す。空なら正常。"""
        errors: list[ValidationError] = []

        for name, d in self.domains.items():
            path = f"domains.{name}"

            # workflow_type 検証
            if d.workflow_type and d.workflow_type not in VALID_WORKFLOW_TYPES:
                errors.append(ValidationError(
                    path=f"{path}.workflow_type",
                    message=f"'{d.workflow_type}' は無効。有効値: {', '.join(sorted(VALID_WORKFLOW_TYPES))}",
                ))

            # ペルソナ構造検証
            for i, p in enumerate(d.personas):
                pp = f"{path}.personas[{i}]"
                if "name" not in p:
                    errors.append(ValidationError(pp, "'name' フィールドが必須"))

            # dimension_leads がペルソナ名を参照しているか
            persona_names = {p.get("name") for p in d.personas}
            for dim, leads in d.dimension_leads.items():
                for lead in leads:
                    if lead not in persona_names:
                        errors.append(ValidationError(
                            f"{path}.dimension_leads.{dim}",
                            f"ペルソナ '{lead}' が personas に存在しない",
                        ))

            # constraints 構造検証
            for i, c in enumerate(d.constraints):
                cp = f"{path}.constraints[{i}]"
                if "id" not in c:
                    errors.append(ValidationError(cp, "'id' フィールドが必須"))
                if "rule" not in c:
                    errors.append(ValidationError(cp, "'rule' フィールドが必須"))

            # processes 構造検証
            for i, p in enumerate(d.processes):
                pp = f"{path}.processes[{i}]"
                if "id" not in p:
                    errors.append(ValidationError(pp, "'id' フィールドが必須"))
                if "rule" not in p:
                    errors.append(ValidationError(pp, "'rule' フィールドが必須"))

            # ワークフロー内のモデル spec 形式検証
            for wf_name, wf_config in d.workflows.items():
                wp = f"{path}.workflows.{wf_name}"
                # reviewers リストの spec 形式
                for key in ("reviewers", "models"):
                    for j, spec in enumerate(wf_config.get(key, [])):
                        if isinstance(spec, str) and "/" not in spec:
                            errors.append(ValidationError(
                                f"{wp}.{key}[{j}]",
                                f"'{spec}' は 'provider/model' 形式でない",
                            ))
                # steps リストの spec 形式
                for j, step in enumerate(wf_config.get("steps", [])):
                    if isinstance(step, dict) and "spec" in step:
                        if "/" not in step["spec"]:
                            errors.append(ValidationError(
                                f"{wp}.steps[{j}].spec",
                                f"'{step['spec']}' は 'provider/model' 形式でない",
                            ))

        # routing の spec 形式
        for task_type, spec in self.routing.items():
            if isinstance(spec, str) and "/" not in spec:
                errors.append(ValidationError(
                    f"routing.{task_type}",
                    f"'{spec}' は 'provider/model' 形式でない",
                ))

        # voters の spec 形式（IMP-017）
        for j, spec in enumerate(self.voters):
            if isinstance(spec, str) and "/" not in spec:
                errors.append(ValidationError(
                    f"voters[{j}]",
                    f"'{spec}' は 'provider/model' 形式でない",
                ))

        # pipelines の step 検証
        for preset_name, steps in self.pipelines.items():
            for j, step in enumerate(steps):
                if isinstance(step, dict):
                    if "spec" in step and "/" not in step["spec"]:
                        errors.append(ValidationError(
                            f"pipelines.{preset_name}[{j}].spec",
                            f"'{step['spec']}' は 'provider/model' 形式でない",
                        ))

        return errors

    # ------------------------------------------------------------------
    # フィードバック
    # ------------------------------------------------------------------

    def save_feedback(self, domain: str, change: str, rationale: str = "") -> None:
        """フィードバックを teams.yaml の feedback セクションに追記。

        ファイルロック（fcntl.LOCK_EX）で並行書き込みによるデータ消失を防止。
        """
        if not self._path or not self._path.exists():
            return

        with open(self._path, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                raw: dict[str, Any] = yaml.safe_load(f) or {}

                fb_list = raw.setdefault("feedback", [])
                fb_list.append({
                    "date": date.today().isoformat(),
                    "domain": domain,
                    "change": change,
                    "rationale": rationale,
                })

                f.seek(0)
                f.truncate()
                yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def record_metric(
        self,
        domain: str,
        workflow: str,
        model: str,
        latency_ms: float,
        success: bool,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """実行メトリクスを teams.yaml の metrics セクションに追記。

        ファイルロック（fcntl.LOCK_EX）で並行書き込みを保護。
        """
        if not self._path or not self._path.exists():
            return

        entry: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "domain": domain,
            "workflow": workflow,
            "model": model,
            "latency_ms": round(latency_ms),
            "success": success,
        }
        if metadata:
            entry["metadata"] = metadata

        with open(self._path, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                raw: dict[str, Any] = yaml.safe_load(f) or {}
                metrics_list = raw.setdefault("metrics", [])
                metrics_list.append(entry)

                f.seek(0)
                f.truncate()
                yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def get_domain_metrics(self, domain: str) -> list[dict[str, Any]]:
        """指定ドメインのメトリクスを返す。"""
        return [m for m in self.metrics if m.get("domain") == domain]

    def get_metrics_summary(self, domain: str | None = None) -> dict[str, Any]:
        """メトリクスの集計サマリを返す。

        Returns:
            {
                "total_runs": int,
                "success_rate": float,
                "avg_latency_ms": float,
                "by_model": {model: {runs, success_rate, avg_latency_ms}},
                "by_workflow": {workflow: {runs, success_rate, avg_latency_ms}},
            }
        """
        entries = self.get_domain_metrics(domain) if domain else self.metrics
        if not entries:
            return {"total_runs": 0, "success_rate": 0.0, "avg_latency_ms": 0.0,
                    "by_model": {}, "by_workflow": {}}

        total = len(entries)
        successes = sum(1 for e in entries if e.get("success"))
        total_lat = sum(e.get("latency_ms", 0) for e in entries)

        by_model: dict[str, dict[str, Any]] = {}
        by_workflow: dict[str, dict[str, Any]] = {}

        for e in entries:
            for key, bucket in [("model", by_model), ("workflow", by_workflow)]:
                val = e.get(key, "unknown")
                if val not in bucket:
                    bucket[val] = {"runs": 0, "successes": 0, "total_latency": 0}
                bucket[val]["runs"] += 1
                if e.get("success"):
                    bucket[val]["successes"] += 1
                bucket[val]["total_latency"] += e.get("latency_ms", 0)

        def _summarize(b: dict) -> dict:
            return {
                k: {
                    "runs": v["runs"],
                    "success_rate": v["successes"] / v["runs"] if v["runs"] else 0.0,
                    "avg_latency_ms": v["total_latency"] / v["runs"] if v["runs"] else 0.0,
                }
                for k, v in b.items()
            }

        return {
            "total_runs": total,
            "success_rate": successes / total,
            "avg_latency_ms": total_lat / total,
            "by_model": _summarize(by_model),
            "by_workflow": _summarize(by_workflow),
        }

    def build_suggest_prompt(self) -> str | None:
        """蓄積フィードバック＋メトリクスから改善提案を生成するためのプロンプトを構築。

        フィードバックもメトリクスもなければ None を返す。
        """
        if not self.feedback and not self.metrics:
            return None

        # 現在の teams.yaml を YAML 文字列化（フィードバック・メトリクス除外）
        current_config: dict[str, Any] = {
            "domains": {},
            "routing": self.routing,
            "voters": self.voters,
            "pipelines": self.pipelines,
        }
        for name, d in self.domains.items():
            domain_dict: dict[str, Any] = {
                "label": d.label,
                "description": d.description,
                "workflow_type": d.workflow_type,
                "personas": d.personas,
                "dimensions": d.dimensions,
                "dimension_leads": d.dimension_leads,
                "workflows": d.workflows,
                "quality_rules": d.quality_rules,
            }
            if d.constraints:
                domain_dict["constraints"] = d.constraints
            if d.style_config:
                domain_dict["style_config"] = d.style_config
            if d.processes:
                domain_dict["processes"] = d.processes
            # v2.0 fields
            if d.persona_refs:
                domain_dict["persona_refs"] = d.persona_refs
            if d.skills:
                domain_dict["skills"] = d.skills
            if d.workflow_phases:
                domain_dict["workflow_phases"] = d.workflow_phases
            if d.orchestration:
                domain_dict["orchestration"] = d.orchestration
            current_config["domains"][name] = domain_dict

        config_yaml = yaml.dump(
            current_config, default_flow_style=False,
            allow_unicode=True, sort_keys=False,
        )

        sections: list[str] = [
            "You are an AI team preset improvement advisor.",
            "",
            "Below is the current teams.yaml domain/workflow configuration:",
            "",
            f"```yaml\n{config_yaml}```",
        ]

        # Feedback list
        if self.feedback:
            sections.append("\nThe following feedback has been accumulated:\n")
            for fb in self.feedback:
                sections.append(
                    f"  [{fb.get('domain', 'general')}] {fb.get('change', '')} "
                    f"(reason: {fb.get('rationale', 'none')}, {fb.get('date', '')})"
                )

        # Metrics summary
        if self.metrics:
            summary = self.get_metrics_summary()
            sections.append(f"\nThe following execution metrics have been accumulated (total {summary['total_runs']} runs):\n")
            sections.append(f"  Overall success rate: {summary['success_rate']:.1%}")
            sections.append(f"  Average latency:      {summary['avg_latency_ms']:.0f}ms")
            if summary["by_model"]:
                sections.append("\n  By model:")
                for model, stats in summary["by_model"].items():
                    sections.append(
                        f"    {model}: {stats['runs']} runs, "
                        f"success rate {stats['success_rate']:.1%}, "
                        f"avg {stats['avg_latency_ms']:.0f}ms"
                    )
            if summary["by_workflow"]:
                sections.append("\n  By workflow:")
                for wf, stats in summary["by_workflow"].items():
                    sections.append(
                        f"    {wf}: {stats['runs']} runs, "
                        f"success rate {stats['success_rate']:.1%}, "
                        f"avg {stats['avg_latency_ms']:.0f}ms"
                    )

        # Add existing learned-rules.yaml rules as reference
        from .learned_rules import LearnedRulesConfig

        lr = LearnedRulesConfig.load()
        if lr._path:
            lr_sections: list[str] = [
                "\nBelow are existing rules from learned-rules.yaml (avoid duplicate proposals):\n",
            ]
            if lr.global_constraints:
                lr_sections.append("  Global constraints:")
                for c in lr.global_constraints:
                    lr_sections.append(f"    [{c.get('id', '?')}] {c.get('rule', '')}")
            if lr.global_processes:
                lr_sections.append("  Global processes:")
                for p in lr.global_processes:
                    lr_sections.append(f"    [{p.get('id', '?')}] {p.get('rule', '')}")
            for name, dr in lr.domain_rules.items():
                if dr.constraints or dr.processes or dr.style_config:
                    lr_sections.append(f"  {name}:")
                    for c in dr.constraints:
                        lr_sections.append(f"    [{c.get('id', '?')}] {c.get('rule', '')}")
                    for p in dr.processes:
                        lr_sections.append(f"    [{p.get('id', '?')}] {p.get('rule', '')}")
                    if dr.style_config:
                        resolved = lr._resolve_style_config(dr.style_config)
                        lr_sections.append(f"    style_config: {list(resolved.keys())}")
            sections.extend(lr_sections)

        sections.append("\nAnalyze the data above and propose specific changes to teams.yaml and learned-rules.yaml.")
        sections.append("""
Output format:
1. For each feedback/metric, describe what section to change and how
2. Rationale for the change
3. Post-change YAML snippet (directly copy-pasteable)

Rules:
- Do not propose deleting existing personas or dimensions (additions/modifications only)
- Model spec must be in "provider/model" format
- workflow_type must be one of: consensus, vote, pipeline, specialty
- Propose alternatives for models/workflows with low success rates in metrics
- Consider faster alternatives for models with high latency
- Avoid duplicating rules already in learned-rules.yaml
- New rules should be proposed for learned-rules.yaml, not teams.yaml""")

        return "\n".join(sections)
