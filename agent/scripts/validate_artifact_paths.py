#!/usr/bin/env python3
"""validate_artifact_paths.py — 成果物パス構造の検証。

PR diff や指定ディレクトリの成果物ファイルが、SSoT の命名規則・配置ルールに
準拠しているかを検証する CI ゲート。

検証内容:
1. P1: エクスポートファイル（PDF/PPTX/Excel）が export/ 配下にあること
2. P2: スクリーンショット（PNG）が screenshots/ 配下にあること
3. P3: DR ファイルが PR番号サブフォルダ方式に準拠していること
4. P4: slide_*.html の連番に抜けがないこと

Usage:
    python3 validate_artifact_paths.py                    # カレントディレクトリ
    python3 validate_artifact_paths.py --path ./output     # 指定ディレクトリ
    python3 validate_artifact_paths.py --diff              # git diff ベース

Exit codes:
    0  All checks PASS (WARN is acceptable)
    1  One or more checks FAIL
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0


def _pass(check_id: str, msg: str) -> None:
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"[PASS] {check_id}: {msg}")


def _fail(check_id: str, msg: str) -> None:
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"[FAIL] {check_id}: {msg}")


def _warn(check_id: str, msg: str) -> None:
    global WARN_COUNT
    WARN_COUNT += 1
    print(f"[WARN] {check_id}: {msg}")


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

EXPORT_EXTS = {".pdf", ".pptx", ".xlsx", ".xls"}
SCREENSHOT_EXTS = {".png"}
SLIDE_PATTERN = re.compile(r"^slide_(\d+)\.html$")


def _collect_files_from_dir(base: Path) -> list[Path]:
    """ディレクトリから再帰的にファイルを収集する。"""
    if not base.exists():
        return []
    return [p for p in base.rglob("*") if p.is_file()]


def _collect_files_from_diff(base: Path) -> list[Path]:
    """git diff --name-only から変更ファイルを収集する。"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD~1"],
            capture_output=True, text=True, cwd=base,
        )
        if result.returncode != 0:
            # HEAD~1 が存在しない場合は --cached を試行
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True, text=True, cwd=base,
            )
        paths = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                paths.append(base / line)
        return paths
    except FileNotFoundError:
        return []


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_export_placement(files: list[Path], base: Path) -> None:
    """P1: エクスポートファイルが export/ 配下にあること。"""
    misplaced: list[str] = []
    for f in files:
        if f.suffix.lower() in EXPORT_EXTS:
            rel = f.relative_to(base)
            parts = rel.parts
            if "export" not in parts and "exports" not in parts:
                # node_modules, .git 等は除外
                if any(p.startswith(".") for p in parts):
                    continue
                if "node_modules" in parts:
                    continue
                misplaced.append(str(rel))

    if misplaced:
        _fail("P1", f"export/ 外にエクスポートファイル: {misplaced[:5]}"
              + (f" ... +{len(misplaced)-5}" if len(misplaced) > 5 else ""))
    else:
        export_count = sum(
            1 for f in files
            if f.suffix.lower() in EXPORT_EXTS
            and not any(p.startswith(".") for p in f.relative_to(base).parts)
        )
        _pass("P1", f"エクスポートファイル {export_count} 件が正しく配置")


def check_screenshot_placement(files: list[Path], base: Path) -> None:
    """P2: スクリーンショットが screenshots/ 配下にあること。"""
    misplaced: list[str] = []
    for f in files:
        if f.suffix.lower() in SCREENSHOT_EXTS:
            rel = f.relative_to(base)
            parts = rel.parts
            # screenshots/ または assets/ 配下は OK
            if "screenshots" not in parts and "assets" not in parts:
                if any(p.startswith(".") for p in parts):
                    continue
                if "node_modules" in parts:
                    continue
                # favicon 等の小さい PNG は除外
                if f.name in {"favicon.png", "logo.png", "icon.png"}:
                    continue
                misplaced.append(str(rel))

    if misplaced:
        _warn("P2", f"screenshots/ 外に PNG: {misplaced[:5]}"
              + (f" ... +{len(misplaced)-5}" if len(misplaced) > 5 else ""))
    else:
        _pass("P2", "スクリーンショット配置 OK")


def check_dr_path_structure(files: list[Path], base: Path) -> None:
    """P3: DR ファイルが PR番号サブフォルダ方式に準拠していること。"""
    dr_pattern = re.compile(r"DR-\d+", re.IGNORECASE)
    misplaced: list[str] = []

    for f in files:
        if not f.name.lower().startswith("dr-"):
            continue
        if not dr_pattern.match(f.name):
            continue

        rel = f.relative_to(base)
        parts = rel.parts

        # decision-records/ 配下にあるか
        if "decision-records" not in parts:
            misplaced.append(str(rel))
            continue

        # PR番号サブフォルダがあるか（数字ディレクトリ）
        dr_idx = list(parts).index("decision-records")
        if dr_idx + 1 < len(parts) - 1:  # DR ファイル自体を除く
            subfolder = parts[dr_idx + 1]
            if not subfolder.isdigit():
                _warn("P3", f"DR のサブフォルダが PR 番号ではない: {rel} (subfolder={subfolder})")

    if misplaced:
        _fail("P3", f"decision-records/ 外に DR ファイル: {misplaced[:5]}")
    else:
        _pass("P3", "DR パス構造 OK")


def check_slide_numbering(files: list[Path], base: Path) -> None:
    """P4: slide_*.html の連番に抜けがないこと。"""
    # ディレクトリ単位でスライドをグループ化
    slide_dirs: dict[Path, list[int]] = {}
    for f in files:
        m = SLIDE_PATTERN.match(f.name)
        if m:
            slide_dirs.setdefault(f.parent, []).append(int(m.group(1)))

    for dir_path, numbers in slide_dirs.items():
        numbers.sort()
        if not numbers:
            continue
        expected = list(range(1, max(numbers) + 1))
        missing = set(expected) - set(numbers)
        if missing:
            rel = dir_path.relative_to(base) if dir_path != base else Path(".")
            _fail("P4", f"{rel}: slide 連番に抜け: {sorted(missing)} "
                  f"(存在: {numbers[0]}..{numbers[-1]}, 計{len(numbers)}枚)")
        else:
            rel = dir_path.relative_to(base) if dir_path != base else Path(".")
            _pass("P4", f"{rel}: slide {len(numbers)} 枚、連番 OK")

    if not slide_dirs:
        _pass("P4", "スライドファイルなし（チェック対象外）")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate artifact path structure",
    )
    parser.add_argument(
        "--path", type=Path, default=Path("."),
        help="検証対象ディレクトリ (default: .)",
    )
    parser.add_argument(
        "--diff", action="store_true",
        help="git diff から変更ファイルのみ検証",
    )
    args = parser.parse_args()

    base = args.path.resolve()
    print("=== validate_artifact_paths.py ===")
    print(f"  base: {base}")
    print(f"  mode: {'git diff' if args.diff else 'directory scan'}")
    print()

    if args.diff:
        files = _collect_files_from_diff(base)
    else:
        files = _collect_files_from_dir(base)

    if not files:
        print("検証対象ファイルなし")
        return 0

    print(f"検証対象: {len(files)} ファイル")
    print()

    check_export_placement(files, base)
    check_screenshot_placement(files, base)
    check_dr_path_structure(files, base)
    check_slide_numbering(files, base)

    print()
    print(f"=== Result: {PASS_COUNT} PASS, {WARN_COUNT} WARN, {FAIL_COUNT} FAIL ===")

    return 1 if FAIL_COUNT > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
