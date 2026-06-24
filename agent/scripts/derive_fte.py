#!/usr/bin/env python3
"""
汎用FTE導出スクリプト

WBS CSV（日程計算済み）+ pj-config.yaml → 月次ピーク/平均FTEを算出

出力内容:
  1. ロール別人日サマリ
  2. 月次ピークFTEテーブル（体制計画用）
  3. 月次平均FTEテーブル（コスト管理用）
  4. ピーク vs 平均比較
  5. FTE-month比較
  6. リソース定義.md 向け TSV データ

元スクリプト: Idemitsu/scripts/calc_peak_fte.py

使い方:
  python derive_fte.py <PJフォルダパス>
  python derive_fte.py ./Idemitsu

前提:
  WBS CSV に開始日・終了日が設定済みであること
  （derive_wbs_schedule.py で日程計算後に実行）
"""

import datetime
import math
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pj_derive_common import (
    PjConfig,
    WbsReader,
    is_business_day,
    business_day_count,
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


def month_key(d: datetime.date) -> str:
    """日付を YYYY-MM 形式に変換"""
    return d.strftime("%Y-%m")


class Task:
    """FTE計算用のタスクデータ"""

    def __init__(self, row, config: PjConfig, granularity: float = 0.25):
        self.task_id = row.task_id
        self.task_name = row.task_name
        self.phase = row.phase
        self.process = row.process
        self.start = row.start_date
        self.end = row.end_date
        self.role_days = {}  # {role_id: Decimal}
        self.daily_fte = {}  # {role_id: float}

        if self.start is None or self.end is None:
            return

        task_bd = business_day_count(self.start, self.end)
        if task_bd <= 0:
            return

        for role_id, days in row.role_days.items():
            d = float(days)
            if d <= 0:
                continue
            self.role_days[role_id] = days
            # 日次FTE = ロール人日 / タスク営業日数（granularity刻みに切り上げ）
            raw_fte = d / task_bd
            inv = 1.0 / granularity
            self.daily_fte[role_id] = math.ceil(raw_fte * inv) / inv

    @property
    def is_valid(self) -> bool:
        return self.start is not None and self.end is not None and len(self.daily_fte) > 0


def build_daily_histogram(tasks: list, roles: list) -> dict:
    """日次FTEヒストグラムを構築

    Returns:
        {date: {role_id: float}}
    """
    # プロジェクト全期間を特定
    all_starts = [t.start for t in tasks if t.is_valid]
    all_ends = [t.end for t in tasks if t.is_valid]
    if not all_starts:
        return {}

    proj_start = min(all_starts)
    proj_end = max(all_ends)

    histogram = {}
    d = proj_start
    while d <= proj_end:
        if is_business_day(d):
            day_fte = {r: 0.0 for r in roles}
            for task in tasks:
                if not task.is_valid:
                    continue
                if task.start <= d <= task.end and is_business_day(d):
                    for role_id, fte in task.daily_fte.items():
                        if role_id in day_fte:
                            day_fte[role_id] += fte
            histogram[d] = day_fte
        d += datetime.timedelta(days=1)

    return histogram


def aggregate_monthly(histogram: dict, roles: list) -> dict:
    """月次集計

    Returns:
        {month_key: {"peak": {role: float}, "avg": {role: float},
                      "sum": {role: float}, "bd_count": int}}
    """
    # 月ごとにグループ化
    monthly_data = defaultdict(list)
    for d, day_fte in sorted(histogram.items()):
        mk = month_key(d)
        monthly_data[mk].append(day_fte)

    result = {}
    for mk, daily_list in sorted(monthly_data.items()):
        bd = len(daily_list)
        peak = {r: 0.0 for r in roles}
        total = {r: 0.0 for r in roles}

        for day_fte in daily_list:
            for r in roles:
                val = day_fte.get(r, 0.0)
                peak[r] = max(peak[r], val)
                total[r] += val

        avg = {r: total[r] / bd if bd > 0 else 0.0 for r in roles}

        result[mk] = {
            "peak": peak,
            "avg": avg,
            "sum": total,
            "bd_count": bd,
        }

    return result


def format_fte_table(monthly: dict, roles: list, mode: str = "peak") -> str:
    """月次FTEテーブルを Markdown で生成

    Args:
        mode: "peak" or "avg"
    """
    label = "ピークFTE" if mode == "peak" else "平均FTE"
    header = f"| 月 | " + " | ".join(roles) + " | 合計 |"
    sep = "|" + "|".join(["---"] * (len(roles) + 2)) + "|"
    lines = [f"### {label}\n", header, sep]

    for mk in sorted(monthly.keys()):
        data = monthly[mk][mode]
        cells = [f"{data.get(r, 0):.2f}" for r in roles]
        total = sum(data.get(r, 0) for r in roles)
        lines.append(f"| {mk} | " + " | ".join(cells) + f" | {total:.2f} |")

    return "\n".join(lines)


def format_comparison_table(monthly: dict, roles: list) -> str:
    """ピーク vs 平均 比較テーブル"""
    lines = [
        "### ピーク vs 平均 比較\n",
        "| 月 | ピーク合計 | 平均合計 | 差分 | 増加率 |",
        "|---|---:|---:|---:|---:|",
    ]

    for mk in sorted(monthly.keys()):
        peak_total = sum(monthly[mk]["peak"].get(r, 0) for r in roles)
        avg_total = sum(monthly[mk]["avg"].get(r, 0) for r in roles)
        diff = peak_total - avg_total
        rate = (peak_total / avg_total - 1) * 100 if avg_total > 0 else 0
        lines.append(
            f"| {mk} | {peak_total:.2f} | {avg_total:.2f} | "
            f"+{diff:.2f} | +{rate:.0f}% |"
        )

    return "\n".join(lines)


def format_fte_month_comparison(monthly: dict, roles: list) -> str:
    """FTE-month 比較（平均方式 vs ピーク方式）"""
    total_peak_fm = {r: 0.0 for r in roles}
    total_avg_fm = {r: 0.0 for r in roles}

    for mk, data in monthly.items():
        for r in roles:
            total_peak_fm[r] += data["peak"].get(r, 0)
            total_avg_fm[r] += data["avg"].get(r, 0)

    lines = [
        "### FTE-month 比較\n",
        "| ロール | 平均方式 | ピーク方式 | 差分 | 増加率 |",
        "|---|---:|---:|---:|---:|",
    ]

    grand_peak = 0.0
    grand_avg = 0.0
    for r in roles:
        p = total_peak_fm[r]
        a = total_avg_fm[r]
        d = p - a
        rate = (p / a - 1) * 100 if a > 0 else 0
        grand_peak += p
        grand_avg += a
        lines.append(f"| {r} | {a:.1f} | {p:.1f} | +{d:.1f} | +{rate:.0f}% |")

    gdiff = grand_peak - grand_avg
    grate = (grand_peak / grand_avg - 1) * 100 if grand_avg > 0 else 0
    lines.append(
        f"| **合計** | **{grand_avg:.1f}** | **{grand_peak:.1f}** | "
        f"**+{gdiff:.1f}** | **+{grate:.0f}%** |"
    )

    return "\n".join(lines)


def format_tsv_for_resource_def(monthly: dict, roles: list) -> str:
    """リソース定義.md 向け TSV データ（ピークFTE）"""
    lines = ["### リソース定義.md 向けデータ（TSV: ピークFTE）\n"]
    lines.append("月\t" + "\t".join(roles) + "\t合計")

    for mk in sorted(monthly.keys()):
        data = monthly[mk]["peak"]
        cells = [f"{data.get(r, 0):.2f}" for r in roles]
        total = sum(data.get(r, 0) for r in roles)
        lines.append(f"{mk}\t" + "\t".join(cells) + f"\t{total:.2f}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("使い方: python derive_fte.py <PJフォルダパス>")
        print("例: python derive_fte.py ./Idemitsu")
        sys.exit(1)

    pj_root = Path(sys.argv[1]).resolve()
    config = PjConfig.load(pj_root)
    wbs_path = find_wbs_csv(pj_root, config)
    wbs = WbsReader(wbs_path, config)
    roles = config.role_ids
    granularity = config.fte_granularity

    print(f"=== FTE導出: {config.project_id} ({config.project_name}) ===\n")
    print(f"WBS: {wbs_path}")
    print(f"FTE刻み: {granularity}")
    print(f"行数: {len(wbs.rows)}\n")

    # --- 1. タスク読み込み ---
    tasks = []
    skipped = 0
    for row in wbs.rows:
        proc_cat = config.process_categories.get(row.process)
        if proc_cat is None:
            skipped += 1
            continue
        task = Task(row, config, granularity)
        if task.is_valid:
            tasks.append(task)
        else:
            skipped += 1

    print(f"有効タスク: {len(tasks)} / スキップ: {skipped}\n")

    if not tasks:
        print("⚠ 有効なタスクがありません（開始日・終了日が未設定の可能性）")
        print("  derive_wbs_schedule.py で日程計算を先に実行してください。")
        sys.exit(1)

    # --- 2. ロール人日サマリ ---
    total_rd = defaultdict(Decimal)
    for task in tasks:
        for role_id, days in task.role_days.items():
            total_rd[role_id] += days

    print("## ロール別人日サマリ\n")
    print("| ロール | 人日合計 |")
    print("|---|---:|")
    grand = Decimal("0")
    for r in roles:
        d = total_rd.get(r, Decimal("0"))
        grand += d
        print(f"| {r} | {float(d):.1f} |")
    print(f"| **合計** | **{float(grand):.1f}** |")
    print()

    # --- 3. 日次ヒストグラム構築 ---
    histogram = build_daily_histogram(tasks, roles)
    if not histogram:
        print("⚠ ヒストグラムが空です")
        sys.exit(1)

    dates = sorted(histogram.keys())
    print(f"期間: {dates[0]} ~ {dates[-1]} ({len(dates)} 営業日)\n")

    # --- 4. 月次集計 ---
    monthly = aggregate_monthly(histogram, roles)

    # --- 5. ピークFTEテーブル ---
    print(format_fte_table(monthly, roles, "peak"))
    print()

    # --- 6. 平均FTEテーブル ---
    print(format_fte_table(monthly, roles, "avg"))
    print()

    # --- 7. ピーク vs 平均 比較 ---
    print(format_comparison_table(monthly, roles))
    print()

    # --- 8. FTE-month 比較 ---
    print(format_fte_month_comparison(monthly, roles))
    print()

    # --- 9. リソース定義.md 向け TSV ---
    print(format_tsv_for_resource_def(monthly, roles))
    print()

    # --- 10. 全期間サマリ ---
    print("### 全期間サマリ\n")
    overall_peak = {r: 0.0 for r in roles}
    for mk, data in monthly.items():
        for r in roles:
            overall_peak[r] = max(overall_peak[r], data["peak"].get(r, 0))

    print("| ロール | 全期間ピークFTE |")
    print("|---|---:|")
    for r in roles:
        print(f"| {r} | {overall_peak[r]:.2f} |")
    total_peak = sum(overall_peak.values())
    print(f"| **合計** | **{total_peak:.2f}** |")


if __name__ == "__main__":
    main()
