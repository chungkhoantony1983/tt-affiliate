#!/usr/bin/env python3
"""ステップコントローラー（WorkflowStepCore）。

Tier 1/2 共通のフェーズ順序管理・状態永続化・バリデーションを提供する。
platform モジュール（TeamsConfig / LearnedRulesConfig）を直接 import し、
Tier 2 CLI と完全に同一の実装でドメイン・ペルソナ・ルールを解決する。

使い方（Tier 1 — Claude Code がオーケストレーター）:
    # 1. 初期化: ドメインのフェーズリスト・ペルソナ・ルールを取得
    python workflow_step.py init {domain} --prompt "..."

    # 2. prereq 完了報告
    python workflow_step.py prereq-done --state {state.json} --work-log {work-log.md}

    # 3. フェーズ実行結果を送って次フェーズへ
    python workflow_step.py advance --state {state.json} --result {result.json}

    # 4. 2-3 を全フェーズ完了まで繰り返し
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# platform モジュールの import（Tier 1/2 実装共有の核心）
# パス解決優先順位:
#   1. projects/platform/ 直接参照（マルチリポ環境 = SSoT）
#   2. .claude/scripts/automation_engine/ 配布コピー（単一リポ / Codex 環境）
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECTS_DIR = _SCRIPT_DIR.parent.parent  # .claude/scripts/ → .claude/ → projects/
_AI_TEAM_DIR = _PROJECTS_DIR / "platform"
if _AI_TEAM_DIR.is_dir() and str(_AI_TEAM_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_TEAM_DIR))
elif (_SCRIPT_DIR / "automation_engine").is_dir() and str(_SCRIPT_DIR) not in sys.path:
    # 配布先: .claude/scripts/automation_engine/ (sync.sh が配置)
    sys.path.insert(0, str(_SCRIPT_DIR))

from automation_engine.presets import TeamsConfig, LearnedRulesConfig  # noqa: E402


class WorkflowStepCore:
    """フェーズ順序管理・状態永続化・バリデーションのコアロジック。

    Tier 1/2 共通: platform の TeamsConfig + LearnedRulesConfig を直接使用し、
    ドメイン定義・ペルソナ・ルール・制約を統合的に提供する。
    """

    def __init__(
        self,
        teams: TeamsConfig,
        learned_rules: LearnedRulesConfig,
    ) -> None:
        self._teams = teams
        self._learned_rules = learned_rules

    # ------------------------------------------------------------------
    # init: ワークフロー初期化
    # ------------------------------------------------------------------

    def init(
        self,
        domain: str,
        prompt: str,
        state_file: str | None = None,
    ) -> dict[str, Any]:
        """ワークフローを初期化し、prereq 情報と state_file パスを返す。"""
        domain_preset = self._get_domain(domain)
        phases = domain_preset.workflow_phases
        if not phases:
            raise ValueError(f"ドメイン '{domain}' の workflow が空です。")

        state_path = state_file or self._generate_state_path(domain)
        state = {
            "domain": domain,
            "prompt": prompt,
            "workflow_phases": phases,
            "current_phase_index": 0,
            "prereq_done": False,
            "config_loaded": True,
            "context": {"prompt": prompt},
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._save_state(state_path, state)
        self._write_workflow_marker(state_path)

        prereq_steps = [
            {"id": "0a", "name": "work_log_init", "description": "作業ログを作成・保存"},
            {"id": "0b", "name": "resolve", "description": "要求構造化 + SSoT変更判定"},
            {"id": "0c", "name": "approve", "description": "ユーザー承認"},
        ]

        # config context を構築（platform の TeamsConfig/LearnedRulesConfig を直接使用）
        config_context = self._build_config_context(domain, domain_preset)

        # IMP-074: work-log パスヒント（SSoT 作業用デフォルト）
        work_log_hint = ""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if project_dir:
            work_log_hint = os.path.join(
                project_dir, ".claude", "logs", "work-logs", "{goal-slug}.md"
            )

        return {
            "status": "prereq_required",
            "prereq_steps": prereq_steps,
            "domain": domain,
            "domain_label": domain_preset.label,
            "workflow_phases": phases,
            "persona_refs": list(domain_preset.persona_refs),
            "config_context": config_context,
            "state_file": state_path,
            "work_log_hint": work_log_hint,
        }

    # ------------------------------------------------------------------
    # prereq-done: 前提ルール完了報告
    # ------------------------------------------------------------------

    def prereq_done(
        self,
        state_file: str,
        work_log_path: str,
        ssot_impact: str = "none",
    ) -> dict[str, Any]:
        """prereq 完了を記録し、最初のフェーズ情報を返す。

        構造的検証:
          1. work-log ファイルの存在（必須）
          2. work-log に [PURPOSE-LOCKED] マーカーが存在すること
          3. ssot_impact の work-log frontmatter との整合性

        Args:
            state_file: state.json のパス
            work_log_path: 作業ログファイルのパス（必須）
            ssot_impact: SSoT変更判定（"none" or SSoTファイルリスト）
        """
        state = self._load_state(state_file)
        if state["prereq_done"]:
            raise ValueError("prereq は既に完了しています。")

        # --- 構造的検証 1: work-log 存在（必須） ---
        if not work_log_path:
            raise ValueError(
                "work-log パスが指定されていません。\n"
                "  → prereq-done --work-log {path} で work-log を指定してください。"
            )
        wl_path = Path(work_log_path)
        if not wl_path.exists():
            raise FileNotFoundError(
                f"work-log が見つかりません: {work_log_path}\n"
                f"  → Step 7 (resolve) で work-log を作成してから prereq-done を実行してください。"
            )
        state["work_log_path"] = work_log_path

        # --- 構造的検証 2: [PURPOSE-LOCKED] マーカー ---
        import re as _re
        content = wl_path.read_text(encoding="utf-8")
        if "[PURPOSE-LOCKED]" not in content:
            raise ValueError(
                "work-log に [PURPOSE-LOCKED] マーカーが見つかりません。\n"
                "  → resolve で統合目的を確定し、ユーザー承認後に [PURPOSE-LOCKED] を記録してください。"
            )

        # --- 構造的検証 3: ssot_impact の整合性 ---
        # work-log frontmatter の ssot_impact と CLI 引数を照合
        fm_match = _re.search(r'^ssot_impact:\s*"?([^"\n]+)"?\s*$', content, _re.MULTILINE)
        if fm_match:
            fm_value = fm_match.group(1).strip()
            cli_is_none = (not ssot_impact or ssot_impact == "none")
            fm_is_none = (fm_value == "none")
            if cli_is_none != fm_is_none:
                raise ValueError(
                    f"ssot_impact の不一致:\n"
                    f"  work-log frontmatter: {fm_value}\n"
                    f"  CLI 引数:             {ssot_impact or 'none'}\n"
                    f"  → work-log の ssot_impact と --ssot-impact 引数を一致させてください。"
                )

        # ssot_impact を記録し、宣言ファイルを管理
        if ssot_impact and ssot_impact != "none":
            state["ssot_impact"] = ssot_impact
            self._write_ssot_impact_declared(ssot_impact)
        else:
            state["ssot_impact"] = "none"

        state["prereq_done"] = True
        self._save_state(state_file, state)
        return self._build_phase_info(state)

    # ------------------------------------------------------------------
    # advance: フェーズ進行
    # ------------------------------------------------------------------

    def phase_approve(
        self,
        state_file: str,
        phase: str,
    ) -> dict[str, Any]:
        """Phase 単位の approve（MEANS-LOCKED）を記録する。

        大規模作業で Phase ごとに構造定義を approve する場合に使用。
        Phase N の approve は Phase N-1 の完了後にのみ許可。

        Args:
            state_file: state.json のパス
            phase: approve する Phase 名

        Returns:
            記録結果（status, phase, phase_locks）
        """
        state = self._load_state(state_file)
        phases = state["workflow_phases"]

        if phase not in phases:
            raise ValueError(
                f"Phase '{phase}' はワークフローに存在しません。\n"
                f"  定義済み Phase: {phases}"
            )

        phase_idx = phases.index(phase)
        phase_locks = state.get("phase_locks", {})

        # Phase N の approve は Phase N-1 の完了後にのみ許可
        if phase_idx > 0:
            prev_phase = phases[phase_idx - 1]
            current_idx = state.get("current_phase_index", 0)
            if current_idx <= phase_idx - 1:
                raise ValueError(
                    f"Phase '{phase}' の approve は Phase '{prev_phase}' の完了後に実施してください。\n"
                    f"  現在の Phase: {phases[current_idx]} ({current_idx + 1}/{len(phases)})\n"
                    f"  → Phase '{prev_phase}' を advance で完了させてから approve してください。"
                )

        phase_locks[phase] = {
            "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "locked": True,
        }
        state["phase_locks"] = phase_locks
        self._save_state(state_file, state)

        return {
            "status": "phase_approved",
            "phase": phase,
            "phase_locks": phase_locks,
            "message": f"Phase '{phase}' の構造定義が承認されました。[MEANS-LOCKED:{phase}]",
        }

    def advance(
        self,
        state_file: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """現フェーズの結果を受け取り、次フェーズに進む。

        Returns:
            次フェーズの PhaseInfo または status: "done"。
            work_log_update キーにログ更新指示を含む。
        """
        state = self._load_state(state_file)

        if not state["prereq_done"]:
            raise ValueError("prereq が完了していません。prereq-done を先に実行してください。")

        idx = state["current_phase_index"]
        phases = state["workflow_phases"]

        if idx >= len(phases):
            raise ValueError("全フェーズが既に完了しています。")

        # S-004: Phase 単位の approve 検証（phase_locks が使用されている場合のみ）
        current_phase = phases[idx]
        phase_locks = state.get("phase_locks", {})
        if phase_locks:
            # phase_locks が1つでも設定されていれば Phase分割approve モード
            if current_phase not in phase_locks:
                raise ValueError(
                    f"Phase '{current_phase}' の approve（MEANS-LOCKED）が未完了です。\n"
                    f"  → workflow_step.py phase-approve --state {{state_file}} --phase {current_phase}\n"
                    f"    を実行して Phase の構造定義をユーザーと合意してください。\n"
                    f"  承認済み Phase: {list(phase_locks.keys())}"
                )

        # 5a: validate — 結果が空でないか + ゲートフェーズ固有の必須フィールド検証
        if not result:
            raise ValueError(
                f"フェーズ '{current_phase}'（{self._phase_label(current_phase)}）の結果が空です。"
            )
        domain = state.get("domain", "")
        self._validate_gate_phase_result(current_phase, result, domain=domain)

        # 5b: context_merge — 結果をコンテキストにマージ
        state["context"][f"phase_{current_phase}_result"] = result

        # 5c: work_log_update — ログ更新指示を生成（直接書き込みしない）
        work_log_update = {
            "phase_completed": current_phase,
            "phase_label": self._phase_label(current_phase),
            "phase_index": idx,
            "total_phases": len(phases),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "summary": result.get("summary", ""),
        }

        # 5e: phase_index_advance
        state["current_phase_index"] = idx + 1

        # 5f: completion_check
        self._save_state(state_file, state)

        if idx + 1 >= len(phases):
            self._remove_workflow_marker()
            self._remove_expected_marker()
            self._remove_ssot_impact_declared()
            self._remove_review_cycle_state()
            return {
                "status": "done",
                "work_log_update": work_log_update,
                "all_phases_completed": True,
            }

        phase_info = self._build_phase_info(state)
        phase_info["work_log_update"] = work_log_update
        return phase_info

    # ------------------------------------------------------------------
    # resume: 中断再開
    # ------------------------------------------------------------------

    def resume(self, state_file: str) -> dict[str, Any]:
        """既存の state.json からワークフローを再開する。"""
        state = self._load_state(state_file)
        domain = state["domain"]
        domain_preset = self._get_domain(domain)
        config_context = self._build_config_context(domain, domain_preset)

        if not state["prereq_done"]:
            return {
                "status": "prereq_required",
                "prereq_steps": [
                    {"id": "0a", "name": "work_log_init", "description": "作業ログを作成・保存"},
                    {"id": "0b", "name": "resolve", "description": "要求構造化 + SSoT変更判定"},
                    {"id": "0c", "name": "approve", "description": "ユーザー承認"},
                ],
                "domain": domain,
                "workflow_phases": state["workflow_phases"],
                "config_context": config_context,
                "state_file": state_file,
            }

        idx = state["current_phase_index"]
        if idx >= len(state["workflow_phases"]):
            return {"status": "done", "all_phases_completed": True}

        return self._build_phase_info(state)

    # ------------------------------------------------------------------
    # 内部メソッド
    # ------------------------------------------------------------------

    def _get_domain(self, domain: str) -> "DomainPreset":
        """TeamsConfig からドメイン定義を取得する。"""
        preset = self._teams.get_domain(domain)
        if preset is None:
            available = ", ".join(sorted(self._teams.domains.keys())) or "なし"
            raise KeyError(f"ドメイン '{domain}' が未定義。定義済み: {available}")
        return preset

    def _build_phase_info(self, state: dict[str, Any]) -> dict[str, Any]:
        """現フェーズの PhaseInfo を構築する。"""
        idx = state["current_phase_index"]
        phase = state["workflow_phases"][idx]
        domain = state["domain"]

        # platform の resolve_actors / resolve_rules を直接使用
        actors = self._teams.resolve_actors(domain, phase)
        teams_rules = self._teams.resolve_rules(domain, phase)
        lr_rules = self._learned_rules.resolve_rules(domain, phase)

        # Tier 2 WorkflowEngine と同じマージ: teams Level 3/4 + learned-rules 4-level
        rules = {
            "constraints": lr_rules["constraints"],
            "processes": lr_rules["processes"],
            "style_config": lr_rules["style_config"],
            "actors": teams_rules["actors"],
            "teams_constraints": teams_rules["constraints"],
            "teams_processes": teams_rules["processes"],
        }

        return {
            "status": "phase",
            "phase": phase,
            "phase_label": self._phase_label(phase),
            "phase_index": idx,
            "total_phases": len(state["workflow_phases"]),
            "actors": actors,
            "rules": rules,
            "context": state["context"],
            "state_file": state.get("_state_file", ""),
        }

    def _build_config_context(
        self, domain: str, domain_preset: "DomainPreset",
    ) -> dict[str, Any]:
        """platform の TeamsConfig/LearnedRulesConfig を使って完全な config context を構築。

        Tier 2 の Config.load() + WorkflowEngine と完全に同一の実装。
        """
        # 1. ペルソナ詳細（TeamsConfig.personas_registry から取得）
        personas: dict[str, dict[str, Any]] = {}
        for ref in domain_preset.persona_refs:
            p = self._teams.personas_registry.get(ref, {})
            if p:
                personas[ref] = {
                    "name": p.get("name", ref),
                    "perspective": p.get("perspective", ""),
                    "expertise": p.get("expertise", []),
                    "phase_affinity": p.get("phase_affinity", []),
                }

        # 2. teams.yaml のドメイン制約・プロセス・スタイル（Level 3）
        constraints = list(domain_preset.constraints)
        processes = list(domain_preset.processes)
        style_config = dict(domain_preset.style_config)

        # 3. learned-rules から全社ルール + ドメイン固有ルールを取得
        # LearnedRulesConfig の構造を直接使用（再実装なし）
        company_rules = [
            {"id": r.get("id", ""), "rule": r.get("rule", ""),
             "enforcement_type": r.get("enforcement_type", "")}
            for r in self._learned_rules.global_constraints
            if r.get("binding", {}).get("level") == "company"
        ]

        dr = self._learned_rules.domain_rules.get(domain)
        domain_rules = []
        if dr:
            domain_rules = [
                {"id": r.get("id", ""), "rule": r.get("rule", ""),
                 "enforcement_type": r.get("enforcement_type", "")}
                for r in dr.constraints
            ]

        # 4. 各フェーズの担当ペルソナを TeamsConfig.resolve_actors() で事前計算
        phase_actors: dict[str, list[str]] = {}
        for phase in domain_preset.workflow_phases:
            actors = self._teams.resolve_actors(domain, phase)
            phase_actors[phase] = [a["id"] for a in actors]

        return {
            "personas": personas,
            "constraints": constraints,
            "processes": processes,
            "company_rules": company_rules,
            "domain_rules": domain_rules,
            "style_config": style_config,
            "phase_actors": phase_actors,
        }

    def _phase_label(self, phase: str) -> str:
        """フェーズ名の日本語ラベルを返す。"""
        labels = {
            "analyze": "分析",
            "propose": "提案",
            "implement": "実装",
            "verify": "検証",
            "requirements": "要件定義",
            "architecture": "設計",
            "vote": "投票",
            "approve": "承認",
            "plan": "計画",
            "design": "デザイン",
            "review": "レビュー",
            "lateral-check": "横展開チェック",
            "source-verify": "出典検証",
            "test": "テスト",
            "export": "エクスポート",
            "report": "報告",
        }
        return labels.get(phase, phase)

    # ゲートフェーズの必須フィールド定義
    _GATE_PHASE_REQUIREMENTS: dict[str, dict[str, str]] = {
        "lateral-check": {
            "patterns_checked": "検索したパターン一覧（grep/検索で確認した同一パターンのリスト）",
            "search_results": "検索結果の要約（各パターンのヒット数・箇所）",
            "lateral_locations_count": "横展開で発見した箇所数（整数）",
            "grep_commands_executed": (
                "実行した grep/検索コマンド一覧（パターン文字列と検索対象パス）。"
                "事後検証（Check j）で再実行し結果を突合する"
            ),
        },
        "source-verify": {
            "values_checked": "検証した数値・データ一覧",
            "sources": "各数値の出典（URL、文書名、ページ番号等）",
            "verification_result": "検証結果（全数値が出典付きか、未検証項目があるか）",
        },
        # --- 0ベースレビュー強制 (RV-002) ---
        # 全ドメインの review フェーズに適用
        "review": {
            "diff_scope": "レビュー対象の diff ファイル一覧（git diff --name-only の結果）",
            "files_read": "Read ツールで読み込んだファイル一覧（ファイル名+行数）。全変更ファイルを含むこと",
            "prior_result_excluded": "前回レビュー結果を参照していないことの宣言（true/false）。0ベースレビューの証跡",
        },
        # --- レビュー報告のPRスコープ+Before/After (GP-017) ---
        "report": {
            "pr_scope": "PRスコープ（変更対象・目的・影響範囲の要約）",
            "structural_changes": "Before/After 構造変更（データフロー・テーブル定義等の変更点。変更なしの場合も明記）",
        },
        # --- エクスポート成果物コミット検証 (GN-004) ---
        "export": {
            "exported_files": "エクスポートした成果物ファイル一覧（パス）",
            "committed": "成果物が作業ブランチにコミット済みであることの確認（true/false）",
        },
    }

    # ドメイン固有の追加ゲート要件（基本要件に加算される）
    _GATE_PHASE_DOMAIN_EXTRAS: dict[str, dict[str, dict[str, str]]] = {
        # code-review / fix / spec ドメインの review フェーズ: diff外シグネチャ検証 (CR-P07)
        "code-review": {
            "review": {
                "external_signatures_verified": (
                    "diff 外呼び出し先のシグネチャ検証結果"
                    "（関数名+一致/不一致）。該当なしの場合も明記"
                ),
            },
            # CR-004 構造化: platform 指摘の一方的 dismiss 防止
            "discuss": {
                "automation_engine_open_findings": (
                    "platform CLI が出力した未解決指摘の総数（整数）。"
                    "platform 未使用の場合は 0"
                ),
                "automation_engine_dismissed_findings": (
                    "棄却した platform 指摘の一覧（JSON配列: "
                    "[{id, reason, code_reference}]）。"
                    "棄却なしの場合は空配列 []"
                ),
                "automation_engine_recheck_result": (
                    "棄却した指摘を platform に再送した結果。"
                    "'re-raised: 0' のように再提出数を明記。"
                    "棄却なしの場合は 'N/A'。"
                    "platform 未使用の場合は 'platform未使用'"
                ),
            },
        },
        "fix": {
            "review": {
                "external_signatures_verified": (
                    "diff 外呼び出し先のシグネチャ検証結果"
                    "（関数名+一致/不一致）。該当なしの場合も明記"
                ),
            },
        },
        "spec": {
            "review": {
                "external_signatures_verified": (
                    "diff 外呼び出し先のシグネチャ検証結果"
                    "（関数名+一致/不一致）。該当なしの場合も明記"
                ),
            },
        },
    }

    def _validate_gate_phase_result(
        self, phase: str, result: dict[str, Any], *, domain: str = "",
    ) -> None:
        """ゲートフェーズの result に必須フィールドが含まれているか検証する。

        必須フィールドが欠けている場合は ValueError を raise し、
        フェーズを完了させない → workflow_enforce.py Check b でブロック。

        基本要件 (_GATE_PHASE_REQUIREMENTS) にドメイン固有の追加要件
        (_GATE_PHASE_DOMAIN_EXTRAS) をマージして検証する。
        """
        # 基本要件
        requirements = dict(self._GATE_PHASE_REQUIREMENTS.get(phase, {}))

        # ドメイン固有の追加要件をマージ
        domain_extras = self._GATE_PHASE_DOMAIN_EXTRAS.get(domain, {})
        phase_extras = domain_extras.get(phase, {})
        requirements.update(phase_extras)

        # 動的条件付き要件: ビジュアルレビュー (GP-018)
        # review フェーズで diff_scope に View/Style ファイルが含まれる場合のみ追加
        if phase == "review" and domain in ("code-review", "fix", "spec"):
            diff_scope = result.get("diff_scope", "")
            _VIEW_STYLE_EXTS = (
                ".haml", ".erb", ".html", ".tsx", ".jsx", ".vue",
                ".scss", ".css", ".slim",
            )
            if any(ext in diff_scope for ext in _VIEW_STYLE_EXTS):
                requirements["visual_review_screenshots"] = (
                    "ビジュアルレビューのスクリーンショットパス一覧"
                    "（PC/SP 両ビューポート）。GP-018 必須"
                )

        if not requirements:
            return  # ゲートフェーズでない → 検証不要

        _MIN_FIELD_LEN = 10  # 最低品質チェック: 空虚な値（"確認済み"等）を防止

        missing = []
        too_short = []
        for field, description in requirements.items():
            if field not in result or not result[field]:
                missing.append(f"  - {field}: {description}")
            else:
                val = str(result[field])
                if len(val) < _MIN_FIELD_LEN:
                    too_short.append(
                        f"  - {field}: {len(val)}文字（最低{_MIN_FIELD_LEN}文字）"
                        f" → 現在値: '{val}'"
                    )

        errors = []
        if missing:
            errors.append("必須フィールドが不足しています:\n" + "\n".join(missing))
        if too_short:
            errors.append(
                f"フィールド値が短すぎます（最低{_MIN_FIELD_LEN}文字）:\n"
                + "\n".join(too_short)
            )

        if errors:
            raise ValueError(
                f"ゲートフェーズ '{phase}'（{self._phase_label(phase)}）の結果に"
                f"問題があります:\n"
                + "\n".join(errors)
                + f"\n\n→ 具体的な内容を含む result を生成してから advance してください。"
            )

    @staticmethod
    def _get_marker_path() -> str | None:
        """マーカーファイルのパスを返す。"""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            return None
        return os.path.join(project_dir, ".claude", "logs", ".workflow-active")

    @staticmethod
    def _write_workflow_marker(state_file: str) -> None:
        """ワークフローアクティブマーカーを書き込む。"""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            return
        marker_dir = os.path.join(project_dir, ".claude", "logs")
        os.makedirs(marker_dir, exist_ok=True)
        marker_path = os.path.join(marker_dir, ".workflow-active")
        with open(marker_path, "w") as f:
            f.write(state_file)

    @staticmethod
    def _remove_workflow_marker() -> None:
        """ワークフローアクティブマーカーを削除する。"""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            return
        marker_path = os.path.join(project_dir, ".claude", "logs", ".workflow-active")
        try:
            os.remove(marker_path)
        except FileNotFoundError:
            pass

    @staticmethod
    def _remove_expected_marker() -> None:
        """ワークフロー期待マーカーを削除する。"""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            return
        marker_path = os.path.join(project_dir, ".claude", "logs", ".workflow-expected")
        try:
            os.remove(marker_path)
        except FileNotFoundError:
            pass

    @staticmethod
    def _write_ssot_impact_declared(ssot_impact: str) -> None:
        """ssot_impact 宣言ファイルを書き込む。ssot_guard.py が参照する。"""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            return
        log_dir = os.path.join(project_dir, ".claude", "logs")
        os.makedirs(log_dir, exist_ok=True)
        impact_path = os.path.join(log_dir, ".ssot-impact-declared")
        with open(impact_path, "w") as f:
            f.write(ssot_impact)

    @staticmethod
    def _remove_ssot_impact_declared() -> None:
        """ssot_impact 宣言ファイルを削除する。"""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            return
        impact_path = os.path.join(project_dir, ".claude", "logs", ".ssot-impact-declared")
        try:
            os.remove(impact_path)
        except FileNotFoundError:
            pass

    @staticmethod
    def _remove_review_cycle_state() -> None:
        """レビューサイクル状態ファイルを削除する（ワークフロー完了時）。"""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            return
        cycle_path = os.path.join(
            project_dir, ".claude", "logs", ".review-cycle-state.json",
        )
        try:
            os.remove(cycle_path)
        except FileNotFoundError:
            pass

    @staticmethod
    def _generate_state_path(domain: str) -> str:
        """一時ファイルパスを生成する。"""
        h = hashlib.md5(f"{domain}-{time.time()}".encode()).hexdigest()[:8]
        return str(Path(tempfile.gettempdir()) / f"wf-state-{domain}-{h}.json")

    @staticmethod
    def _load_state(state_file: str) -> dict[str, Any]:
        """state.json を読み込む。"""
        p = Path(state_file)
        if not p.exists():
            raise FileNotFoundError(f"状態ファイルが見つかりません: {state_file}")
        with p.open("r", encoding="utf-8") as f:
            state = json.load(f)
        state["_state_file"] = state_file
        return state

    @staticmethod
    def _save_state(state_file: str, state: dict[str, Any]) -> None:
        """state.json を保存する。"""
        data = {k: v for k, v in state.items() if not k.startswith("_")}
        p = Path(state_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ======================================================================
# CLI エントリポイント
# ======================================================================

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ワークフローステップコントローラー",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="ワークフロー初期化")
    p_init.add_argument("domain", help="ドメイン名（例: fix, spec, research）")
    p_init.add_argument("--prompt", required=True, help="タスク内容")
    p_init.add_argument("--teams-yaml", help="teams.yaml のパス（自動検出可）")
    p_init.add_argument("--learned-rules-path", help="learned-rules パス（自動検出可）")
    p_init.add_argument("--state-file", help="状態ファイルのパス（省略時は自動生成）")

    # prereq-done
    p_prereq = sub.add_parser("prereq-done", help="前提ルール完了報告")
    p_prereq.add_argument("--state", required=True, help="state.json のパス")
    p_prereq.add_argument("--work-log", required=True, help="作業ログファイルのパス（必須）")
    p_prereq.add_argument("--ssot-impact", default="none", help="SSoT変更判定（'none' or SSoTファイルリスト）")
    p_prereq.add_argument("--teams-yaml", help="teams.yaml のパス")

    # advance
    p_advance = sub.add_parser("advance", help="フェーズ進行")
    p_advance.add_argument("--state", required=True, help="state.json のパス")
    p_advance.add_argument("--result", required=True, help="result.json のパス")
    p_advance.add_argument("--teams-yaml", help="teams.yaml のパス")

    # resume
    p_resume = sub.add_parser("resume", help="中断再開")
    p_resume.add_argument("--state", required=True, help="state.json のパス")
    p_resume.add_argument("--teams-yaml", help="teams.yaml のパス")

    # phase-approve (S-004)
    p_phase = sub.add_parser("phase-approve", help="Phase単位のapprove（MEANS-LOCKED）を記録")
    p_phase.add_argument("--state", required=True, help="state.json のパス")
    p_phase.add_argument("--phase", required=True, help="approve する Phase 名")
    p_phase.add_argument("--teams-yaml", help="teams.yaml のパス")

    # record-review-cycle
    p_review = sub.add_parser("record-review-cycle", help="レビューサイクル結果を記録")
    p_review.add_argument("--pass", dest="is_pass", action="store_true", help="全軸 Pass の場合")
    p_review.add_argument("--fail", dest="is_fail", action="store_true", help="指摘ありの場合")
    p_review.add_argument("--findings", type=int, default=0, help="指摘件数")
    p_review.add_argument("--cycle", type=int, help="サイクル番号（省略時は自動インクリメント）")

    return parser


def _record_review_cycle(args: argparse.Namespace) -> dict[str, Any]:
    """レビューサイクルの結果（Pass/Fail）を永続記録する。

    .claude/logs/.review-cycle-state.json に連続パス数と履歴を保存。
    workflow_enforce.py の Check h が push 時にこれを読み取り、
    3連続パス未達なら BLOCK する。
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project_dir:
        raise RuntimeError("CLAUDE_PROJECT_DIR が設定されていません。")

    cycle_path = os.path.join(
        project_dir, ".claude", "logs", ".review-cycle-state.json",
    )

    # 既存データの読み込み
    cycle_data: dict[str, Any] = {
        "consecutive_passes": 0,
        "required_passes": 3,
        "total_cycles": 0,
        "history": [],
    }
    if os.path.isfile(cycle_path):
        try:
            with open(cycle_path) as f:
                cycle_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            pass

    is_pass = getattr(args, "is_pass", False)
    is_fail = getattr(args, "is_fail", False)
    findings = getattr(args, "findings", 0)

    if not is_pass and not is_fail:
        # デフォルト: findings > 0 なら fail、0 なら pass
        is_pass = findings == 0

    cycle_num = getattr(args, "cycle", None) or (cycle_data.get("total_cycles", 0) + 1)

    # 更新
    if is_pass:
        cycle_data["consecutive_passes"] = cycle_data.get("consecutive_passes", 0) + 1
    else:
        cycle_data["consecutive_passes"] = 0

    cycle_data["total_cycles"] = cycle_num

    entry = {
        "cycle": cycle_num,
        "pass": is_pass,
        "findings": findings,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    history = cycle_data.get("history", [])
    history.append(entry)
    # 最新10件のみ保持
    cycle_data["history"] = history[-10:]

    # 保存
    log_dir = os.path.dirname(cycle_path)
    os.makedirs(log_dir, exist_ok=True)
    with open(cycle_path, "w") as f:
        json.dump(cycle_data, f, ensure_ascii=False, indent=2)

    return {
        "status": "recorded",
        "cycle": cycle_num,
        "is_pass": is_pass,
        "findings": findings,
        "consecutive_passes": cycle_data["consecutive_passes"],
        "required_passes": cycle_data["required_passes"],
        "converged": cycle_data["consecutive_passes"] >= cycle_data["required_passes"],
    }


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # platform の TeamsConfig/LearnedRulesConfig を直接使用（Tier 2 と同一コード）
    teams_yaml_path = getattr(args, "teams_yaml", None)
    teams = TeamsConfig.load(teams_yaml_path)

    lr_path = getattr(args, "learned_rules_path", None)
    learned_rules = LearnedRulesConfig.load(lr_path)

    core = WorkflowStepCore(teams, learned_rules)

    if args.command == "init":
        result = core.init(args.domain, args.prompt, args.state_file)
    elif args.command == "prereq-done":
        result = core.prereq_done(
            args.state,
            work_log_path=args.work_log,
            ssot_impact=args.ssot_impact,
        )
    elif args.command == "advance":
        with open(args.result, "r", encoding="utf-8") as f:
            phase_result = json.load(f)
        result = core.advance(args.state, phase_result)
    elif args.command == "resume":
        result = core.resume(args.state)
    elif args.command == "phase-approve":
        result = core.phase_approve(args.state, args.phase)
    elif args.command == "record-review-cycle":
        result = _record_review_cycle(args)
    else:
        parser.print_help()
        sys.exit(1)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
