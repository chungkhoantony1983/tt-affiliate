#!/usr/bin/env python3
"""
汎用WBS日程計算スクリプト

WBS CSV + pj-config.yaml → ASAP日程算出 + リソースレベリング

処理フロー:
  1. WBS CSV 読み込み
  2. pj-config の schedule 設定を適用（追加タスク、先行タスク修正、日数修正）
  3. ゲート分類（pj-config の gates/phases 設定に基づく）
  4. ゲートごとにASAP日程算出（トポロジカルソート + 先行タスク制約）
  5. リソースレベリング（FTE変動の平滑化）
  6. 更新済みCSV出力

元スクリプト:
  - create_sequential_wbs.py（ASAP日程算出）
  - level_resources.py（リソースレベリング）

使い方:
  python derive_wbs_schedule.py <PJフォルダパス> [--no-leveling]
  python derive_wbs_schedule.py ./Idemitsu

出力:
  WBS CSV を上書き更新（開始日・終了日列を更新）
"""

import csv
import datetime
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pj_derive_common import (
    PjConfig,
    is_business_day,
    next_business_day,
    prev_business_day,
    add_business_days,
    sub_business_days,
    shift_business_days,
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


# ============================================================
# CSV 読み込み・前処理
# ============================================================

def load_csv(csv_path: Path) -> tuple:
    """CSV を読み込み、(fieldnames, rows) を返す"""
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    return fieldnames, rows


def apply_schedule_config(rows: list, config: PjConfig) -> list:
    """pj-config の schedule 設定を適用

    - extra_tasks: 追加タスク
    - predecessor_fixes: 先行タスク修正
    - duration_fixes: 日数修正
    """
    sched = config.schedule_config
    cols = config.wbs_columns

    # 追加タスクの挿入
    extra_tasks = sched.get("extra_tasks", [])
    if extra_tasks:
        task_id_col = cols.get("task_id", "タスクID")
        # 挿入位置を特定（タスクIDの直後に挿入）
        for extra in extra_tasks:
            after_id = extra.get("after")
            if after_id:
                idx = next(
                    (i for i, r in enumerate(rows)
                     if r.get(task_id_col, "") == after_id),
                    len(rows) - 1,
                )
                rows.insert(idx + 1, extra.get("row", {}))
            else:
                rows.append(extra.get("row", {}))

    # 先行タスク修正
    pred_fixes = sched.get("predecessor_fixes", {})
    if pred_fixes:
        task_id_col = cols.get("task_id", "タスクID")
        pred_col = cols.get("predecessor", "先行タスク")
        for row in rows:
            tid = row.get(task_id_col, "")
            if tid in pred_fixes:
                preds = pred_fixes[tid]
                if isinstance(preds, list):
                    row[pred_col] = ",".join(preds)
                else:
                    row[pred_col] = str(preds)

    # 日数修正
    dur_fixes = sched.get("duration_fixes", {})
    if dur_fixes:
        task_id_col = cols.get("task_id", "タスクID")
        days_col = cols.get("days", "日数(営業日)")
        for row in rows:
            tid = row.get(task_id_col, "")
            if tid in dur_fixes:
                row[days_col] = str(dur_fixes[tid])

    return rows


# ============================================================
# ゲート分類
# ============================================================

def classify_tasks_by_gate(rows: list, config: PjConfig) -> dict:
    """各タスクをゲートに分類

    Returns:
        {gate_id: [row_index, ...]}
    """
    cols = config.wbs_columns
    phase_col = cols.get("phase", "フェーズ")
    process_col = cols.get("process", "工程")
    proc_cats = config.process_categories

    # フェーズ → ゲートのマッピングを構築
    phase_to_gates = {}
    for gate in config.gates:
        gate_id = gate["id"]
        proc_filter = gate.get("process_filter")
        for pid in gate.get("phase_ids", []):
            if pid not in phase_to_gates:
                phase_to_gates[pid] = []
            phase_to_gates[pid].append((gate_id, proc_filter))

    result = defaultdict(list)
    unclassified = []

    for i, row in enumerate(rows):
        phase = row.get(phase_col, "")
        process = row.get(process_col, "")
        proc_cat = proc_cats.get(process)

        if phase not in phase_to_gates:
            unclassified.append(i)
            continue

        matched = False
        for gate_id, proc_filter in phase_to_gates[phase]:
            if proc_filter is None:
                # フィルタなし → 全工程がこのゲート
                result[gate_id].append(i)
                matched = True
                break
            elif proc_filter == proc_cat:
                result[gate_id].append(i)
                matched = True
                break

        if not matched:
            # どのゲートにもマッチしない場合、最初のフィルタなしゲートに割り当て
            for gate_id, proc_filter in phase_to_gates[phase]:
                if proc_filter is None:
                    result[gate_id].append(i)
                    matched = True
                    break
            if not matched:
                unclassified.append(i)

    return dict(result), unclassified


# ============================================================
# ASAP スケジューリング
# ============================================================

def topo_sort(task_indices: list, predecessors: dict) -> list:
    """トポロジカルソート（BFS / Kahn's algorithm）"""
    index_set = set(task_indices)

    # ゲート内の依存関係のみを考慮
    in_degree = {i: 0 for i in task_indices}
    adj = defaultdict(list)

    for i in task_indices:
        for pred_idx in predecessors.get(i, []):
            if pred_idx in index_set:
                adj[pred_idx].append(i)
                in_degree[i] += 1

    queue = deque([i for i in task_indices if in_degree[i] == 0])
    order = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


def schedule_gate_asap(rows: list, task_indices: list,
                       predecessors: dict, gate_start: datetime.date,
                       config: PjConfig) -> None:
    """ゲート内のタスクをASAPでスケジュール"""
    cols = config.wbs_columns
    days_col = cols.get("days", "日数(営業日)")
    start_col = cols.get("start_date", "開始日")
    end_col = cols.get("end_date", "終了日")

    order = topo_sort(task_indices, predecessors)
    index_set = set(task_indices)

    for i in order:
        row = rows[i]
        days_str = row.get(days_col, "0").strip()
        try:
            days = int(float(days_str)) if days_str else 0
        except ValueError:
            days = 0

        if days <= 0:
            # マイルストーン等: 先行タスクの最終日 or ゲート開始
            latest_end = gate_start
            for pred_idx in predecessors.get(i, []):
                pred_end_str = rows[pred_idx].get(end_col, "")
                if pred_end_str:
                    try:
                        pred_end = datetime.date.fromisoformat(pred_end_str)
                        if pred_end > latest_end:
                            latest_end = pred_end
                    except ValueError:
                        pass
            row[start_col] = str(latest_end)
            row[end_col] = str(latest_end)
            continue

        # 開始日 = max(ゲート開始, 全先行タスク終了日+1BD)
        earliest_start = next_business_day(gate_start)
        for pred_idx in predecessors.get(i, []):
            pred_end_str = rows[pred_idx].get(end_col, "")
            if pred_end_str:
                try:
                    pred_end = datetime.date.fromisoformat(pred_end_str)
                    candidate = shift_business_days(pred_end, 1)
                    if candidate > earliest_start:
                        earliest_start = candidate
                except ValueError:
                    pass

        start = next_business_day(earliest_start)
        end = add_business_days(start, days)

        row[start_col] = str(start)
        row[end_col] = str(end)


# ============================================================
# リソースレベリング
# ============================================================

class Histogram:
    """日別FTE合計を管理"""

    def __init__(self):
        self._data = defaultdict(float)

    def add(self, start: datetime.date, end: datetime.date, daily_fte: float):
        d = start
        while d <= end:
            if is_business_day(d):
                self._data[d] += daily_fte
            d += datetime.timedelta(days=1)

    def remove(self, start: datetime.date, end: datetime.date, daily_fte: float):
        d = start
        while d <= end:
            if is_business_day(d):
                self._data[d] -= daily_fte
            d += datetime.timedelta(days=1)

    def peak(self, start: datetime.date = None, end: datetime.date = None) -> float:
        vals = []
        for d, v in self._data.items():
            if start and d < start:
                continue
            if end and d > end:
                continue
            vals.append(v)
        return max(vals) if vals else 0.0


def compute_task_daily_fte(row: dict, config: PjConfig) -> float:
    """タスクの日次FTE合計を算出"""
    cols = config.wbs_columns
    role_map = config.role_column_map
    days_col = cols.get("days", "日数(営業日)")
    start_col = cols.get("start_date", "開始日")
    end_col = cols.get("end_date", "終了日")

    start_str = row.get(start_col, "")
    end_str = row.get(end_col, "")
    if not start_str or not end_str:
        return 0.0

    try:
        start = datetime.date.fromisoformat(start_str)
        end = datetime.date.fromisoformat(end_str)
    except ValueError:
        return 0.0

    task_bd = business_day_count(start, end)
    if task_bd <= 0:
        return 0.0

    total_role_days = 0.0
    for role_id, col_name in role_map.items():
        val = row.get(col_name, "0").strip()
        try:
            total_role_days += float(val) if val else 0.0
        except ValueError:
            pass

    return total_role_days / task_bd if task_bd > 0 else 0.0


def backward_pass(rows: list, task_indices: list, predecessors: dict,
                  successors: dict, gate_deadline: datetime.date,
                  config: PjConfig) -> dict:
    """後退パスで最遅開始日（LS）を算出

    Returns:
        {row_index: datetime.date}
    """
    cols = config.wbs_columns
    days_col = cols.get("days", "日数(営業日)")
    end_col = cols.get("end_date", "終了日")
    index_set = set(task_indices)

    # 逆トポロジカル順
    order = topo_sort(task_indices, predecessors)
    order.reverse()

    ls = {}
    for i in order:
        row = rows[i]
        days_str = row.get(days_col, "0").strip()
        try:
            days = int(float(days_str)) if days_str else 0
        except ValueError:
            days = 0

        if days <= 0:
            ls[i] = gate_deadline
            continue

        # 後続タスクの最遅開始日から逆算
        latest_finish = gate_deadline
        for succ_idx in successors.get(i, []):
            if succ_idx in index_set and succ_idx in ls:
                # 後続タスクのLS - 1BD
                candidate = prev_business_day(
                    ls[succ_idx] - datetime.timedelta(days=1)
                )
                if candidate < latest_finish:
                    latest_finish = candidate

        # LS = 最遅終了日 - タスク日数 + 1
        ls[i] = sub_business_days(latest_finish, days)

    return ls


def level_gate(rows: list, task_indices: list, predecessors: dict,
               successors: dict, gate_start: datetime.date,
               gate_deadline: datetime.date, config: PjConfig,
               max_trial_points: int = 20) -> None:
    """ゲート内タスクのリソースレベリング"""
    cols = config.wbs_columns
    days_col = cols.get("days", "日数(営業日)")
    start_col = cols.get("start_date", "開始日")
    end_col = cols.get("end_date", "終了日")

    index_set = set(task_indices)
    order = topo_sort(task_indices, predecessors)

    # LS算出
    ls = backward_pass(rows, task_indices, predecessors, successors,
                       gate_deadline, config)

    # ヒストグラム構築
    hist = Histogram()
    for i in task_indices:
        row = rows[i]
        fte = compute_task_daily_fte(row, config)
        if fte <= 0:
            continue
        start_str = row.get(start_col, "")
        end_str = row.get(end_col, "")
        if start_str and end_str:
            try:
                s = datetime.date.fromisoformat(start_str)
                e = datetime.date.fromisoformat(end_str)
                hist.add(s, e, fte)
            except ValueError:
                pass

    # レベリング
    for i in order:
        row = rows[i]
        days_str = row.get(days_col, "0").strip()
        try:
            days = int(float(days_str)) if days_str else 0
        except ValueError:
            days = 0

        if days <= 0:
            continue

        fte = compute_task_daily_fte(row, config)
        if fte <= 0:
            continue

        # 現在の配置を削除
        cur_start_str = row.get(start_col, "")
        cur_end_str = row.get(end_col, "")
        if cur_start_str and cur_end_str:
            try:
                cur_s = datetime.date.fromisoformat(cur_start_str)
                cur_e = datetime.date.fromisoformat(cur_end_str)
                hist.remove(cur_s, cur_e, fte)
            except ValueError:
                pass

        # ES = max(ゲート開始, 先行タスク終了+1BD)
        es = next_business_day(gate_start)
        for pred_idx in predecessors.get(i, []):
            pred_end_str = rows[pred_idx].get(end_col, "")
            if pred_end_str:
                try:
                    pred_end = datetime.date.fromisoformat(pred_end_str)
                    candidate = shift_business_days(pred_end, 1)
                    if candidate > es:
                        es = candidate
                except ValueError:
                    pass

        # LS
        task_ls = ls.get(i, gate_deadline)

        # Float = LS - ES（営業日数）
        es = next_business_day(es)
        float_days = business_day_count(es, task_ls)

        if float_days <= 0:
            # クリティカル: ESに配置
            best_start = es
        else:
            # [ES, LS] 内で試行
            trial_count = min(max_trial_points, float_days + 1)
            step = max(1, float_days // trial_count)

            best_start = es
            best_peak = float("inf")

            trial_start = es
            for _ in range(trial_count):
                trial_end = add_business_days(trial_start, days)
                # 仮配置してピークを測定
                hist.add(trial_start, trial_end, fte)
                peak = hist.peak(gate_start, gate_deadline)
                hist.remove(trial_start, trial_end, fte)

                if peak < best_peak:
                    best_peak = peak
                    best_start = trial_start

                trial_start = shift_business_days(trial_start, step)
                if trial_start > task_ls:
                    break

        # 最適位置に配置
        best_end = add_business_days(best_start, days)
        row[start_col] = str(best_start)
        row[end_col] = str(best_end)
        hist.add(best_start, best_end, fte)


# ============================================================
# 先行タスク解析
# ============================================================

def build_predecessor_map(rows: list, config: PjConfig) -> tuple:
    """先行タスク/後続タスクのマッピングを構築

    Returns:
        (predecessors, successors):
            predecessors: {row_index: [pred_row_index, ...]}
            successors: {row_index: [succ_row_index, ...]}
    """
    cols = config.wbs_columns
    task_id_col = cols.get("task_id", "タスクID")
    pred_col = cols.get("predecessor", "先行タスク")

    # タスクID → row index
    id_to_idx = {}
    for i, row in enumerate(rows):
        tid = row.get(task_id_col, "").strip()
        if tid:
            id_to_idx[tid] = i

    predecessors = defaultdict(list)
    successors = defaultdict(list)

    for i, row in enumerate(rows):
        pred_str = row.get(pred_col, "").strip()
        if not pred_str:
            continue
        for pred_id in pred_str.split(","):
            pred_id = pred_id.strip()
            if pred_id in id_to_idx:
                pred_idx = id_to_idx[pred_id]
                predecessors[i].append(pred_idx)
                successors[pred_idx].append(i)

    return dict(predecessors), dict(successors)


# ============================================================
# CSV 出力
# ============================================================

def write_csv(csv_path: Path, fieldnames: list, rows: list) -> None:
    """CSV を書き出す"""
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# 月次ピークFTEサマリ
# ============================================================

def print_monthly_peak_summary(rows: list, config: PjConfig) -> None:
    """月次ピークFTE概要を出力"""
    cols = config.wbs_columns
    start_col = cols.get("start_date", "開始日")
    end_col = cols.get("end_date", "終了日")
    role_map = config.role_column_map
    roles = config.role_ids

    # 日次ヒストグラム構築
    daily = defaultdict(lambda: {r: 0.0 for r in roles})

    for row in rows:
        start_str = row.get(start_col, "")
        end_str = row.get(end_col, "")
        if not start_str or not end_str:
            continue
        try:
            start = datetime.date.fromisoformat(start_str)
            end = datetime.date.fromisoformat(end_str)
        except ValueError:
            continue

        task_bd = business_day_count(start, end)
        if task_bd <= 0:
            continue

        for role_id, col_name in role_map.items():
            val = row.get(col_name, "0").strip()
            try:
                rd = float(val) if val else 0.0
            except ValueError:
                rd = 0.0
            if rd <= 0:
                continue
            daily_fte = rd / task_bd
            d = start
            while d <= end:
                if is_business_day(d):
                    daily[d][role_id] += daily_fte
                d += datetime.timedelta(days=1)

    if not daily:
        return

    # 月次ピーク
    monthly_peak = defaultdict(lambda: {r: 0.0 for r in roles})
    for d, role_fte in daily.items():
        mk = d.strftime("%Y-%m")
        for r in roles:
            monthly_peak[mk][r] = max(monthly_peak[mk][r], role_fte.get(r, 0.0))

    print("\n## 月次ピークFTE概要\n")
    header = "| 月 | " + " | ".join(roles) + " | 合計 |"
    sep = "|" + "|".join(["---"] * (len(roles) + 2)) + "|"
    print(header)
    print(sep)

    for mk in sorted(monthly_peak.keys()):
        peak = monthly_peak[mk]
        cells = [f"{peak.get(r, 0):.2f}" for r in roles]
        total = sum(peak.get(r, 0) for r in roles)
        print(f"| {mk} | " + " | ".join(cells) + f" | {total:.2f} |")


# ============================================================
# メイン
# ============================================================

def main():
    no_leveling = "--no-leveling" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print("使い方: python derive_wbs_schedule.py <PJフォルダパス> [--no-leveling]")
        print("例: python derive_wbs_schedule.py ./Idemitsu")
        sys.exit(1)

    pj_root = Path(args[0]).resolve()
    config = PjConfig.load(pj_root)
    wbs_path = find_wbs_csv(pj_root, config)

    print(f"=== WBS日程計算: {config.project_id} ({config.project_name}) ===\n")
    print(f"WBS: {wbs_path}")
    print(f"レベリング: {'無効' if no_leveling else '有効'}\n")

    # --- 1. CSV 読み込み ---
    fieldnames, rows = load_csv(wbs_path)
    print(f"読み込み行数: {len(rows)}")

    # --- 2. schedule 設定の適用 ---
    rows = apply_schedule_config(rows, config)
    print(f"設定適用後行数: {len(rows)}")

    # --- 3. 先行タスクマップ構築 ---
    predecessors, successors = build_predecessor_map(rows, config)

    # --- 4. ゲート分類 ---
    gate_tasks, unclassified = classify_tasks_by_gate(rows, config)
    print(f"\nゲート分類:")
    for gate_id, indices in gate_tasks.items():
        print(f"  {gate_id}: {len(indices)} タスク")
    if unclassified:
        print(f"  未分類: {len(unclassified)} タスク")

    # --- 5. ゲートごとにASAPスケジューリング ---
    print("\n--- ASAP スケジューリング ---")
    for gate in config.gates:
        gate_id = gate["id"]
        if gate_id not in gate_tasks:
            continue

        gs = gate.get("start_date")
        if not gs:
            print(f"  ⚠ {gate_id}: start_date 未設定、スキップ")
            continue

        gate_start = (
            datetime.date.fromisoformat(gs) if isinstance(gs, str) else gs
        )
        print(f"  {gate_id}: 開始={gate_start}, {len(gate_tasks[gate_id])}タスク")

        schedule_gate_asap(
            rows, gate_tasks[gate_id], predecessors, gate_start, config
        )

    # --- 6. リソースレベリング ---
    if not no_leveling:
        print("\n--- リソースレベリング ---")
        max_trials = config.schedule_config.get(
            "leveling", {}
        ).get("max_trial_points", 20)

        for gate in config.gates:
            gate_id = gate["id"]
            if gate_id not in gate_tasks:
                continue

            gs = gate.get("start_date")
            gd = gate.get("deadline")
            if not gs or not gd:
                print(f"  ⚠ {gate_id}: start_date/deadline 未設定、スキップ")
                continue

            gate_start = (
                datetime.date.fromisoformat(gs) if isinstance(gs, str) else gs
            )
            gate_deadline = (
                datetime.date.fromisoformat(gd) if isinstance(gd, str) else gd
            )

            print(
                f"  {gate_id}: {gate_start} ~ {gate_deadline}, "
                f"{len(gate_tasks[gate_id])}タスク"
            )

            level_gate(
                rows, gate_tasks[gate_id], predecessors, successors,
                gate_start, gate_deadline, config, max_trials
            )

    # --- 7. CSV 出力 ---
    write_csv(wbs_path, fieldnames, rows)
    print(f"\n✓ WBS CSV 更新完了: {wbs_path}")

    # --- 8. 月次ピークFTEサマリ ---
    print_monthly_peak_summary(rows, config)

    # --- 9. 検証 ---
    cols = config.wbs_columns
    start_col = cols.get("start_date", "開始日")
    end_col = cols.get("end_date", "終了日")

    scheduled = sum(1 for r in rows if r.get(start_col) and r.get(end_col))
    print(f"\n--- 検証 ---")
    print(f"  スケジュール済み: {scheduled}/{len(rows)} タスク")

    # ゲート境界チェック
    violations = 0
    for gate in config.gates:
        gate_id = gate["id"]
        gd = gate.get("deadline")
        if not gd or gate_id not in gate_tasks:
            continue
        deadline = (
            datetime.date.fromisoformat(gd) if isinstance(gd, str) else gd
        )
        for i in gate_tasks[gate_id]:
            end_str = rows[i].get(end_col, "")
            if end_str:
                try:
                    end = datetime.date.fromisoformat(end_str)
                    if end > deadline:
                        violations += 1
                        task_id = rows[i].get(
                            cols.get("task_id", "タスクID"), ""
                        )
                        print(
                            f"  ⚠ {gate_id} 境界違反: {task_id} "
                            f"終了={end} > 期限={deadline}"
                        )
                except ValueError:
                    pass

    if violations:
        print(f"  ✗ {violations} 件のゲート境界違反")
    else:
        print(f"  ✓ ゲート境界: OK")


if __name__ == "__main__":
    main()
