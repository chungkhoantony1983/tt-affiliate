#!/usr/bin/env python3
"""
汎用リソース定義導出スクリプト

WBS CSV + pj-config.yaml → リソース定義.md の費用テーブルを生成

出力内容:
  1. フェーズ×ロール別人日テーブル
  2. フェーズ別金額テーブル（コンティンジェンシー込み）
  3. ゲート×ロールFTEテーブル
  4. 月次FTE計画（ゲート割当）

元スクリプト: Idemitsu/scripts/derive_all_from_master.py (Step 2-4)

使い方:
  python derive_resources.py <PJフォルダパス>
  python derive_resources.py ./Idemitsu
"""

import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

# pj_derive_common.py は同ディレクトリにある想定
sys.path.insert(0, str(Path(__file__).parent))
from pj_derive_common import (
    PjConfig,
    WbsReader,
    InvariantChecker,
    compute_phase_costs,
    compute_gate_role_days,
    compute_gate_fte,
    cost_from_role_days,
)


def find_wbs_csv(pj_root: Path, config: PjConfig) -> Path:
    """WBS CSV のパスを探す"""
    # 標準パターン: {PJ}-002-WBS.csv
    candidates = [
        pj_root / "0_Project" / f"{config.project_id}-002-WBS.csv",
        pj_root / "0_Project" / "WBS.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"WBS CSV が見つかりません。検索パス: {[str(c) for c in candidates]}"
    )


def format_phase_role_table(phase_rd: dict, config: PjConfig) -> str:
    """フェーズ×ロール人日テーブルを Markdown で生成"""
    roles = config.role_ids
    phases = config.phase_ids

    # ヘッダー
    header = "| フェーズ | " + " | ".join(roles) + " | 合計 |"
    sep = "|" + "|".join(["---"] * (len(roles) + 2)) + "|"
    lines = [header, sep]

    total_by_role = defaultdict(Decimal)
    for phase_id in phases:
        rd = phase_rd.get(phase_id, {})
        cells = []
        row_total = Decimal("0")
        for role_id in roles:
            days = rd.get(role_id, Decimal("0"))
            cells.append(f"{float(days):.1f}")
            total_by_role[role_id] += days
            row_total += days
        lines.append(
            f"| {phase_id} | " + " | ".join(cells) + f" | {float(row_total):.1f} |"
        )

    # 合計行
    grand_total = sum(total_by_role.values(), Decimal("0"))
    total_cells = [f"{float(total_by_role.get(r, Decimal('0'))):.1f}" for r in roles]
    lines.append(
        f"| **合計** | " + " | ".join(total_cells) + f" | **{float(grand_total):.1f}** |"
    )

    return "\n".join(lines)


def format_phase_cost_table(phase_costs: dict, config: PjConfig) -> str:
    """フェーズ別金額テーブルを Markdown で生成"""
    phases = config.phase_ids
    lines = [
        "| フェーズ | 金額（税抜） |",
        "|---|---:|",
    ]
    total = 0
    for phase_id in phases:
        cost = phase_costs.get(phase_id, 0)
        total += cost
        lines.append(f"| {phase_id} | ¥{cost:,} |")
    lines.append(f"| **合計** | **¥{total:,}** |")
    return "\n".join(lines)


def format_gate_fte_table(gate_fte: dict, config: PjConfig) -> str:
    """ゲート×ロールFTEテーブルを Markdown で生成"""
    roles = config.role_ids
    header = "| ゲート | 期間(月) | " + " | ".join(roles) + " | 合計FTE |"
    sep = "|" + "|".join(["---"] * (len(roles) + 3)) + "|"
    lines = [header, sep]

    for gate in config.gates:
        gate_id = gate["id"]
        if gate_id not in gate_fte:
            continue
        fte = gate_fte[gate_id]
        months = fte.get("_months", 0)
        cells = [f"{fte.get(r, 0):.2f}" for r in roles]
        total = fte.get("_total", 0)
        lines.append(
            f"| {gate_id} | {months} | " + " | ".join(cells) + f" | {total:.2f} |"
        )

    return "\n".join(lines)


def format_monthly_fte_plan(gate_fte: dict, config: PjConfig) -> str:
    """月次FTE計画テーブルを Markdown で生成"""
    import datetime

    roles = config.role_ids
    start = config.start_date
    end = config.end_date

    # 月ごとのゲート割り当てを構築
    gate_periods = {}
    for gate in config.gates:
        gate_id = gate["id"]
        gs = gate.get("start_date")
        gd = gate.get("deadline")
        if gs and gd:
            gate_periods[gate_id] = (
                datetime.date.fromisoformat(gs) if isinstance(gs, str) else gs,
                datetime.date.fromisoformat(gd) if isinstance(gd, str) else gd,
            )

    # 月リスト生成
    months = []
    cur = start.replace(day=1)
    end_month = end.replace(day=1)
    while cur <= end_month:
        months.append(cur)
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    # ヘッダー
    header = "| 月 | ゲート | " + " | ".join(roles) + " | 合計 |"
    sep = "|" + "|".join(["---"] * (len(roles) + 3)) + "|"
    lines = [header, sep]

    for m in months:
        month_label = m.strftime("%Y-%m")
        # この月に該当するゲートを特定
        active_gate = None
        for gate_id, (gs, gd) in gate_periods.items():
            if gs.replace(day=1) <= m <= gd.replace(day=1):
                active_gate = gate_id
                break

        if active_gate and active_gate in gate_fte:
            fte = gate_fte[active_gate]
            cells = [f"{fte.get(r, 0):.2f}" for r in roles]
            total = fte.get("_total", 0)
            lines.append(
                f"| {month_label} | {active_gate} | "
                + " | ".join(cells)
                + f" | {total:.2f} |"
            )
        else:
            cells = ["0.00"] * len(roles)
            lines.append(
                f"| {month_label} | - | " + " | ".join(cells) + " | 0.00 |"
            )

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("使い方: python derive_resources.py <PJフォルダパス>")
        print("例: python derive_resources.py ./Idemitsu")
        sys.exit(1)

    pj_root = Path(sys.argv[1]).resolve()
    config = PjConfig.load(pj_root)
    wbs_path = find_wbs_csv(pj_root, config)
    wbs = WbsReader(wbs_path, config)

    print(f"=== リソース定義導出: {config.project_id} ({config.project_name}) ===\n")
    print(f"WBS: {wbs_path}")
    print(f"行数: {len(wbs.rows)}")
    print(f"ロール: {config.role_ids}")
    print(f"コンティンジェンシー: {float(config.contingency)*100:.0f}%\n")

    # --- 1. フェーズ×ロール人日 ---
    phase_rd = wbs.phase_role_days()
    print("## フェーズ×ロール人日\n")
    print(format_phase_role_table(phase_rd, config))
    print()

    # --- 2. フェーズ別金額 ---
    phase_costs = compute_phase_costs(phase_rd, config)
    total_cost = sum(phase_costs.values())
    print("## フェーズ別金額\n")
    print(format_phase_cost_table(phase_costs, config))
    print()

    # --- 3. ゲート×ロールFTE ---
    # ゲート分類にはフェーズ×工程分類が必要な場合がある
    # 簡易版: フェーズIDベースの振り分け
    gate_rd = compute_gate_role_days(phase_rd, config)
    gate_fte = compute_gate_fte(gate_rd, config)
    if gate_fte:
        print("## ゲート×ロールFTE\n")
        print(format_gate_fte_table(gate_fte, config))
        print()

    # --- 4. 月次FTE計画 ---
    if gate_fte:
        print("## 月次FTE計画\n")
        print(format_monthly_fte_plan(gate_fte, config))
        print()

    # --- 5. 不変条件検証 ---
    checker = InvariantChecker(config)
    checker.check_total_cost(total_cost)
    checker.check_total_days(float(wbs.total_days()))
    checker.check_phase_costs(phase_costs)
    print(checker.report())

    if not checker.all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
