"""promoter.py — bridge ルールの昇格パイプライン。

昇格 = テキスト移動ではない。
昇格 = workflow phase追加 + ペルソナ配置 + Python実装 + テスト/hook を1セットで実装。
関連ドキュメント（SKILL.md / references / platform docs）も同時更新。

IMP-071 Phase 3（拡張版: Phase 2 統合済み）。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PromotionPlan:
    """昇格計画。"""

    rule_id: str
    rule_text: str
    root_cause: str  # 構造 / 業務ドメイン / AIモデル / ワークフロー
    enforcement_type: str  # hook_strict / hook_fuzzy / prose_gate
    level: str  # 'hook' | 'constraint' | 'process' | 'phase'
    target_domain: str
    rationale: str = ""
    # level == 'phase' の場合
    phase_name: str | None = None
    phase_position: str | None = None  # 'after:review' etc
    persona_id: str | None = None  # 既存ペルソナID（新規作成より拡張優先）
    persona_new: bool = False  # 既存にない場合のみ True
    py_module: str | None = None  # 'lateral_check' etc
    test_module: str | None = None
    # level == 'constraint' | 'process' の場合
    constraint_text: str | None = None
    # 関連変更（analyze で AI が導出）
    affected_files: list[str] = field(default_factory=list)
    linked_improvement: str | None = None  # IMP-XXX


@dataclass
class PromotionResult:
    """昇格実行結果。"""

    rule_id: str
    success: bool
    level: str
    changes: list[str] = field(default_factory=list)  # 変更したファイル一覧
    error: str | None = None
    manual_review_needed: list[str] = field(default_factory=list)  # 手動レビュー対象


class PromotionPipeline:
    """bridge ルールの昇格パイプライン。

    フロー:
    1. analyze_rule() → 構造情報収集 + AI 判断 → PromotionPlan
    2. quality_gate() → 品質ゲート（重複/一般論/scope不在/矛盾）
    3. vote_plan() → マルチモデル合議で妥当性検証
    4. execute_plan() → 1セット実装（teams.yaml + py + test + docs + backlog）
    5. verify() → pytest 実行 → pass なら bridge 削除
    """

    def __init__(
        self,
        learned_rules_path: Path,
        teams_yaml_path: Path,
        domains_dir: Path,
        tests_dir: Path,
    ):
        self.learned_rules_path = learned_rules_path
        self.teams_yaml_path = teams_yaml_path
        self.domains_dir = domains_dir
        self.tests_dir = tests_dir
        self._backups: dict[Path, Path] = {}
        self._generated_files: list[Path] = []  # rollback 時に削除する生成ファイル

    def get_bridge_rules(self) -> list[dict[str, Any]]:
        """learned-rules.yaml / ドメイン別 YAML から type:bridge ルールを取得。"""
        import yaml

        bridges: list[dict[str, Any]] = []
        for yf in self._iter_rule_files():
            with open(yf) as f:
                data = yaml.safe_load(f) or {}
            for rule in data.get("rules", []):
                if isinstance(rule, dict) and rule.get("type") == "bridge":
                    bridges.append(rule)
        return bridges

    # =========================================================================
    # Stage 1: analyze — 構造情報収集 + AI 判断
    # =========================================================================

    def analyze_rule(self, rule: dict[str, Any]) -> PromotionPlan:
        """2段階分析: 構造情報を Python で収集 → AI に判断を委ねる。

        enforcement_type が hook_strict/hook_fuzzy の場合は AI 判断不要
        （機械的に確定）。
        """
        rule_id = rule.get("id", "")
        rule_text = rule.get("rule", "")
        enforcement = rule.get("enforcement_type", "prose_gate")
        domain = self._resolve_domain(rule)
        linked_imp = rule.get("linked_improvement")

        # hook_strict/fuzzy は機械的に確定（AI 判断不要）
        if enforcement in ("hook_strict", "hook_fuzzy"):
            return PromotionPlan(
                rule_id=rule_id,
                rule_text=rule_text,
                root_cause="構造",
                enforcement_type=enforcement,
                level="hook",
                target_domain=domain,
                rationale=f"enforcement_type={enforcement} → compile-hooks で hook 生成",
                affected_files=[],
                linked_improvement=linked_imp,
            )

        # prose_gate: AI に判断を委ねる
        domain_context = self._get_domain_context(domain)
        plan = self._ai_analyze(rule, domain, domain_context)
        plan.linked_improvement = linked_imp
        return plan

    def _get_domain_context(self, domain: str) -> dict[str, Any]:
        """ドメインの構造情報を収集（AI 判断の入力として使用）。"""
        import yaml

        if not self.teams_yaml_path.exists():
            return {"domain": domain, "workflow": [], "persona_refs": [],
                    "personas": {}, "constraints": [], "processes": [],
                    "skill_md_path": None, "reference_docs": []}

        with open(self.teams_yaml_path) as f:
            data = yaml.safe_load(f) or {}

        domain_data = data.get("domains", {}).get(domain, {})
        all_personas = data.get("personas", {})

        persona_refs = domain_data.get("persona_refs", [])
        domain_personas = {
            pid: {
                "name": all_personas[pid].get("name", pid),
                "phase_affinity": all_personas[pid].get("phase_affinity", []),
                "expertise": all_personas[pid].get("expertise", []),
            }
            for pid in persona_refs
            if pid in all_personas
        }

        return {
            "domain": domain,
            "workflow": domain_data.get("workflow", []),
            "persona_refs": persona_refs,
            "personas": domain_personas,
            "constraints": [
                c.get("rule", "") if isinstance(c, dict) else str(c)
                for c in domain_data.get("constraints", [])
            ],
            "processes": [
                p.get("rule", "") if isinstance(p, dict) else str(p)
                for p in domain_data.get("processes", [])
            ],
            "skill_md_path": self._find_skill_md(domain),
            "reference_docs": self._find_reference_docs(domain),
        }

    def _ai_analyze(
        self,
        rule: dict[str, Any],
        domain: str,
        context: dict[str, Any],
    ) -> PromotionPlan:
        """AI に昇格計画の判断を委ねる（vote 経由）。"""
        rule_id = rule.get("id", "")
        rule_text = rule.get("rule", "")
        enforcement = rule.get("enforcement_type", "prose_gate")

        prompt = self._build_analyze_prompt(rule, context)
        system = (
            "あなたは AI ワークフローフレームワークの設計者です。"
            "bridge ルールの昇格計画を策定してください。"
            "出力は必ず JSON のみ（マークダウンのコードブロックなし）で返してください。"
        )

        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "automation_engine", "run",
                    "--mode", "direct",
                    "--model", "gemini/gemini-2.5-pro",
                    "--system", system,
                    prompt,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            ai_output = result.stdout.strip()
            return self._parse_ai_plan(ai_output, rule, domain, context)
        except (subprocess.TimeoutExpired, Exception):
            # AI 失敗時はフォールバック（保守的に constraint）
            return PromotionPlan(
                rule_id=rule_id,
                rule_text=rule_text,
                root_cause="不明（AI分析失敗）",
                enforcement_type=enforcement,
                level="constraint",
                target_domain=domain,
                rationale="AI分析失敗 → 保守的に constraint にフォールバック",
                constraint_text=rule_text,
                affected_files=[],
            )

    def _build_analyze_prompt(
        self,
        rule: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """AI 分析用プロンプトを構築。"""
        personas_str = "\n".join(
            f"  - {pid}: phase_affinity={info['phase_affinity']}"
            for pid, info in context.get("personas", {}).items()
        )
        constraints_str = "\n".join(
            f"  - {c}" for c in context.get("constraints", [])[:5]
        )
        processes_str = "\n".join(
            f"  - {p}" for p in context.get("processes", [])[:5]
        )

        skill_md = context.get("skill_md_path") or "なし"
        ref_docs = ", ".join(context.get("reference_docs", [])) or "なし"

        return f"""以下の bridge ルールの昇格計画を策定してください。

## ルール
ID: {rule.get('id', '')}
テキスト: {rule.get('rule', '')}
ドメイン: {context['domain']}

## ドメインの現在の構造
ワークフロー: {context['workflow']}
ペルソナ:
{personas_str or '  なし'}
既存 constraints({len(context.get('constraints', []))}件):
{constraints_str or '  なし'}
既存 processes({len(context.get('processes', []))}件):
{processes_str or '  なし'}
SKILL.md: {skill_md}
関連リファレンス: {ref_docs}

## 判断基準
- constraint: 品質基準の宣言（「〜であること」「〜禁止」）→ teams.yaml constraints に追加
- process: 手順・チェックポイントの追加（「〜の前に〜する」「〜を確認すること」）→ teams.yaml processes に追加
- phase: ワークフローの構造変更が必要（新しいフェーズの追加 + Python実装 + テスト）→ workflow + py + test

## 出力（JSON のみ。```json や説明文は不要）
{{
  "level": "constraint" or "process" or "phase",
  "root_cause": "構造 / 業務ドメイン / AIモデル / ワークフロー のいずれか",
  "rationale": "この判断をした根拠",
  "phase_name": "英語スネークケース。level==phase の場合のみ",
  "phase_position": "after:既存phase名。level==phase の場合のみ",
  "persona_id": "ドメインの persona_refs から選択。phase の場合は担当ペルソナ",
  "affected_files": ["同時更新が必要なファイルパス。SKILL.md, references/, docs/ 等"]
}}"""

    def _parse_ai_plan(
        self,
        ai_output: str,
        rule: dict[str, Any],
        domain: str,
        context: dict[str, Any],
    ) -> PromotionPlan:
        """AI 出力を PromotionPlan にパース。"""
        rule_id = rule.get("id", "")
        rule_text = rule.get("rule", "")
        enforcement = rule.get("enforcement_type", "prose_gate")

        # JSON を抽出（コードブロック内の場合も対応）
        text = ai_output
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        # JSON の開始位置を探す
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            text = text[json_start:json_end]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # パース失敗 → 保守的に constraint
            return PromotionPlan(
                rule_id=rule_id,
                rule_text=rule_text,
                root_cause="不明（JSONパース失敗）",
                enforcement_type=enforcement,
                level="constraint",
                target_domain=domain,
                rationale=f"JSONパース失敗 → constraint フォールバック。AI出力: {ai_output[:200]}",
                constraint_text=rule_text,
                affected_files=[],
            )

        level = data.get("level", "constraint")
        if level not in ("constraint", "process", "phase"):
            level = "constraint"

        plan = PromotionPlan(
            rule_id=rule_id,
            rule_text=rule_text,
            root_cause=data.get("root_cause", "不明"),
            enforcement_type=enforcement,
            level=level,
            target_domain=domain,
            rationale=data.get("rationale", ""),
            affected_files=data.get("affected_files", []),
        )

        if level == "phase":
            plan.phase_name = data.get("phase_name", "custom_check")
            plan.phase_position = data.get("phase_position", f"after:{context['workflow'][-1]}" if context.get("workflow") else None)
            plan.persona_id = data.get("persona_id")
            # ペルソナがドメインに存在するか検証
            if plan.persona_id and plan.persona_id not in context.get("persona_refs", []):
                plan.persona_new = True
            plan.py_module = plan.phase_name
            plan.test_module = f"test_{plan.phase_name}"

        if level in ("constraint", "process"):
            plan.constraint_text = rule_text

        return plan

    # =========================================================================
    # Stage 2: quality_gate
    # =========================================================================

    def quality_gate(
        self,
        plan: PromotionPlan,
        existing_rules: list[dict[str, Any]],
    ) -> tuple[bool, str]:
        """品質ゲート。

        Returns:
            (pass, reason)
        """
        from ..domains.learning.plan import _tokenize, match_against_rules
        from ..domains.learning.types import ExtractedFeedback

        # 1. 重複検出
        fb = ExtractedFeedback(text=plan.rule_text, pattern="promotion")
        matches = match_against_rules([fb], existing_rules, min_overlap=3)
        if matches and matches[0].match_type != "none":
            matched_id = matches[0].matched_rule_id
            return False, f"既存ルール {matched_id} と重複"

        # 2. 一般論棄却（キーワード密度チェック）
        tokens = _tokenize(plan.rule_text)
        if len(tokens) < 3:
            return False, "具体性不足（キーワード3未満）"

        # 3. scope 不在チェック（ドメイン解決済みか）
        if not plan.target_domain:
            return False, "target_domain が未解決"

        return True, "OK"

    # =========================================================================
    # Stage 3: vote_plan — 昇格計画のマルチモデルレビュー
    # =========================================================================

    async def vote_plan(self, plan: PromotionPlan) -> dict[str, Any]:
        """マルチモデル合議で昇格計画を検証。"""
        prompt = self._build_vote_prompt(plan)
        system = (
            "あなたは AI フレームワーク設計の専門家です。"
            "以下の昇格計画を (1)妥当性 (2)過剰/不足 (3)ペルソナ選択 (4)phase位置 "
            "(5)affected_files の網羅性 の5軸で評価し、"
            "approve / reject / modify を判定してください。"
            "特に「constraint で済むのに phase は過剰」「affected_files の漏れ」を厳しくチェック。"
        )

        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "automation_engine", "vote",
                    "--system", system, prompt,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "approved": "approve" in result.stdout.lower(),
                "output": result.stdout,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"approved": False, "output": "vote timeout", "returncode": -1}

    # =========================================================================
    # Stage 4: execute_plan — 全変更を1トランザクションで実行
    # =========================================================================

    def execute_plan(self, plan: PromotionPlan) -> PromotionResult:
        """昇格計画を実行（全変更を1セット。分割禁止）。

        実行前に全変更対象ファイルをバックアップ。fail 時はロールバック。
        """
        changes: list[str] = []
        manual_review: list[str] = []
        self._generated_files = []
        self._backup_all(plan)

        try:
            # === コア変更（昇格レベルに応じた分岐）===
            if plan.level == "hook":
                pass  # compile-hooks は最後にまとめて実行
            elif plan.level == "constraint":
                self._add_constraint_to_teams_yaml(plan, changes)
            elif plan.level == "process":
                self._add_process_to_teams_yaml(plan, changes)
            elif plan.level == "phase":
                self._add_phase_to_teams_yaml(plan, changes)
                py_path = self._generate_phase_code(plan)
                self._generated_files.append(py_path)
                changes.append(str(py_path))
                test_path = self._generate_test_code(plan)
                self._generated_files.append(test_path)
                changes.append(str(test_path))

            # === 関連ドキュメント更新 ===
            # SKILL.md: phase 追加時のみ。global は自動更新しない
            if plan.level == "phase" and plan.target_domain != "global":
                self._append_phase_skeleton_to_skill_md(plan, changes)

            # role-workflow-guide.md: ペルソナ×フェーズ変更時
            if plan.level == "phase":
                self._update_reference_docs(plan, changes)

            # domain-phase-spec.md: phase 追加時
            if plan.level == "phase":
                self._update_automation_engine_specs(plan, changes)

            # === 完了処理 ===
            # improvement-backlog status 更新
            self._update_improvement_backlog(plan, changes)

            # compile-hooks（全レベル共通、最後に1回のみ）
            self._run_compile_hooks(changes)

            # affected_files のうち自動更新されなかったものを手動レビュー対象に
            auto_changed = set(changes)
            for af in plan.affected_files:
                if not any(af in c for c in auto_changed):
                    manual_review.append(af)

            return PromotionResult(
                rule_id=plan.rule_id,
                success=True,
                level=plan.level,
                changes=changes,
                manual_review_needed=manual_review,
            )
        except Exception as e:
            self._rollback_all()
            return PromotionResult(
                rule_id=plan.rule_id,
                success=False,
                level=plan.level,
                changes=changes,
                error=str(e),
            )

    # =========================================================================
    # Stage 5: verify + delete
    # =========================================================================

    def verify(self, result: PromotionResult) -> bool:
        """pytest でフルテストスイートを実行。"""
        if not result.success:
            return False

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-x", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.domains_dir.parent.parent),  # platform/
            )
            return proc.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def delete_bridge_rule(self, rule_id: str) -> bool:
        """昇格完了後に bridge ルールをドメイン別 YAML から削除。"""
        import yaml

        for yf in self._iter_rule_files():
            with open(yf) as f:
                data = yaml.safe_load(f) or {}

            rules = data.get("rules", [])
            original_count = len(rules)
            data["rules"] = [r for r in rules if r.get("id") != rule_id]

            if len(data["rules"]) < original_count:
                with open(yf, "w") as f:
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
                return True
        return False

    # =========================================================================
    # Private helpers — ファイルアクセス
    # =========================================================================

    def _iter_rule_files(self) -> list[Path]:
        """learned_rules_path からルールファイル一覧を返す。

        IMP-072: ディレクトリの場合はドメイン別 YAML を列挙、
        ファイルの場合は単一ファイルを返す（後方互換）。
        """
        p = self.learned_rules_path
        if p.is_dir():
            return sorted(
                f for f in p.glob("*.yaml")
                if f.name != "improvement-backlog.yaml"
                and not f.name.endswith(".bak")
            )
        if p.is_file():
            return [p]
        return []

    def _domain_file_path(self, domain: str) -> Path:
        """ドメイン名から書き込み先ファイルパスを返す。

        IMP-072: ディレクトリの場合はドメインファイル、
        ファイルの場合はそのファイル（後方互換）。
        """
        p = self.learned_rules_path
        if p.is_dir():
            return p / f"{domain}.yaml"
        return p

    def _rules_base(self) -> Path:
        """ルールファイルの基底ディレクトリ（rules/）を返す。"""
        p = self.learned_rules_path
        if p.is_dir():
            return p
        return p.parent

    def _ssot_base(self) -> Path:
        """SSoT ベースディレクトリ (.claude/) を返す。"""
        p = self.learned_rules_path
        if p.is_dir():
            # rules/ → references/ → .claude/
            return p.parent.parent
        # learned-rules.yaml → rules/ → references/ → .claude/
        return p.parent.parent.parent

    # =========================================================================
    # Private helpers — ドメイン情報
    # =========================================================================

    def _resolve_domain(self, rule: dict[str, Any]) -> str:
        """ルールの binding からドメインを解決。"""
        binding = rule.get("binding", {})
        if binding.get("level") == "domain":
            return binding.get("target", "")
        if binding.get("level") == "company":
            return "global"
        # fallback: テキストからドメイン推定
        from ..domains.learning.plan import _guess_domain
        return _guess_domain(rule.get("rule", ""))

    def _find_skill_md(self, domain: str) -> str | None:
        """ドメインに対応する SKILL.md のパスを探す。"""
        # skill_mapping の逆引き: domain → skill name
        skill_map = {
            "code-review": "ai-review",
            "slides": "ai-slides",
            "fix": "ai-fix",
            "spec": "ai-spec-update",
            "research": "ai-survey",
            "pm-export": "export",
            "pm-planning": "ai-pm-planning",
            "learning": "ai-learn",
            "project-mgmt": "pj-init",
            "ops": "push",
        }
        skill_name = skill_map.get(domain)
        if not skill_name:
            return None

        # SSoT パスから検索
        ssot_base = self._ssot_base()
        skill_md = ssot_base / "skills" / skill_name / "SKILL.md"
        if skill_md.exists():
            return str(skill_md)
        return None

    def _find_reference_docs(self, domain: str) -> list[str]:
        """ドメインに関連するリファレンスドキュメントのパスを探す。"""
        ssot_base = self._ssot_base()
        docs: list[str] = []

        # 共通ガイド
        role_guide = ssot_base / "references" / "guides" / "role-workflow-guide.md"
        if role_guide.exists():
            docs.append(str(role_guide))

        # platform docs
        automation_engine_root = self.domains_dir.parent.parent  # platform/
        spec = automation_engine_root / "docs" / "specs" / "domain-phase-spec.md"
        if spec.exists():
            docs.append(str(spec))

        return docs

    # =========================================================================
    # Private helpers — teams.yaml 操作
    # =========================================================================

    def _add_constraint_to_teams_yaml(
        self, plan: PromotionPlan, changes: list[str],
    ) -> None:
        """teams.yaml にドメイン constraint を追加。"""
        self._add_entry_to_teams_yaml(
            plan, "constraints", changes,
            label="constraint",
        )

    def _add_process_to_teams_yaml(
        self, plan: PromotionPlan, changes: list[str],
    ) -> None:
        """teams.yaml にドメイン process を追加。"""
        self._add_entry_to_teams_yaml(
            plan, "processes", changes,
            label="process",
        )

    def _add_entry_to_teams_yaml(
        self,
        plan: PromotionPlan,
        section: str,
        changes: list[str],
        label: str,
    ) -> None:
        """teams.yaml のドメインセクションにエントリを追加（共通実装）。"""
        try:
            from ruamel.yaml import YAML
            ryaml = YAML()
            ryaml.preserve_quotes = True
            with open(self.teams_yaml_path) as f:
                data = ryaml.load(f)
            writer = lambda d, f: ryaml.dump(d, f)
        except ImportError:
            import yaml as _yaml
            with open(self.teams_yaml_path) as f:
                data = _yaml.safe_load(f)
            writer = lambda d, f: _yaml.dump(d, f, allow_unicode=True, default_flow_style=False)

        if plan.target_domain == "global":
            # global: トップレベルの section に追加
            if section not in data:
                data[section] = []
            data[section].append({
                "id": plan.rule_id,
                "rule": plan.constraint_text or plan.rule_text,
                "source": "promoted",
            })
        else:
            domain_data = data.get("domains", {}).get(plan.target_domain, {})
            if section not in domain_data:
                domain_data[section] = []
            domain_data[section].append({
                "id": plan.rule_id,
                "rule": plan.constraint_text or plan.rule_text,
                "source": "promoted",
            })

        with open(self.teams_yaml_path, "w") as f:
            writer(data, f)
        changes.append(f"teams.yaml ({label}追加: {plan.rule_id} in {plan.target_domain})")

    def _add_phase_to_teams_yaml(
        self, plan: PromotionPlan, changes: list[str],
    ) -> None:
        """teams.yaml にドメイン workflow phase を追加 + ペルソナ拡張。"""
        try:
            from ruamel.yaml import YAML
            ryaml = YAML()
            ryaml.preserve_quotes = True
            with open(self.teams_yaml_path) as f:
                data = ryaml.load(f)
            writer = lambda d, f: ryaml.dump(d, f)
        except ImportError:
            import yaml as _yaml
            with open(self.teams_yaml_path) as f:
                data = _yaml.safe_load(f)
            writer = lambda d, f: _yaml.dump(d, f, allow_unicode=True, default_flow_style=False)

        domain_data = data.get("domains", {}).get(plan.target_domain)
        if not domain_data:
            raise ValueError(f"ドメイン {plan.target_domain} が teams.yaml に存在しません")

        # workflow に phase 追加
        workflow = domain_data.get("workflow", [])
        if plan.phase_name and plan.phase_name not in workflow:
            insert_idx = len(workflow)  # デフォルト: 末尾
            if plan.phase_position and plan.phase_position.startswith("after:"):
                after_phase = plan.phase_position[6:]
                if after_phase in workflow:
                    insert_idx = workflow.index(after_phase) + 1
            workflow.insert(insert_idx, plan.phase_name)
            domain_data["workflow"] = workflow

        # ペルソナの phase_affinity 拡張（新規作成より拡張優先）
        if plan.persona_id and plan.phase_name:
            personas = data.get("personas", {})
            if plan.persona_id in personas:
                affinity = personas[plan.persona_id].get("phase_affinity", [])
                if plan.phase_name not in affinity:
                    affinity.append(plan.phase_name)
                    personas[plan.persona_id]["phase_affinity"] = affinity

        with open(self.teams_yaml_path, "w") as f:
            writer(data, f)
        changes.append(f"teams.yaml (phase追加: {plan.phase_name} in {plan.target_domain})")

    # =========================================================================
    # Private helpers — コード生成
    # =========================================================================

    def _generate_phase_code(self, plan: PromotionPlan) -> Path:
        """phase 実装コードのスケルトンを生成。"""
        domain_dir_name = plan.target_domain.replace("-", "_")
        phase_dir = self.domains_dir / domain_dir_name
        phase_dir.mkdir(parents=True, exist_ok=True)
        # __init__.py がなければ作成（import 解決のため）
        init_py = phase_dir / "__init__.py"
        if not init_py.exists():
            init_py.write_text("")
        py_path = phase_dir / f"{plan.phase_name}.py"

        code = f'''"""domains/{domain_dir_name}/{plan.phase_name} — 自動昇格で生成。

ルール: {plan.rule_id}
根本原因: {plan.root_cause}
"""

from __future__ import annotations

from typing import Any


async def execute(
    *, actors: list[dict[str, Any]], rules: dict[str, Any], context: dict[str, Any],
) -> dict[str, Any]:
    """WorkflowEngine エントリポイント: {plan.phase_name} phase。

    TODO: このスケルトンを具体的な検証ロジックで実装する。
    ルール: {plan.rule_text}
    """
    return {{
        "phase_{plan.phase_name}": {{
            "status": "completed",
            "actor_count": len(actors),
        }},
    }}
'''
        py_path.write_text(code)
        return py_path

    def _generate_test_code(self, plan: PromotionPlan) -> Path:
        """テストコードのスケルトンを生成。"""
        domain_dir_name = plan.target_domain.replace("-", "_")
        test_dir = self.tests_dir / "domains" / domain_dir_name
        test_dir.mkdir(parents=True, exist_ok=True)
        # __init__.py がなければ作成（pytest の import 解決のため）
        for d in [self.tests_dir / "domains", test_dir]:
            init_py = d / "__init__.py"
            if not init_py.exists():
                init_py.write_text("")
        test_path = test_dir / f"test_{plan.phase_name}.py"

        code = f'''"""tests/domains/{domain_dir_name}/test_{plan.phase_name} — 自動昇格で生成。

ルール: {plan.rule_id}
"""

import pytest


@pytest.mark.asyncio
async def test_{plan.phase_name}_basic():
    """基本動作テスト。"""
    from automation_engine.domains.{domain_dir_name}.{plan.phase_name} import execute

    result = await execute(actors=[], rules={{}}, context={{}})
    assert "phase_{plan.phase_name}" in result
    assert result["phase_{plan.phase_name}"]["status"] == "completed"
'''
        test_path.write_text(code)
        return test_path

    # =========================================================================
    # Private helpers — 関連ドキュメント更新
    # =========================================================================

    def _append_phase_skeleton_to_skill_md(
        self, plan: PromotionPlan, changes: list[str],
    ) -> None:
        """SKILL.md に新 phase の TODO スケルトンを追記。"""
        skill_md_path = self._find_skill_md(plan.target_domain)
        if not skill_md_path:
            return

        path = Path(skill_md_path)
        if not path.exists():
            return

        skeleton = f"""

<!-- TODO: 自動昇格で追加 ({plan.rule_id}) -->
<!-- Phase: {plan.phase_name} — {plan.rule_text[:80]} -->
<!-- このセクションの詳細は Claude Code が /ai-learn 実行時に補完する -->
"""
        with open(path, "a") as f:
            f.write(skeleton)
        changes.append(f"SKILL.md (TODO追記: {plan.phase_name})")

    def _update_reference_docs(
        self, plan: PromotionPlan, changes: list[str],
    ) -> None:
        """role-workflow-guide.md のペルソナ×フェーズマッピングを更新。"""
        ssot_base = self._ssot_base()
        guide = ssot_base / "references" / "guides" / "role-workflow-guide.md"
        if not guide.exists():
            return

        note = f"""

<!-- TODO: 自動昇格で追加 ({plan.rule_id}) -->
<!-- ドメイン {plan.target_domain} に {plan.phase_name} phase 追加 -->
<!-- ペルソナ {plan.persona_id} の phase_affinity に {plan.phase_name} を追加 -->
"""
        with open(guide, "a") as f:
            f.write(note)
        changes.append(f"role-workflow-guide.md (TODO追記: {plan.phase_name})")

    def _update_automation_engine_specs(
        self, plan: PromotionPlan, changes: list[str],
    ) -> None:
        """domain-phase-spec.md に phase 定義を追記。"""
        automation_engine_root = self.domains_dir.parent.parent
        spec = automation_engine_root / "docs" / "specs" / "domain-phase-spec.md"
        if not spec.exists():
            return

        entry = f"""

<!-- TODO: 自動昇格で追加 ({plan.rule_id}) -->
## {plan.target_domain}.{plan.phase_name}

- **位置**: {plan.phase_position}
- **ペルソナ**: {plan.persona_id}
- **ルール**: {plan.rule_text[:120]}
- **実装**: `domains/{plan.target_domain.replace('-', '_')}/{plan.phase_name}.py`
"""
        with open(spec, "a") as f:
            f.write(entry)
        changes.append(f"domain-phase-spec.md (追記: {plan.target_domain}.{plan.phase_name})")

    def _update_improvement_backlog(
        self, plan: PromotionPlan, changes: list[str],
    ) -> None:
        """improvement-backlog.yaml の linked IMP を status: done に更新。"""
        if not plan.linked_improvement:
            return

        import yaml

        backlog_path = self._rules_base() / "improvement-backlog.yaml"
        if not backlog_path.exists():
            return

        with open(backlog_path) as f:
            data = yaml.safe_load(f) or {}

        updated = False
        for item in data.get("items", []):
            if isinstance(item, dict) and item.get("id") == plan.linked_improvement:
                item["status"] = "done"
                updated = True
                break

        if updated:
            with open(backlog_path, "w") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            changes.append(f"improvement-backlog.yaml ({plan.linked_improvement} → done)")

    def _run_compile_hooks(self, changes: list[str]) -> None:
        """compile-hooks を実行（最後に1回のみ）。"""
        proc = subprocess.run(
            [sys.executable, "-m", "automation_engine", "compile-hooks"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"compile-hooks failed: {proc.stderr}")
        changes.append("hooks/validate_rules.py (再生成)")

    # =========================================================================
    # Private helpers — バックアップ / ロールバック
    # =========================================================================

    def _backup_all(self, plan: PromotionPlan) -> None:
        """全変更対象ファイルのバックアップを作成。"""
        self._backups = {}

        # 常にバックアップ対象
        targets = [self.teams_yaml_path]

        # improvement-backlog
        if plan.linked_improvement:
            backlog = self._rules_base() / "improvement-backlog.yaml"
            if backlog.exists():
                targets.append(backlog)

        # SKILL.md
        skill_md = self._find_skill_md(plan.target_domain)
        if skill_md:
            targets.append(Path(skill_md))

        # reference docs
        for doc in self._find_reference_docs(plan.target_domain):
            targets.append(Path(doc))

        for path in targets:
            if path.exists():
                backup = path.with_suffix(path.suffix + ".bak")
                shutil.copy2(path, backup)
                self._backups[path] = backup

    def _rollback_all(self) -> None:
        """全ファイルをバックアップから復元 + 生成ファイルを削除。"""
        for original, backup in self._backups.items():
            if backup.exists():
                shutil.copy2(backup, original)
                backup.unlink()
        for generated in self._generated_files:
            if generated.exists():
                generated.unlink()
        self._backups.clear()
        self._generated_files.clear()

    def _cleanup_backups(self) -> None:
        """成功時にバックアップファイルを削除。"""
        for backup in self._backups.values():
            if backup.exists():
                backup.unlink()
        self._backups.clear()
        self._generated_files.clear()

    # =========================================================================
    # Private helpers — vote プロンプト
    # =========================================================================

    def _build_vote_prompt(self, plan: PromotionPlan) -> str:
        """vote 用プロンプトを構築。"""
        parts = [
            f"# 昇格計画レビュー: {plan.rule_id}",
            f"ルール: {plan.rule_text}",
            f"根本原因: {plan.root_cause}",
            f"昇格レベル: {plan.level}",
            f"対象ドメイン: {plan.target_domain}",
            f"判断根拠: {plan.rationale}",
            f"影響ファイル: {plan.affected_files}",
        ]
        if plan.level == "phase":
            parts.extend([
                f"Phase名: {plan.phase_name}",
                f"位置: {plan.phase_position}",
                f"ペルソナ: {plan.persona_id} (新規: {plan.persona_new})",
            ])
        if plan.level in ("constraint", "process"):
            parts.append(f"テキスト: {plan.constraint_text}")
        return "\n".join(parts)
