#!/usr/bin/env python3
"""
汎用見積書導出スクリプト

WBS CSV + pj-config.yaml → 見積書.md の金額テーブルを生成

出力内容:
  1. 段階見積サマリ（Stage 1-N）
  2. 要件定義/それ以外 按分
  3. ロール別コスト内訳
  4. 不変条件検証

元スクリプト: Idemitsu/scripts/derive_all_from_master.py (Step 5-7)

使い方:
  python derive_estimate.py <PJフォルダパス>
  python derive_estimate.py ./Idemitsu
"""

import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pj_derive_common import (
    PjConfig,
    WbsReader,
    InvariantChecker,
    compute_phase_costs,
    cost_from_role_days,
)


def find_wbs_csv(pj_root: Path, config: PjConfig) -> Path:
    """WBS CSV のパスを探す"""
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


def compute_stage_estimates(wbs: WbsReader, config: PjConfig) -> list:
    """段階見積を算出

    Returns:
        [{"id": str, "label": str, "role_days": {role: Decimal},
          "cost": int, "cumulative_cost": int}, ...]
    """
    # フェーズ別ロール人日
    phase_rd = wbs.phase_role_days()
    # フェーズ×工程分類別ロール人日
    phase_proc_rd = wbs.phase_process_role_days()
    stages = config.stages

    results = []
    cumulative = 0

    for stage in stages:
        stage_id = stage["id"]
        label = stage.get("label", stage_id)
        gate_ids = stage.get("gate_ids", [])
        phase_ids = stage.get("phase_ids", [])
        proc_filter = stage.get("process_filter")

        # この段階に含まれるロール人日を集計
        stage_role_days = defaultdict(Decimal)

        if phase_ids:
            # フェーズIDベースで集計
            for pid in phase_ids:
                if proc_filter and pid in phase_proc_rd:
                    # 工程フィルタあり
                    proc_data = phase_proc_rd[pid]
                    if proc_filter in proc_data:
                        for role_id, days in proc_data[proc_filter].items():
                            stage_role_days[role_id] += days
                elif pid in phase_rd:
                    # フィルタなし: フェーズ全体
                    for role_id, days in phase_rd[pid].items():
                        stage_role_days[role_id] += days
        elif gate_ids:
            # ゲートIDベースで集計（フェーズIDが未指定の場合）
            for gate in config.gates:
                if gate["id"] in gate_ids:
                    for pid in gate.get("phase_ids", []):
                        gf = gate.get("process_filter")
                        if gf and pid in phase_proc_rd:
                            proc_data = phase_proc_rd[pid]
                            if gf in proc_data:
                                for role_id, days in proc_data[gf].items():
                                    stage_role_days[role_id] += days
                        elif pid in phase_rd:
                            for role_id, days in phase_rd[pid].items():
                                stage_role_days[role_id] += days

        cost = cost_from_role_days(
            {k: float(v) for k, v in stage_role_days.items()},
            config.unit_prices,
            config.contingency,
        )
        cumulative += cost

        results.append({
            "id": stage_id,
            "label": label,
            "role_days": dict(stage_role_days),
            "cost": cost,
            "cumulative_cost": cumulative,
        })

    return results


def compute_process_breakdown(wbs: WbsReader, config: PjConfig) -> dict:
    """要件定義/それ以外の按分を算出

    Returns:
        {phase_id: {process_category: {"role_days": {role: Decimal}, "cost": int}}}
    """
    phase_proc_rd = wbs.phase_process_role_days()
    result = {}

    for phase_id, proc_data in phase_proc_rd.items():
        result[phase_id] = {}
        for proc_cat, role_days in proc_data.items():
            cost = cost_from_role_days(
                {k: float(v) for k, v in role_days.items()},
                config.unit_prices,
                config.contingency,
            )
            result[phase_id][proc_cat] = {
                "role_days": dict(role_days),
                "cost": cost,
            }

    return result


def format_stage_table(stage_estimates: list, config: PjConfig) -> str:
    """段階見積テーブルを Markdown で生成"""
    roles = config.role_ids
    header = "| 段階 | " + " | ".join(roles) + " | 金額 | 累計 |"
    sep = "|" + "|".join(["---"] * (len(roles) + 3)) + "|"
    lines = [header, sep]

    for stage in stage_estimates:
        rd = stage["role_days"]
        cells = [f"{float(rd.get(r, Decimal('0'))):.1f}" for r in roles]
        lines.append(
            f"| {stage['label']} | "
            + " | ".join(cells)
            + f" | ¥{stage['cost']:,} | ¥{stage['cumulative_cost']:,} |"
        )

    return "\n".join(lines)


def format_process_breakdown_table(breakdown: dict, config: PjConfig) -> str:
    """工程分類別金額テーブルを Markdown で生成"""
    phases = config.phase_ids
    # 全工程分類を収集
    all_cats = set()
    for proc_data in breakdown.values():
        all_cats.update(proc_data.keys())
    cats = sorted(all_cats)

    if not cats:
        return "(工程分類データなし)"

    header = "| フェーズ | " + " | ".join(cats) + " | 合計 |"
    sep = "|" + "|".join(["---"] * (len(cats) + 2)) + "|"
    lines = [header, sep]

    total_by_cat = defaultdict(int)
    for phase_id in phases:
        if phase_id not in breakdown:
            continue
        proc_data = breakdown[phase_id]
        cells = []
        row_total = 0
        for cat in cats:
            cost = proc_data.get(cat, {}).get("cost", 0)
            cells.append(f"¥{cost:,}")
            total_by_cat[cat] += cost
            row_total += cost
        lines.append(
            f"| {phase_id} | " + " | ".join(cells) + f" | ¥{row_total:,} |"
        )

    grand_total = sum(total_by_cat.values())
    total_cells = [f"¥{total_by_cat.get(c, 0):,}" for c in cats]
    lines.append(
        f"| **合計** | " + " | ".join(total_cells) + f" | **¥{grand_total:,}** |"
    )

    return "\n".join(lines)


def format_role_cost_table(phase_rd: dict, config: PjConfig) -> str:
    """ロール別コスト内訳テーブルを Markdown で生成"""
    roles = config.role_ids
    unit_prices = config.unit_prices
    contingency = config.contingency

    # ロール別の合計人日
    total_by_role = defaultdict(Decimal)
    for rd in phase_rd.values():
        for role_id, days in rd.items():
            total_by_role[role_id] += days

    lines = [
        "| ロール | 日額単価 | 人日合計 | 基本金額 | コンティンジェンシー込み |",
        "|---|---:|---:|---:|---:|",
    ]

    grand_base = Decimal("0")
    grand_with_cont = Decimal("0")
    for role_id in roles:
        days = total_by_role.get(role_id, Decimal("0"))
        price = unit_prices.get(role_id, 0)
        base = days * Decimal(str(price))
        with_cont = base * (Decimal("1") + contingency)
        with_cont_int = int(with_cont.to_integral_value(rounding=ROUND_HALF_UP))
        grand_base += base
        grand_with_cont += with_cont
        lines.append(
            f"| {role_id} | ¥{price:,} | {float(days):.1f} | "
            f"¥{int(base):,} | ¥{with_cont_int:,} |"
        )

    grand_with_cont_int = int(
        grand_with_cont.to_integral_value(rounding=ROUND_HALF_UP)
    )
    lines.append(
        f"| **合計** | - | "
        f"{float(sum(total_by_role.values(), Decimal('0'))):.1f} | "
        f"**¥{int(grand_base):,}** | **¥{grand_with_cont_int:,}** |"
    )

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("使い方: python derive_estimate.py <PJフォルダパス>")
        print("例: python derive_estimate.py ./Idemitsu")
        sys.exit(1)

    pj_root = Path(sys.argv[1]).resolve()
    config = PjConfig.load(pj_root)
    wbs_path = find_wbs_csv(pj_root, config)
    wbs = WbsReader(wbs_path, config)

    print(f"=== 見積導出: {config.project_id} ({config.project_name}) ===\n")
    print(f"WBS: {wbs_path}")
    print(f"コンティンジェンシー: {float(config.contingency)*100:.0f}%\n")

    # --- 1. フェーズ別金額 ---
    phase_rd = wbs.phase_role_days()
    phase_costs = compute_phase_costs(phase_rd, config)
    total_cost = sum(phase_costs.values())

    print("## ロール別コスト内訳\n")
    print(format_role_cost_table(phase_rd, config))
    print()

    # --- 2. 段階見積 ---
    if config.stages:
        stage_estimates = compute_stage_estimates(wbs, config)
        print("## 段階見積サマリ\n")
        print(format_stage_table(stage_estimates, config))
        print()

        # 検証: 最終段階の累計が総額と一致するか
        if stage_estimates:
            last_cumulative = stage_estimates[-1]["cumulative_cost"]
            diff = abs(last_cumulative - total_cost)
            if diff > config.cost_tolerance:
                print(
                    f"⚠ 段階見積累計 (¥{last_cumulative:,}) と "
                    f"フェーズ合計 (¥{total_cost:,}) の差分: ¥{diff:,}"
                )
    else:
        print("(段階見積未設定)\n")

    # --- 3. 要件定義/それ以外 按分 ---
    breakdown = compute_process_breakdown(wbs, config)
    if breakdown:
        print("## 工程分類別金額\n")
        print(format_process_breakdown_table(breakdown, config))
        print()

    # --- 4. 不変条件検証 ---
    checker = InvariantChecker(config)
    checker.check_total_cost(total_cost)
    checker.check_total_days(float(wbs.total_days()))
    checker.check_phase_costs(phase_costs)
    print(checker.report())

    if not checker.all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
