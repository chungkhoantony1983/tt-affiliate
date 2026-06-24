#!/usr/bin/env python3
"""
PJ導出スクリプト共通モジュール

Idemitsu の 6 本の導出スクリプトから抽出した共通ロジック:
  - PjConfig: pj-config.yaml のローダー
  - WbsReader: WBS CSV の汎用パーサー
  - InvariantChecker: 不変条件の検証
  - 営業日計算ユーティリティ（is_bd, next_bd, add_bd, sub_bd, bd_count 等）
  - Decimal 計算ユーティリティ

使い方:
  from pj_derive_common import PjConfig, WbsReader, InvariantChecker

出典:
  - level_resources.py: is_bd, next_bd, prev_bd, add_bd, sub_bd, shift_bd, bd_count
  - derive_all_from_master.py: ROLES, UNIT_PRICES, CONTINGENCY, PHASES, GATES
  - create_master_wbs.py: TARGET_RAW, PRIOR_WEIGHTS
"""

import csv
import datetime
import os
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    # PyYAML がない場合は簡易パーサーで対応（CI環境等）
    yaml = None


# ============================================================
# 営業日計算ユーティリティ
# ============================================================
# 出典: level_resources.py L25-72, create_sequential_wbs.py, calc_peak_fte.py
# 全6スクリプトで重複実装されていたものを統合

def is_business_day(d: datetime.date) -> bool:
    """営業日判定（土日のみ除外、祝日は考慮しない）"""
    return d.weekday() < 5


def next_business_day(d: datetime.date) -> datetime.date:
    """d 以降の最初の営業日"""
    while not is_business_day(d):
        d += datetime.timedelta(days=1)
    return d


def prev_business_day(d: datetime.date) -> datetime.date:
    """d 以前の最後の営業日"""
    while not is_business_day(d):
        d -= datetime.timedelta(days=1)
    return d


def add_business_days(start: datetime.date, n: int) -> datetime.date:
    """start から n 営業日後の日付（n=0 は start 自身を返す）"""
    if n <= 0:
        return start
    cur = next_business_day(start)
    for _ in range(n - 1):
        cur += datetime.timedelta(days=1)
        cur = next_business_day(cur)
    return cur


def sub_business_days(end: datetime.date, n: int) -> datetime.date:
    """n BD タスクが end に終わるための最遅開始日"""
    if n <= 0:
        return end
    cur = prev_business_day(end)
    for _ in range(n - 1):
        cur -= datetime.timedelta(days=1)
        cur = prev_business_day(cur)
    return cur


def shift_business_days(start: datetime.date, n: int) -> datetime.date:
    """start から n 営業日「後方にシフト」した日付"""
    d = start
    for _ in range(n):
        d += datetime.timedelta(days=1)
        d = next_business_day(d)
    return d


def business_day_count(start: datetime.date, end: datetime.date) -> int:
    """start から end までの営業日数（両端含む）"""
    n = 0
    d = start
    while d <= end:
        if is_business_day(d):
            n += 1
        d += datetime.timedelta(days=1)
    return n


# ============================================================
# Decimal 計算ユーティリティ
# ============================================================

def parse_decimal(val: str) -> Decimal:
    """文字列を Decimal に変換（空文字列は 0）"""
    if not val or not val.strip():
        return Decimal("0")
    return Decimal(val.strip().replace(",", ""))


def cost_from_role_days(role_days: dict, unit_prices: dict,
                        contingency: Decimal) -> int:
    """ロール別人日と単価から金額を算出（コンティンジェンシー込み）"""
    total = Decimal("0")
    for role_id, days in role_days.items():
        price = unit_prices.get(role_id, 0)
        total += Decimal(str(days)) * Decimal(str(price))
    total_with_contingency = total * (Decimal("1") + contingency)
    return int(total_with_contingency.to_integral_value(rounding=ROUND_HALF_UP))


# ============================================================
# YAML ローダー
# ============================================================

def _load_yaml(path: Path) -> dict:
    """YAML ファイルを読み込む"""
    if yaml is None:
        raise ImportError(
            "PyYAML が必要です。pip install pyyaml でインストールしてください。"
        )
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ============================================================
# PjConfig: pj-config.yaml のローダー
# ============================================================

class PjConfig:
    """pj-config.yaml をロードし、設定値を提供する。

    Idemitsu の 6 スクリプトに散在していた以下の定数を統一的に提供:
      - ROLES, UNIT_PRICES (derive_all_from_master.py)
      - CONTINGENCY (derive_all_from_master.py)
      - PHASES (derive_all_from_master.py)
      - GATES, STAGES (derive_all_from_master.py)
      - PROCESS_NORM (derive_all_from_master.py)
      - EXPECTED_COST, EXPECTED_TOTAL (derive_all_from_master.py)
      - TARGET_RAW, PRIOR_WEIGHTS (create_master_wbs.py)
    """

    def __init__(self, data: dict):
        self._data = data

    @classmethod
    def load(cls, pj_root: Path) -> "PjConfig":
        """PJフォルダ直下の pj-config.yaml をロード"""
        config_path = pj_root / "pj-config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"pj-config.yaml が見つかりません: {config_path}"
            )
        return cls(_load_yaml(config_path))

    @property
    def schema_version(self) -> str:
        return self._data.get("schema_version", "1.0")

    # --- PJ基本情報 ---

    @property
    def project_id(self) -> str:
        return self._data["project"]["id"]

    @property
    def project_name(self) -> str:
        return self._data["project"]["name"]

    @property
    def client(self) -> str:
        return self._data["project"]["client"]

    @property
    def project_type(self) -> str:
        return self._data["project"]["type"]

    @property
    def start_date(self) -> datetime.date:
        return datetime.date.fromisoformat(self._data["project"]["start_date"])

    @property
    def end_date(self) -> datetime.date:
        return datetime.date.fromisoformat(self._data["project"]["end_date"])

    @property
    def contract_type(self) -> str:
        return self._data["project"].get("contract_type", "準委任")

    # --- ロール ---

    @property
    def roles(self) -> list:
        """ロール定義のリスト [{"id": "PM", "name": "...", "unit_price": 120000}, ...]"""
        return self._data.get("roles", [])

    @property
    def role_ids(self) -> list:
        """ロールIDのリスト ["PM", "SA", ...]"""
        return [r["id"] for r in self.roles]

    @property
    def unit_prices(self) -> dict:
        """ロールID → 日額単価 {"PM": 120000, ...}"""
        return {r["id"]: r["unit_price"] for r in self.roles}

    # --- フェーズ ---

    @property
    def phases(self) -> list:
        """フェーズ定義のリスト"""
        return self._data.get("phases", [])

    @property
    def phase_ids(self) -> list:
        """フェーズIDのリスト"""
        return [p["id"] for p in self.phases]

    # --- ゲート ---

    @property
    def gates(self) -> list:
        """ゲート定義のリスト"""
        return self._data.get("gates", [])

    def gate_by_id(self, gate_id: str) -> dict:
        """ゲートIDからゲート定義を取得"""
        for g in self.gates:
            if g["id"] == gate_id:
                return g
        raise KeyError(f"ゲート '{gate_id}' が見つかりません")

    # --- 見積パラメータ ---

    @property
    def contingency(self) -> Decimal:
        return Decimal(str(
            self._data.get("estimate", {}).get("contingency_rate", 0.15)
        ))

    @property
    def business_days_per_month(self) -> int:
        return self._data.get("estimate", {}).get("business_days_per_month", 20)

    @property
    def stages(self) -> list:
        return self._data.get("estimate", {}).get("stages", [])

    @property
    def process_categories(self) -> dict:
        """工程名 → 正規化カテゴリ のマッピング"""
        return self._data.get("estimate", {}).get("process_categories", {})

    # --- WBS設定 ---

    @property
    def wbs_columns(self) -> dict:
        return self._data.get("wbs", {}).get("csv_columns", {})

    @property
    def role_column_map(self) -> dict:
        """ロールID → WBS CSV列名 のマッピング"""
        explicit = self._data.get("wbs", {}).get("csv_columns", {}).get(
            "role_columns", {}
        )
        if explicit:
            return explicit
        # 自動生成: ロールID → "{id}(人日)"
        return {r["id"]: f"{r['id']}(人日)" for r in self.roles}

    @property
    def prior_weights(self) -> dict:
        return self._data.get("wbs", {}).get("prior_weights", {})

    @property
    def budget_role_days(self) -> dict:
        return self._data.get("wbs", {}).get("budget_role_days", {})

    # --- スケジュール設定 ---

    @property
    def schedule_config(self) -> dict:
        return self._data.get("schedule", {})

    @property
    def fte_granularity(self) -> float:
        return self._data.get("schedule", {}).get(
            "leveling", {}
        ).get("fte_granularity", 0.25)

    # --- 不変条件 ---

    @property
    def invariants(self) -> dict:
        return self._data.get("invariants", {})

    @property
    def expected_total_cost(self) -> Optional[int]:
        val = self.invariants.get("total_cost")
        return int(val) if val is not None else None

    @property
    def expected_total_days(self) -> Optional[float]:
        val = self.invariants.get("total_base_days")
        return float(val) if val is not None else None

    @property
    def cost_tolerance(self) -> int:
        return self.invariants.get("cost_tolerance", 8000)

    @property
    def days_tolerance(self) -> float:
        return self.invariants.get("days_tolerance", 0.5)

    # --- エクスポート ---

    @property
    def export_config(self) -> dict:
        return self._data.get("export", {})


# ============================================================
# WbsReader: WBS CSV の汎用パーサー
# ============================================================

class WbsReader:
    """WBS CSVを pj-config のカラムマッピングで解析する。

    使い方:
        config = PjConfig.load(pj_root)
        wbs = WbsReader(pj_root / "0_Project" / f"{config.project_id}-002-WBS.csv", config)
        for row in wbs.rows:
            print(row.phase, row.process, row.days, row.role_days)
    """

    class Row:
        """WBS CSVの1行を表すオブジェクト"""
        def __init__(self, raw: dict, config: PjConfig):
            cols = config.wbs_columns
            self.raw = raw
            self.no = raw.get(cols.get("no", "No"), "")
            self.stream = raw.get(cols.get("stream", "ストリーム"), "")
            self.track = raw.get(cols.get("track", "トラック"), "")
            self.phase = raw.get(cols.get("phase", "フェーズ"), "")
            self.feature_id = raw.get(cols.get("feature_id", "機能ID"), "")
            self.task_name = raw.get(cols.get("task_name", "タスク名"), "")
            self.process = raw.get(cols.get("process", "工程"), "")
            self.days = parse_decimal(
                raw.get(cols.get("days", "日数(営業日)"), "0")
            )
            self.predecessor = raw.get(
                cols.get("predecessor", "先行タスク"), ""
            )
            self.start_date_str = raw.get(
                cols.get("start_date", "開始日"), ""
            )
            self.end_date_str = raw.get(cols.get("end_date", "終了日"), "")
            self.task_id = raw.get(cols.get("task_id", "タスクID"), "")
            self.notes = raw.get(cols.get("notes", "備考"), "")

            # ロール別人日
            role_map = config.role_column_map
            self.role_days = {}
            for role_id, col_name in role_map.items():
                self.role_days[role_id] = parse_decimal(
                    raw.get(col_name, "0")
                )

            # ロール人日合計
            total_col = cols.get("role_total", "ロール人日計")
            self.role_days_total = parse_decimal(raw.get(total_col, "0"))

        @property
        def start_date(self) -> Optional[datetime.date]:
            try:
                return datetime.date.fromisoformat(self.start_date_str)
            except (ValueError, TypeError):
                return None

        @property
        def end_date(self) -> Optional[datetime.date]:
            try:
                return datetime.date.fromisoformat(self.end_date_str)
            except (ValueError, TypeError):
                return None

    def __init__(self, csv_path: Path, config: PjConfig):
        self.csv_path = Path(csv_path)
        self.config = config
        self._rows = None

    @property
    def rows(self) -> list:
        """全行を Row オブジェクトのリストとして返す"""
        if self._rows is None:
            self._rows = self._load()
        return self._rows

    def _load(self) -> list:
        rows = []
        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                rows.append(self.Row(raw, self.config))
        return rows

    def phase_role_days(self) -> dict:
        """フェーズ別ロール別人日を集計

        Returns:
            {phase_id: {role_id: Decimal, ...}, ...}
        """
        result = defaultdict(lambda: defaultdict(Decimal))
        for row in self.rows:
            if not row.phase:
                continue
            proc_cat = self.config.process_categories.get(row.process)
            if proc_cat is None:
                continue  # マイルストーン等は除外
            for role_id, days in row.role_days.items():
                result[row.phase][role_id] += days
        return dict(result)

    def phase_process_role_days(self) -> dict:
        """フェーズ×工程分類×ロール別人日

        Returns:
            {phase_id: {process_category: {role_id: Decimal}}}
        """
        result = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))
        for row in self.rows:
            if not row.phase:
                continue
            proc_cat = self.config.process_categories.get(row.process)
            if proc_cat is None:
                continue
            for role_id, days in row.role_days.items():
                result[row.phase][proc_cat][role_id] += days
        return dict(result)

    def total_role_days(self) -> dict:
        """全体のロール別人日合計

        Returns:
            {role_id: Decimal}
        """
        result = defaultdict(Decimal)
        for row in self.rows:
            proc_cat = self.config.process_categories.get(row.process)
            if proc_cat is None:
                continue
            for role_id, days in row.role_days.items():
                result[role_id] += days
        return dict(result)

    def total_days(self) -> Decimal:
        """全ロール人日合計"""
        return sum(self.total_role_days().values(), Decimal("0"))


# ============================================================
# InvariantChecker: 不変条件の検証
# ============================================================

class InvariantChecker:
    """pj-config.yaml の invariants セクションに定義された不変条件を検証する。

    使い方:
        checker = InvariantChecker(config)
        checker.check_total_cost(actual_total)
        checker.check_total_days(actual_days)
        checker.check_phase_costs(actual_phase_costs)
        report = checker.report()
    """

    def __init__(self, config: PjConfig):
        self.config = config
        self._results = []

    def check_total_cost(self, actual: int) -> bool:
        """総額の検証"""
        expected = self.config.expected_total_cost
        if expected is None:
            self._results.append(("総額", "SKIP", "不変条件未設定"))
            return True
        tolerance = self.config.cost_tolerance
        diff = abs(actual - expected)
        ok = diff <= tolerance
        self._results.append((
            "総額",
            "OK" if ok else "FAIL",
            f"期待: ¥{expected:,} / 実績: ¥{actual:,} / 差分: ¥{diff:,} "
            f"(許容: ¥{tolerance:,})"
        ))
        return ok

    def check_total_days(self, actual: float) -> bool:
        """総ロール人日の検証"""
        expected = self.config.expected_total_days
        if expected is None:
            self._results.append(("総人日", "SKIP", "不変条件未設定"))
            return True
        tolerance = self.config.days_tolerance
        diff = abs(actual - expected)
        ok = diff <= tolerance
        self._results.append((
            "総人日",
            "OK" if ok else "FAIL",
            f"期待: {expected:.1f}d / 実績: {actual:.1f}d / 差分: {diff:.2f}d "
            f"(許容: {tolerance}d)"
        ))
        return ok

    def check_phase_costs(self, actual: dict) -> dict:
        """フェーズ別金額の検証

        Args:
            actual: {phase_id: int}

        Returns:
            {phase_id: bool}
        """
        expected = self.config.invariants.get("phase_costs", {})
        if not expected:
            return {}
        tolerance = self.config.cost_tolerance
        results = {}
        for phase_id, exp_cost in expected.items():
            act_cost = actual.get(phase_id, 0)
            diff = abs(act_cost - exp_cost)
            ok = diff <= tolerance
            results[phase_id] = ok
            self._results.append((
                f"フェーズ {phase_id}",
                "OK" if ok else "FAIL",
                f"期待: ¥{exp_cost:,} / 実績: ¥{act_cost:,} / 差分: ¥{diff:,}"
            ))
        return results

    def report(self) -> str:
        """検証結果のサマリを文字列で返す"""
        lines = ["=== 不変条件検証 ==="]
        all_ok = True
        for label, status, detail in self._results:
            mark = "✓" if status == "OK" else ("⚠" if status == "SKIP" else "✗")
            lines.append(f"  {mark} [{status}] {label}: {detail}")
            if status == "FAIL":
                all_ok = False
        lines.append(f"\n  結果: {'全項目 OK' if all_ok else '検証失敗あり'}")
        return "\n".join(lines)

    @property
    def all_ok(self) -> bool:
        return all(s != "FAIL" for _, s, _ in self._results)


# ============================================================
# ユーティリティ関数
# ============================================================

def compute_phase_costs(phase_role_days: dict, config: PjConfig) -> dict:
    """フェーズ別金額を算出

    Args:
        phase_role_days: {phase_id: {role_id: Decimal}}
        config: PjConfig

    Returns:
        {phase_id: int}
    """
    result = {}
    for phase_id, role_days in phase_role_days.items():
        result[phase_id] = cost_from_role_days(
            {k: float(v) for k, v in role_days.items()},
            config.unit_prices,
            config.contingency
        )
    return result


def compute_gate_role_days(phase_role_days: dict,
                           config: PjConfig) -> dict:
    """ゲート別ロール別人日を算出

    Returns:
        {gate_id: {role_id: Decimal}}
    """
    result = defaultdict(lambda: defaultdict(Decimal))
    for gate in config.gates:
        gate_id = gate["id"]
        for phase_id in gate.get("phase_ids", []):
            if phase_id in phase_role_days:
                for role_id, days in phase_role_days[phase_id].items():
                    # 工程フィルタが設定されている場合はスキップ
                    # （フェーズ×工程の詳細データが必要なら phase_process_role_days を使う）
                    result[gate_id][role_id] += days
    return dict(result)


def compute_gate_fte(gate_role_days: dict, config: PjConfig) -> dict:
    """ゲート別ロール別FTEを算出

    Returns:
        {gate_id: {role_id: float, "_total": float, "_months": int}}
    """
    bd_per_month = config.business_days_per_month
    result = {}
    for gate in config.gates:
        gate_id = gate["id"]
        months = gate.get("months", 0)
        if months <= 0 or gate_id not in gate_role_days:
            continue
        total_bd = months * bd_per_month
        fte = {}
        total_fte = 0.0
        for role_id, days in gate_role_days[gate_id].items():
            f = float(days) / total_bd
            fte[role_id] = round(f, 2)
            total_fte += f
        fte["_total"] = round(total_fte, 2)
        fte["_months"] = months
        result[gate_id] = fte
    return result


# ============================================================
# メイン（テスト用）
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python pj_derive_common.py <PJフォルダパス>")
        print("例: python pj_derive_common.py ./Idemitsu")
        sys.exit(1)

    pj_root = Path(sys.argv[1])
    config = PjConfig.load(pj_root)

    print(f"PJ: {config.project_id} ({config.project_name})")
    print(f"クライアント: {config.client}")
    print(f"タイプ: {config.project_type}")
    print(f"ロール: {config.role_ids}")
    print(f"フェーズ: {config.phase_ids}")
    print(f"コンティンジェンシー: {config.contingency}")

    # WBS CSV があれば読み込みテスト
    wbs_path = pj_root / "0_Project" / f"{config.project_id}-002-WBS.csv"
    if wbs_path.exists():
        wbs = WbsReader(wbs_path, config)
        print(f"\nWBS行数: {len(wbs.rows)}")
        print(f"総ロール人日: {wbs.total_days()}")

        phase_rd = wbs.phase_role_days()
        phase_costs = compute_phase_costs(phase_rd, config)
        total_cost = sum(phase_costs.values())

        print(f"\nフェーズ別金額:")
        for pid, cost in phase_costs.items():
            print(f"  {pid}: ¥{cost:,}")
        print(f"  合計: ¥{total_cost:,}")

        checker = InvariantChecker(config)
        checker.check_total_cost(total_cost)
        checker.check_total_days(float(wbs.total_days()))
        checker.check_phase_costs(phase_costs)
        print(f"\n{checker.report()}")
    else:
        print(f"\nWBS CSV なし: {wbs_path}")
