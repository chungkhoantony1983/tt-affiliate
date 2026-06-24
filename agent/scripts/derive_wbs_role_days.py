#!/usr/bin/env python3
"""
汎用ロール人日配分スクリプト

WBS CSV + pj-config.yaml → WBS CSV にロール人日列を追加

アルゴリズム:
  1. フェーズ×工程のタスク日数を集計
  2. prior_weights で工程別ロール生配分を計算
  3. budget_role_days でフェーズ別キャリブレーション
  4. タスク日数按分で各行に配分
  5. 端数補正（to_cents 整数演算）で予算値と厳密一致

元スクリプト: Idemitsu/scripts/create_master_wbs.py

使い方:
  python derive_wbs_role_days.py <PJフォルダパス>
  python derive_wbs_role_days.py ./Idemitsu
"""

import csv
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pj_derive_common import PjConfig, InvariantChecker, cost_from_role_days


def to_cents(val: float) -> int:
    return int(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)


def from_cents(c: int) -> float:
    return c / 100.0


def find_wbs_csv(pj_root: Path, config: PjConfig) -> Path:
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


def normalize_process(raw: str, valid_keys: list) -> str | None:
    """CSV工程名をprior_weightsキーに正規化。一致なしはNone"""
    raw = raw.strip()
    if not raw:
        return None
    if raw in valid_keys:
        return raw
    for key in valid_keys:
        if key in raw or raw in key:
            return key
    return None


def main():
    if len(sys.argv) < 2:
        print("使い方: python derive_wbs_role_days.py <PJフォルダパス>")
        sys.exit(1)

    pj_root = Path(sys.argv[1]).resolve()
    config = PjConfig.load(pj_root)
    csv_path = find_wbs_csv(pj_root, config)

    prior_weights = config.prior_weights
    budget = config.budget_role_days
    roles = config.role_ids
    phases = config.phase_ids

    if not prior_weights:
        print("ERROR: pj-config.yaml に wbs.prior_weights が未定義です")
        sys.exit(1)
    if not budget:
        print("ERROR: pj-config.yaml に wbs.budget_role_days が未定義です")
        sys.exit(1)

    process_keys = list(prior_weights.keys())

    # ロール列名
    role_col_map = config.role_column_map
    role_cols = [role_col_map[r] for r in roles]
    total_col = config.wbs_columns.get("role_total", "ロール人日計")
    cols_to_strip = set(role_cols + [total_col])

    # ----------------------------------------------------------
    # Step 1: CSV 読み込み（既存ロール列を除外）
    # ----------------------------------------------------------
    cols = config.wbs_columns
    phase_key = cols.get("phase", "フェーズ")
    proc_key = cols.get("process", "工程")
    days_key = cols.get("days", "日数(営業日)")

    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn for fn in reader.fieldnames if fn not in cols_to_strip]
        for row in reader:
            clean = {k: v for k, v in row.items() if k not in cols_to_strip}
            rows.append(clean)

    print(f"読み込み: {len(rows)}行, {len(fieldnames)}列（ロール列除外後）")

    # ----------------------------------------------------------
    # Step 2: フェーズ×工程のタスク日数集計
    # ----------------------------------------------------------
    phase_proc_days = defaultdict(lambda: defaultdict(float))
    task_indices = defaultdict(list)

    for i, row in enumerate(rows):
        phase = row.get(phase_key, "").strip()
        proc_raw = row.get(proc_key, "").strip()
        days_str = row.get(days_key, "").strip()

        if not days_str or days_str == "0" or not phase or phase == "-":
            continue

        proc = normalize_process(proc_raw, process_keys)
        if proc is None:
            continue

        days = float(days_str)
        if days <= 0:
            continue

        phase_proc_days[phase][proc] += days
        task_indices[(phase, proc)].append(i)

    # ----------------------------------------------------------
    # Step 3: キャリブレーション
    # ----------------------------------------------------------
    # raw[phase][proc][role] = proc_days × prior_weight / 100
    raw = {}
    for p in phases:
        raw[p] = {}
        for proc in process_keys:
            raw[p][proc] = {}
            d = phase_proc_days[p].get(proc, 0)
            weights = prior_weights[proc]
            for role in roles:
                w = weights.get(role, 0) if isinstance(weights, dict) else 0
                raw[p][proc][role] = d * w / 100.0

    # scale[phase][role] = budget_target / sum_raw
    scale = {}
    for p in phases:
        scale[p] = {}
        phase_budget = budget.get(p, {})
        for role in roles:
            sum_raw = sum(raw[p][proc][role] for proc in process_keys)
            target = phase_budget.get(role, 0)
            scale[p][role] = target / sum_raw if sum_raw > 0 else 0.0

    # calibrated[phase][proc][role]
    calibrated = {}
    for p in phases:
        calibrated[p] = {}
        for proc in process_keys:
            calibrated[p][proc] = {}
            for role in roles:
                calibrated[p][proc][role] = raw[p][proc][role] * scale[p][role]

    # 検証
    print("\nキャリブレーション検証:")
    for p in phases:
        phase_budget = budget.get(p, {})
        ok = True
        for role in roles:
            computed = sum(calibrated[p][proc][role] for proc in process_keys)
            target = phase_budget.get(role, 0)
            if abs(computed - target) > 0.01:
                print(f"  NG: {p} {role}: computed={computed:.2f}, target={target}")
                ok = False
        if ok:
            print(f"  {p}: OK")

    # ----------------------------------------------------------
    # Step 4: タスク行に配分
    # ----------------------------------------------------------
    task_role_days = {}

    for p in phases:
        for proc in process_keys:
            total_proc = phase_proc_days[p].get(proc, 0)
            if total_proc == 0:
                continue
            for idx in task_indices[(p, proc)]:
                days = float(rows[idx].get(days_key, "0").strip())
                fraction = days / total_proc
                task_role_days[idx] = {
                    role: round(calibrated[p][proc][role] * fraction, 2)
                    for role in roles
                }

    for i in range(len(rows)):
        if i not in task_role_days:
            task_role_days[i] = {role: 0.0 for role in roles}

    # ----------------------------------------------------------
    # Step 5: 端数補正（to_cents 整数演算）
    # ----------------------------------------------------------
    for idx in task_role_days:
        for role in roles:
            task_role_days[idx][role] = to_cents(task_role_days[idx][role])

    for p in phases:
        phase_budget = budget.get(p, {})
        phase_indices = []
        for proc in process_keys:
            phase_indices.extend(task_indices.get((p, proc), []))
        if not phase_indices:
            continue

        for role in roles:
            current = sum(task_role_days[idx][role] for idx in phase_indices)
            target_cents = to_cents(phase_budget.get(role, 0))
            diff = target_cents - current

            if diff == 0:
                continue
            if diff > 0:
                max_idx = max(phase_indices, key=lambda i: task_role_days[i][role])
                task_role_days[max_idx][role] += diff
            else:
                remaining = -diff
                sorted_idx = sorted(
                    [i for i in phase_indices if task_role_days[i][role] > 0],
                    key=lambda i: task_role_days[i][role],
                    reverse=True,
                )
                while remaining > 0 and sorted_idx:
                    for i in sorted_idx:
                        if remaining <= 0:
                            break
                        if task_role_days[i][role] > 0:
                            task_role_days[i][role] -= 1
                            remaining -= 1
                    sorted_idx = [i for i in sorted_idx if task_role_days[i][role] > 0]

    # float に戻す
    for idx in task_role_days:
        for role in roles:
            task_role_days[idx][role] = from_cents(task_role_days[idx][role])

    # ----------------------------------------------------------
    # Step 6: 検証
    # ----------------------------------------------------------
    print("\n端数補正後の検証:")
    unit_prices = config.unit_prices
    all_ok = True
    for p in phases:
        phase_budget = budget.get(p, {})
        phase_indices = []
        for proc in process_keys:
            phase_indices.extend(task_indices.get((p, proc), []))

        for role in roles:
            actual_cents = sum(to_cents(task_role_days[idx][role]) for idx in phase_indices)
            target_cents = to_cents(phase_budget.get(role, 0))
            if actual_cents != target_cents:
                print(f"  NG: {p} {role}: actual={from_cents(actual_cents):.2f}, "
                      f"expected={phase_budget.get(role, 0)}")
                all_ok = False

        # 金額検証
        phase_rd = {role: sum(task_role_days[idx][role] for idx in phase_indices) for role in roles}
        cost = cost_from_role_days(phase_rd, unit_prices, config.contingency)
        print(f"  {p}: ロール人日一致, 金額 ¥{cost:,}")

    if all_ok:
        print("  全フェーズ全ロール一致")

    # 不変条件チェック
    checker = InvariantChecker(config)
    total_rd = {role: Decimal("0") for role in roles}
    for p in phases:
        for proc in process_keys:
            for idx in task_indices.get((p, proc), []):
                for role in roles:
                    total_rd[role] += Decimal(str(task_role_days[idx][role]))
    total_days = sum(total_rd.values())
    total_cost = cost_from_role_days(total_rd, unit_prices, config.contingency)

    checker.check_total_days(float(total_days))
    checker.check_total_cost(total_cost)
    print(checker.report())

    # ----------------------------------------------------------
    # Step 7: CSV 書き出し
    # ----------------------------------------------------------
    new_fieldnames = list(fieldnames) + role_cols + [total_col]

    new_rows = []
    for i, row in enumerate(rows):
        new_row = dict(row)
        total_rd_row = 0.0
        for role in roles:
            col = role_col_map[role]
            val = task_role_days[i][role]
            new_row[col] = f"{val:.2f}" if val > 0 else "0"
            total_rd_row += val
        new_row[total_col] = f"{total_rd_row:.2f}" if total_rd_row > 0 else "0"
        new_rows.append(new_row)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)

    print(f"\n書き出し: {csv_path} ({len(new_rows)}行, {len(new_fieldnames)}列)")
    print(f"追加列: {', '.join(role_cols)}, {total_col}")
    print(f"\n総ロール人日: {float(total_days):.1f}d")
    print(f"総額: ¥{total_cost:,}")


if __name__ == "__main__":
    main()
