#!/usr/bin/env python3
"""
PJ設定JSONに基づいて成果物を一括エクスポートする共通オーケストレーター。

設定ファイル例:
{
  "markdown_files": ["0_Project/HKD-001-PJ定義.md"],
  "slide_source_files": ["9_Decision_Records/DR-0001-example.md"],
  "slide_markdown_files": ["9_Decision_Records/DR-0001-example.md"],
  "csv_files": ["0_Project/HKD-002-WBS.csv"]
}
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPTS_DIR.parent.parent
MARKDOWN_SCRIPT = SCRIPTS_DIR / "export_markdown_to_pdf.py"
PREPARE_SLIDE_SCRIPT = SCRIPTS_DIR / "prepare_slides_markdown.py"
SLIDE_SCRIPT = SCRIPTS_DIR / "export_slides_pdf.py"
CSV_SCRIPT = SCRIPTS_DIR / "export_csv_to_excel.py"
GANTT_SCRIPT = SCRIPTS_DIR / "export_wbs_gantt.py"


@dataclass
class ExportItem:
    kind: str
    path: str
    sheet_name: str | None = None
    mode: str | None = None
    gantt: bool = False
    filter_column: str | None = None
    filter_value: str | None = None
    drop_columns: list[str] | None = None
    deliverable_name: str | None = None
    version: str | None = None
    document_name: str | None = None


# 内部管理番号パターン (IDM-001, HKD-002, SMP-003, 77B-001 等)
_INTERNAL_ID_PATTERN = re.compile(r"^[A-Z0-9]{2,4}-\d{3}")


def validate_deliverable_schema(items: list[ExportItem]) -> list[str]:
    """全アイテムの deliverable_name/version 必須チェック + 内部番号検出。"""
    errors: list[str] = []
    for item in items:
        if not item.deliverable_name:
            errors.append(
                f"ERROR: '{item.path}' に deliverable_name が未設定です。"
                " export-config.json に deliverable_name（ケバブケース）を追加してください。"
            )
        elif _INTERNAL_ID_PATTERN.match(item.deliverable_name):
            errors.append(
                f"ERROR: '{item.path}' の deliverable_name '{item.deliverable_name}' に"
                " 内部管理番号が含まれています。ケバブケースの成果物名を使用してください。"
                " 例: 'pj-definition', 'wbs-summary'"
            )
        if not item.version:
            errors.append(
                f"ERROR: '{item.path}' に version が未設定です。"
                " export-config.json に version（例: 'v1.0'）を追加してください。"
            )
        if item.document_name and _INTERNAL_ID_PATTERN.match(item.document_name):
            errors.append(
                f"ERROR: '{item.path}' の document_name '{item.document_name}' に"
                " 内部管理番号が含まれています。顧客向けの表示名を使用してください。"
            )
    return errors


def build_output_path(
    item: ExportItem, project_root: Path, export_date: str, ext: str, suffix: str = ""
) -> Path:
    """成果物の出力パスを構成する。

    出力先: docs/exports/{deliverable_name}/{document_name}_{version}_{date}{suffix}.{ext}
    """
    deliverable_name = item.deliverable_name or "unknown"
    doc_name = item.document_name or deliverable_name
    version = item.version or "v0.0"
    date_str = export_date.replace("-", "")
    deliverable_dir = project_root / "docs" / "exports" / deliverable_name
    deliverable_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{doc_name}_{version}_{date_str}{suffix}.{ext}"
    return deliverable_dir / filename


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PJ設定JSONを元に成果物を一括エクスポートします。"
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="PJ設定JSON（例: Hokkaido/scripts/export-config.json）",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="PJルート（省略時は config の親ディレクトリ構造から推定）",
    )
    parser.add_argument(
        "--date",
        dest="deliverable_date",
        help="提出日（YYYY-MM-DD, 省略時は当日）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実変換は行わず、実行コマンドのみ確認する",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="途中失敗しても他ファイルの処理を継続する",
    )
    return parser.parse_args()


def load_config(config_path: Path) -> dict:
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON構文エラー: {config_path} ({exc})") from exc


def resolve_project_root(args: argparse.Namespace, config_path: Path) -> Path:
    if args.project_root:
        return args.project_root.resolve()

    # 期待配置: <PJ>/scripts/export-config.json
    if config_path.parent.name == "scripts":
        return config_path.parent.parent.resolve()

    raise ValueError(
        "PJルートを推定できませんでした。`--project-root <path>` を指定してください。"
    )


def resolve_export_date(value: str | None) -> str:
    if value is None:
        return date.today().isoformat()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"--date は YYYY-MM-DD 形式で指定してください: {value}") from exc


def normalize_entries(raw_items: list, kind: str) -> list[ExportItem]:
    items: list[ExportItem] = []
    for entry in raw_items:
        if isinstance(entry, str):
            items.append(ExportItem(kind=kind, path=entry))
            continue

        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            mode = entry.get("mode")
            if mode is not None and mode not in {"fast", "ai"}:
                raise ValueError(
                    f"mode が不正です: {mode!r} "
                    "(slide_source_files では fast / ai を指定してください)"
                )
            drop_cols_raw = entry.get("drop_columns")
            drop_cols = drop_cols_raw if isinstance(drop_cols_raw, list) else None
            items.append(
                ExportItem(
                    kind=kind,
                    path=entry["path"],
                    sheet_name=entry.get("sheet_name"),
                    mode=mode,
                    gantt=bool(entry.get("gantt", False)),
                    filter_column=entry.get("filter_column"),
                    filter_value=entry.get("filter_value"),
                    drop_columns=drop_cols,
                    deliverable_name=entry.get("deliverable_name"),
                    version=entry.get("version"),
                    document_name=entry.get("document_name"),
                )
            )
            continue

        raise ValueError(
            f"設定値が不正です: kind={kind}, entry={entry!r} "
            "(string または {'path': ...} を指定してください)"
        )
    return items


_ISSUE_CSV_KEYWORDS = ("課題", "issues")


def validate_csv_filter_settings(items: list[ExportItem]) -> list[str]:
    """課題管理CSVに公開区分フィルタが設定されているか検証する（export-standard §5-2）。"""
    errors: list[str] = []
    for item in items:
        if item.kind != "csv":
            continue
        path_lower = item.path.lower()
        if not any(kw in path_lower for kw in _ISSUE_CSV_KEYWORDS):
            continue
        if not item.filter_column:
            errors.append(
                f"ERROR: 課題管理CSV '{item.path}' に filter_column が未設定です。"
                " export-standard §5-2 に従い、公開区分フィルタを export-config.json に追加してください。"
            )
        elif not item.drop_columns or item.filter_column not in item.drop_columns:
            errors.append(
                f"WARNING: 課題管理CSV '{item.path}' の drop_columns に"
                f" '{item.filter_column}' が含まれていません。"
                " 成果物に内部管理列が残る可能性があります。"
            )
    return errors


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(cmd, capture_output=True, text=True)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def print_child_output(out: str) -> None:
    if not out:
        return
    print(out)


def parse_prepared_output_path(stdout: str) -> Path | None:
    for line in stdout.splitlines():
        if line.startswith("OUTPUT:"):
            raw = line[len("OUTPUT:") :].strip()
            if raw:
                return Path(raw)
    return None


def build_markdown_command(
    item: ExportItem, project_root: Path, export_date: str, dry_run: bool
) -> list[str]:
    source_path = project_root / item.path
    output_path = build_output_path(item, project_root, export_date, "pdf")
    cmd = [
        sys.executable,
        str(MARKDOWN_SCRIPT),
        str(source_path),
        "-o",
        str(output_path),
    ]
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def build_slide_command_from_source(
    item: ExportItem, project_root: Path, export_date: str, dry_run: bool
) -> tuple[list[str], list[str], Path]:
    source_path = project_root / item.path
    output_pdf = build_output_path(item, project_root, export_date, "pdf")

    prepare_cmd = [
        sys.executable,
        str(PREPARE_SLIDE_SCRIPT),
        str(source_path),
        "--project-root",
        str(project_root),
        "--mode",
        item.mode or "fast",
    ]
    if dry_run:
        prepare_cmd.append("--dry-run")

    slide_export_cmd = [
        sys.executable,
        str(SLIDE_SCRIPT),
        "__PREPARED_SLIDES_PATH__",
        "-o",
        str(output_pdf),
    ]
    if dry_run:
        slide_export_cmd.append("--dry-run")

    return prepare_cmd, slide_export_cmd, output_pdf


def build_slide_command(
    item: ExportItem, project_root: Path, export_date: str, dry_run: bool
) -> list[str]:
    output_path = build_output_path(item, project_root, export_date, "pdf")
    cmd = [
        sys.executable,
        str(SLIDE_SCRIPT),
        str(project_root / item.path),
        "-o",
        str(output_path),
    ]
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def build_gantt_command(
    item: ExportItem, project_root: Path, export_date: str, dry_run: bool
) -> list[str]:
    output_path = build_output_path(item, project_root, export_date, "xlsx", suffix="_gantt")
    cmd = [
        sys.executable,
        str(GANTT_SCRIPT),
        str(project_root / item.path),
        "-o",
        str(output_path),
    ]
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def build_csv_command(
    item: ExportItem, project_root: Path, export_date: str, dry_run: bool
) -> list[str]:
    output_path = build_output_path(item, project_root, export_date, "xlsx")
    cmd = [
        sys.executable,
        str(CSV_SCRIPT),
        str(project_root / item.path),
        "-o",
        str(output_path),
    ]
    if item.sheet_name:
        cmd.extend(["--sheet-name", item.sheet_name])
    if item.filter_column and item.filter_value is not None:
        cmd.extend(["--filter-column", item.filter_column, "--filter-value", item.filter_value])
    if item.drop_columns:
        cmd.extend(["--drop-columns", ",".join(item.drop_columns)])
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def main() -> int:
    args = parse_args()
    config_path = args.config.resolve()
    if not config_path.exists():
        print(f"ERROR: 設定ファイルが見つかりません: {config_path}", file=sys.stderr)
        return 1

    try:
        project_root = resolve_project_root(args, config_path)
        export_date = resolve_export_date(args.deliverable_date)
        config = load_config(config_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        items: list[ExportItem] = []
        items.extend(normalize_entries(config.get("markdown_files", []), "markdown"))
        items.extend(normalize_entries(config.get("slide_source_files", []), "slide_source"))
        items.extend(normalize_entries(config.get("slide_markdown_files", []), "slide"))
        items.extend(normalize_entries(config.get("csv_files", []), "csv"))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not items:
        print("ERROR: 設定ファイルに対象ファイルがありません。", file=sys.stderr)
        return 1

    # deliverable_name / version 必須チェック + 内部番号検出
    schema_errors = validate_deliverable_schema(items)
    for msg in schema_errors:
        print(msg, file=sys.stderr)
    if schema_errors:
        return 1

    # 課題管理CSVの公開区分フィルタ検証（export-standard §5-2）
    csv_filter_errors = validate_csv_filter_settings(items)
    for msg in csv_filter_errors:
        print(msg, file=sys.stderr)
    if any(msg.startswith("ERROR:") for msg in csv_filter_errors):
        return 1

    required_scripts = [MARKDOWN_SCRIPT, PREPARE_SLIDE_SCRIPT, SLIDE_SCRIPT, CSV_SCRIPT]
    if any(item.gantt for item in items):
        required_scripts.append(GANTT_SCRIPT)
    for script_path in required_scripts:
        if not script_path.exists():
            print(f"ERROR: 共通スクリプトが見つかりません: {script_path}", file=sys.stderr)
            return 1

    print("=== Export Start ===")
    print(f"config      : {config_path}")
    print(f"project_root: {project_root}")
    print(f"date        : {export_date}")
    print(f"targets     : {len(items)}")

    failures: list[str] = []
    for index, item in enumerate(items, start=1):
        print(f"\n[{index}/{len(items)}] {item.kind}: {item.path}")
        if item.kind == "markdown":
            cmd = build_markdown_command(item, project_root, export_date, args.dry_run)
            print("  cmd:", " ".join(cmd))
            code, out, err = run_command(cmd)
            print_child_output(out)
            if code != 0:
                if err:
                    print(err, file=sys.stderr)
                failures.append(f"{item.kind}:{item.path}")
                if not args.continue_on_error:
                    break
            continue

        if item.kind == "slide_source":
            prepare_cmd, slide_cmd, output_pdf = build_slide_command_from_source(
                item, project_root, export_date, args.dry_run
            )
            print("  prepare-cmd:", " ".join(prepare_cmd))
            code, out, err = run_command(prepare_cmd)
            print_child_output(out)
            if code != 0:
                if err:
                    print(err, file=sys.stderr)
                failures.append(f"{item.kind}:{item.path}:prepare")
                if not args.continue_on_error:
                    break
                continue

            prepared_path = parse_prepared_output_path(out)
            if prepared_path is None:
                print(
                    "ERROR: スライド前処理の出力パス取得に失敗しました。",
                    file=sys.stderr,
                )
                failures.append(f"{item.kind}:{item.path}:parse-output")
                if not args.continue_on_error:
                    break
                continue

            slide_cmd[2] = str(prepared_path)
            print("  export-cmd :", " ".join(slide_cmd))
            code, out, err = run_command(slide_cmd)
            print_child_output(out)
            if code != 0:
                if err:
                    print(err, file=sys.stderr)
                failures.append(f"{item.kind}:{item.path}:export")
                if not args.continue_on_error:
                    break
                continue

            print(f"  output     : {output_pdf}")
            continue

        if item.kind == "slide":
            cmd = build_slide_command(item, project_root, export_date, args.dry_run)
            print("  cmd:", " ".join(cmd))
            code, out, err = run_command(cmd)
            print_child_output(out)
            if code != 0:
                if err:
                    print(err, file=sys.stderr)
                failures.append(f"{item.kind}:{item.path}")
                if not args.continue_on_error:
                    break
            continue

        if item.kind == "csv":
            cmd = build_csv_command(item, project_root, export_date, args.dry_run)
            print("  cmd:", " ".join(cmd))
            code, out, err = run_command(cmd)
            print_child_output(out)
            if code != 0:
                if err:
                    print(err, file=sys.stderr)
                failures.append(f"{item.kind}:{item.path}")
                if not args.continue_on_error:
                    break

            if item.gantt and (code == 0 or args.continue_on_error):
                gantt_cmd = build_gantt_command(item, project_root, export_date, args.dry_run)
                print(f"  gantt-cmd: {' '.join(gantt_cmd)}")
                g_code, g_out, g_err = run_command(gantt_cmd)
                print_child_output(g_out)
                if g_code != 0:
                    if g_err:
                        print(g_err, file=sys.stderr)
                    failures.append(f"gantt:{item.path}")
                    if not args.continue_on_error:
                        break

            continue

        print(f"ERROR: 未対応の種別です: {item.kind}", file=sys.stderr)
        failures.append(f"{item.kind}:{item.path}")
        if not args.continue_on_error:
            break

    print("\n=== Export Summary ===")
    if failures:
        print("status: FAILED")
        print("failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("status: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
