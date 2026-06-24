#!/usr/bin/env python3
"""
Markdown を PDF に変換する共通スクリプト。

主な機能:
- Mermaid を PNG 描画して埋め込み
- 参照画像の存在チェック
- 日本語フォント前提の共通スタイル適用
- 成果物ディレクトリ (`docs/exports/`) への出力
"""

from __future__ import annotations

import argparse
import base64
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import markdown

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPTS_DIR.parent.parent
DEFAULT_CSS_PATH = SCRIPTS_DIR / "styles" / "document-pdf.css"
MERMAID_CONFIG_PATH = SCRIPTS_DIR / "mermaid-config.json"
MERMAID_PATTERN = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

# Lint patterns (C-0029-3, C-0029-4)
_BOLD_COLON_RE = re.compile(r"\*\*[：:]\s*$")
_LIST_MARKER_RE = re.compile(r"^(\s*)- ")
_NESTED_2SP_BULLET_RE = re.compile(r"^  - ")
_NESTED_2SP_NUM_RE = re.compile(r"^  \d+\. ")
_NESTED_3SP_BULLET_RE = re.compile(r"^   - ")
_TOP_LIST_RE = re.compile(r"^(?:- |\d+\. )")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Markdown を PDF に変換します（Mermaid描画対応）。"
    )
    parser.add_argument("input_md", type=Path, help="入力 Markdown ファイル")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="出力 PDF ファイル（省略時は入力と同名 .pdf）",
    )
    parser.add_argument(
        "--css",
        type=Path,
        default=DEFAULT_CSS_PATH,
        help=f"PDF用CSS（既定: {DEFAULT_CSS_PATH}）",
    )
    parser.add_argument(
        "--to-deliverable",
        action="store_true",
        help="`docs/exports/` へ出力する",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="`--to-deliverable` 時のPJルート（省略時は入力ファイルから推定）",
    )
    parser.add_argument(
        "--date",
        dest="deliverable_date",
        help="`--to-deliverable` 時の日付（YYYY-MM-DD, 省略時は当日）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="変換は実行せず、前処理チェックと出力先確認のみ行う",
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="リスト記法の問題を検出して警告する（C-0029-3/4）。変換前チェックまたは単体実行用",
    )
    return parser.parse_args()


def infer_project_root(input_path: Path) -> Path | None:
    required = {"0_Project", "9_Decision_Records"}
    for parent in [input_path.parent, *input_path.parents]:
        try:
            dir_names = {child.name for child in parent.iterdir() if child.is_dir()}
        except OSError:
            continue

        if required.issubset(dir_names):
            return parent

    return None


def resolve_output_pdf(args: argparse.Namespace, input_md: Path, *, dry_run: bool = False) -> Path:
    if args.output:
        output = args.output.resolve()
        if not dry_run:
            output.parent.mkdir(parents=True, exist_ok=True)
        return output

    if not args.to_deliverable:
        return input_md.with_suffix(".pdf")

    if args.deliverable_date:
        try:
            export_date = date.fromisoformat(args.deliverable_date).isoformat()
        except ValueError as exc:
            raise ValueError(
                f"--date は YYYY-MM-DD 形式で指定してください: {args.deliverable_date}"
            ) from exc
    else:
        export_date = date.today().isoformat()

    project_root = args.project_root.resolve() if args.project_root else infer_project_root(input_md)
    if project_root is None:
        raise ValueError(
            "--to-deliverable 利用時にPJルートを推定できませんでした。"
            " `--project-root <path>` を指定してください。"
        )

    deliverable_dir = project_root / "docs" / "exports"
    if not dry_run:
        deliverable_dir.mkdir(parents=True, exist_ok=True)
    return deliverable_dir / f"{input_md.stem}.pdf"


def normalize_newlines(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def extract_local_image_paths(md_content: str) -> list[str]:
    paths: list[str] = []
    for raw in IMAGE_PATTERN.findall(md_content):
        token = raw.strip().split()[0].strip("<>").strip()
        if not token:
            continue
        if token.startswith(("http://", "https://", "data:", "#")):
            continue
        paths.append(token)
    return paths


def check_image_paths(md_content: str, base_dir: Path) -> list[str]:
    missing: list[str] = []
    for image_path in extract_local_image_paths(md_content):
        path = Path(image_path)
        resolved = path if path.is_absolute() else (base_dir / path).resolve()
        if not resolved.exists():
            missing.append(image_path)
    return missing


def lint_markdown(md_content: str, filepath: str = "<stdin>") -> list[str]:
    """リスト記法の問題を検出する（C-0029-3: 空行欠落, C-0029-4: インデント不足）。"""
    warnings: list[str] = []
    lines = md_content.split("\n")

    for i, line in enumerate(lines):
        # C-0029-3: **bold**: 直後にリストがあるが空行がない
        if _BOLD_COLON_RE.search(line) and i + 1 < len(lines):
            next_line = lines[i + 1]
            if _LIST_MARKER_RE.match(next_line):
                warnings.append(
                    f"{filepath}:{i + 1}: C-0029-3: "
                    f"'**...**: ' の直後にリストがあります。間に空行を挿入してください"
                )

        # C-0029-4: 2〜3スペースのネストリスト
        if _NESTED_2SP_BULLET_RE.match(line) or _NESTED_2SP_NUM_RE.match(line) or _NESTED_3SP_BULLET_RE.match(line):
            # 直前の非空行がトップレベルリストか確認
            for j in range(i - 1, max(i - 10, -1), -1):
                prev = lines[j].rstrip()
                if prev == "":
                    break
                if _TOP_LIST_RE.match(prev):
                    warnings.append(
                        f"{filepath}:{i + 1}: C-0029-4: "
                        f"ネストリストのインデントが4スペース未満です: {line.rstrip()[:60]}"
                    )
                    break
                if prev.startswith("  "):
                    break

    return warnings


def _sanitize_er_attribute_names(mermaid_code: str) -> str:
    """erDiagram の数字始まり属性名に _ プレフィックスを付与（Mermaid パーサー制約回避）。"""
    if "erDiagram" not in mermaid_code:
        return mermaid_code
    return re.sub(
        r"^(\s+\w+\s+)(\d)",
        r"\1_\2",
        mermaid_code,
        flags=re.MULTILINE,
    )


def render_mermaid_to_png(mermaid_code: str, tmp_dir: Path, index: int) -> str:
    mmdc_path = shutil.which("mmdc")
    if not mmdc_path:
        raise RuntimeError(
            "mmdc が見つかりません。`npm install -g @mermaid-js/mermaid-cli` を実行してください。"
        )

    mermaid_code = _sanitize_er_attribute_names(mermaid_code)

    mmd_file = tmp_dir / f"diagram_{index}.mmd"
    png_file = tmp_dir / f"diagram_{index}.png"
    mmd_file.write_text(mermaid_code, encoding="utf-8")

    cmd = [
        mmdc_path,
        "-i",
        str(mmd_file),
        "-o",
        str(png_file),
        "-e",
        "png",
        "-b",
        "white",
        "-s",
        "2",
        "-q",
    ]
    if MERMAID_CONFIG_PATH.exists():
        cmd.extend(["-c", str(MERMAID_CONFIG_PATH)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0 or not png_file.exists():
        details = (result.stderr or "").strip()
        if details:
            details = "\n".join(details.splitlines()[:6])
        raise RuntimeError(f"Mermaid描画に失敗しました: {details or 'unknown error'}")

    png_data = png_file.read_bytes()
    return base64.b64encode(png_data).decode("ascii")


def replace_mermaid_blocks(md_content: str, tmp_dir: Path) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match) -> str:
        nonlocal count
        count += 1
        code = match.group(1).strip()
        png_b64 = render_mermaid_to_png(code, tmp_dir, count)
        return (
            "\n<div class=\"mermaid-diagram\">\n"
            f"<img src=\"data:image/png;base64,{png_b64}\" alt=\"mermaid-{count}\">\n"
            "</div>\n"
        )

    replaced = MERMAID_PATTERN.sub(repl, md_content)
    return replaced, count


def convert_markdown_to_html(md_content: str, title: str, css_text: str) -> str:
    body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "toc", "nl2br", "sane_lists"],
    )
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>{css_text}</style>
</head>
<body>
{body}
</body>
</html>"""


def main() -> int:
    args = parse_args()

    input_md = args.input_md.resolve()
    if not input_md.exists():
        print(f"ERROR: 入力ファイルが見つかりません: {input_md}", file=sys.stderr)
        return 1

    css_path = args.css.resolve()
    if not css_path.exists():
        print(f"ERROR: CSSファイルが見つかりません: {css_path}", file=sys.stderr)
        return 1

    try:
        output_pdf = resolve_output_pdf(args, input_md, dry_run=args.dry_run)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    md_content = normalize_newlines(input_md.read_text(encoding="utf-8"))

    # Lint check (--lint: 単体実行 / 通常変換時も警告出力)
    lint_warnings = lint_markdown(md_content, str(args.input_md))
    if lint_warnings:
        for w in lint_warnings:
            print(f"WARN: {w}", file=sys.stderr)
        print(f"WARN: {len(lint_warnings)} 件のリスト記法の問題を検出しました", file=sys.stderr)
    if args.lint:
        return 1 if lint_warnings else 0

    missing_images = check_image_paths(md_content, input_md.parent)
    if missing_images:
        sample = ", ".join(missing_images[:5])
        print(
            "ERROR: 参照画像が見つかりません。"
            f" missing={sample}",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        mermaid_count = len(MERMAID_PATTERN.findall(md_content))
        print("INFO: Dry run mode: 変換は実行しません。")
        print(f"   input  : {input_md}")
        print(f"   output : {output_pdf}")
        print(f"   css    : {css_path}")
        print(f"   mermaid: {mermaid_count}")
        return 0

    try:
        with tempfile.TemporaryDirectory() as tmp:
            md_content, _ = replace_mermaid_blocks(md_content, Path(tmp))
            css_text = css_path.read_text(encoding="utf-8")
            html = convert_markdown_to_html(md_content, input_md.stem, css_text)
            from weasyprint import HTML  # lazy import: --lint では不要
            HTML(string=html, base_url=str(input_md.parent)).write_pdf(str(output_pdf))
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: PDF変換に失敗しました: {exc}", file=sys.stderr)
        return 1

    print(f"OK: PDF 出力完了: {output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
