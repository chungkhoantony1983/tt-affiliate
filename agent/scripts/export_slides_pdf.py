#!/usr/bin/env python3
"""
Markdown を Marp テーマ付きスライド PDF へ変換するスクリプト。

固定要件:
- スライドサイズ: 16:9
- フッター: TikTok Affiliate Automation
- スライドごとにタイトル（先頭見出し）を必須化
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPTS_DIR.parent.parent
DEFAULT_THEME_PATH = SCRIPTS_DIR.parent / "slides" / "marp" / "themes" / "project-slide.css"
DEFAULT_THEME_NAME = "project-slide"
DEFAULT_FOOTER = "TikTok Affiliate Automation"

TITLE_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+\S")
FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*(?:\n|$)", re.DOTALL)


def ensure_japanese_fonts() -> None:
    """BIZ UDPGothic フォントが未インストールなら自動インストールする。"""
    try:
        result = subprocess.run(
            ["fc-list", ":lang=ja"],
            capture_output=True, text=True, timeout=10,
        )
        if "BIZ UDPGothic" in result.stdout:
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print("INFO: 日本語フォント (BIZ UDPGothic) をインストールしています...")
    try:
        subprocess.run(
            ["sudo", "apt-get", "install", "-y", "-qq", "fonts-morisawa-bizud-gothic"],
            capture_output=True, text=True, timeout=120,
        )
        subprocess.run(["fc-cache", "-f"], capture_output=True, timeout=30)
        print("INFO: BIZ UDPGothic フォントをインストールしました。")
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        print(
            f"WARNING: フォントの自動インストールに失敗しました: {exc}\n"
            "   手動で実行してください: sudo apt install fonts-morisawa-bizud-gothic",
            file=sys.stderr,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Markdown を Marp スライド PDF に変換します。"
    )
    parser.add_argument("input_md", type=Path, help="入力 Markdown ファイル")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="出力 PDF ファイル（省略時は入力と同名 .pdf）",
    )
    parser.add_argument(
        "--theme",
        type=Path,
        default=DEFAULT_THEME_PATH,
        help=f"Marp テーマ CSS（既定: {DEFAULT_THEME_PATH}）",
    )
    parser.add_argument(
        "--theme-name",
        default=DEFAULT_THEME_NAME,
        help=f"Marp テーマ名（既定: {DEFAULT_THEME_NAME}）",
    )
    parser.add_argument(
        "--footer",
        default=DEFAULT_FOOTER,
        help=f"固定フッター文言（既定: {DEFAULT_FOOTER}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Marp は実行せず、前処理と実行コマンドの生成のみ行う",
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
    return parser.parse_args()


def normalize_newlines(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def split_front_matter(content: str) -> tuple[str, str]:
    match = FRONT_MATTER_PATTERN.match(content)
    if not match:
        return "", content

    full = match.group(0)
    body = match.group("body")
    rest = content[len(full) :]
    return body, rest


def sanitize_front_matter(front_matter_body: str) -> str:
    if not front_matter_body:
        return ""

    blocked_keys = {"theme", "size", "paginate", "footer"}
    kept_lines = []
    for line in front_matter_body.splitlines():
        key_match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*:", line)
        if key_match and key_match.group(1).lower() in blocked_keys:
            continue
        kept_lines.append(line)

    if not any(line.strip() for line in kept_lines):
        return ""

    return "---\n" + "\n".join(kept_lines).rstrip() + "\n---\n\n"


def strip_conflicting_comment_directives(content: str) -> str:
    blocked = {"theme", "size", "paginate", "footer"}
    kept_lines = []
    for line in content.splitlines():
        match = re.match(r"^\s*<!--\s*([A-Za-z0-9_-]+)\s*:", line)
        if match and match.group(1).lower() in blocked:
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines).strip() + "\n"


def find_code_fences(content: str) -> list[tuple[int, str]]:
    """コードフェンス（```）を含むスライドを検出する。

    コードフェンスはMarpスライドPDFでレイアウト崩れの原因になるため、
    SVG画像に事前変換すべき。
    """
    slides = split_slides(content)
    found = []
    for idx, slide in enumerate(slides, start=1):
        for line in slide.splitlines():
            stripped = line.strip()
            if re.match(r"^[`~]{3,}", stripped):
                # コードフェンスの最初の行から内容を推定
                preview = slide.strip().splitlines()
                first_content = next(
                    (l.strip() for l in preview if l.strip() and not l.strip().startswith("#")
                     and not re.match(r"^[`~]{3,}", l.strip())),
                    "(空)",
                )
                found.append((idx, first_content[:60]))
                break
    return found


def find_missing_slide_titles(content: str) -> list[int]:
    slides = split_slides(content)
    missing = []

    for idx, slide in enumerate(slides, start=1):
        if not has_title_heading(slide):
            missing.append(idx)

    return missing


def split_slides(content: str) -> list[str]:
    slides: list[str] = []
    current: list[str] = []

    in_code_fence = False
    fence_char = ""
    fence_len = 0

    for line in content.splitlines():
        stripped = line.strip()
        fence_match = re.match(r"^([`~]{3,})", stripped)

        if fence_match:
            marker = fence_match.group(1)
            if not in_code_fence:
                in_code_fence = True
                fence_char = marker[0]
                fence_len = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                in_code_fence = False
                fence_char = ""
                fence_len = 0

            current.append(line)
            continue

        if not in_code_fence and stripped == "---":
            slides.append("\n".join(current))
            current = []
            continue

        current.append(line)

    slides.append("\n".join(current))
    return slides


def has_title_heading(slide: str) -> bool:
    in_multiline_comment = False

    for line in slide.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if in_multiline_comment:
            if "-->" in stripped:
                in_multiline_comment = False
            continue

        if stripped.startswith("<!--"):
            if not stripped.endswith("-->"):
                in_multiline_comment = True
            continue

        return bool(TITLE_PATTERN.match(stripped))

    return False


def resolve_chrome_path() -> str | None:
    """Puppeteer キャッシュ等から Chrome バイナリを自動検出する。

    優先順位:
    1. CHROME_PATH 環境変数（既に設定済みならそのまま）
    2. ~/.cache/puppeteer/chrome/ 配下の最新バージョン
    3. システムの chromium / google-chrome
    """
    env_path = os.environ.get("CHROME_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    puppeteer_dir = Path.home() / ".cache" / "puppeteer" / "chrome"
    if puppeteer_dir.is_dir():
        candidates = sorted(puppeteer_dir.glob("linux-*/chrome-linux64/chrome"), reverse=True)
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

    for name in ("chromium", "google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found

    return None


def resolve_marp_command() -> list[str]:
    local_marp = ROOT_DIR / "node_modules" / ".bin" / "marp"  # workspace root
    if local_marp.exists():
        return [str(local_marp)]

    global_marp = shutil.which("marp")
    if global_marp:
        return [global_marp]

    if shutil.which("npx"):
        return ["npx", "--yes", "@marp-team/marp-cli@4.2.3"]

    raise RuntimeError(
        "Marp CLI が見つかりません。`npm i -D @marp-team/marp-cli` または `npm install -g @marp-team/marp-cli` を実施してください。"
    )


def build_locked_directives(theme_name: str, footer: str) -> str:
    directives = (
        ("theme", theme_name),
        ("size", "16:9"),
        ("paginate", "true"),
        ("footer", footer),
    )
    return "\n".join(f"<!-- {key}: {value} -->" for key, value in directives)


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
        output_pdf = args.output.resolve()
        if not dry_run:
            output_pdf.parent.mkdir(parents=True, exist_ok=True)
        return output_pdf

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


def main() -> int:
    args = parse_args()

    ensure_japanese_fonts()

    input_md = args.input_md.resolve()
    if not input_md.exists():
        print(f"ERROR: 入力ファイルが見つかりません: {input_md}", file=sys.stderr)
        return 1

    theme_path = args.theme.resolve()
    if not theme_path.exists():
        print(f"ERROR: テーマ CSS が見つかりません: {theme_path}", file=sys.stderr)
        return 1

    try:
        output_pdf = resolve_output_pdf(args, input_md, dry_run=args.dry_run)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    raw = normalize_newlines(input_md.read_text(encoding="utf-8"))
    front_body, body = split_front_matter(raw)

    body = strip_conflicting_comment_directives(body)

    # コードフェンス検出（Marp PDFで崩れるため事前にSVGへ変換すべき）
    code_fences = find_code_fences(body)
    if code_fences:
        print(
            "ERROR: コードフェンス（```）を含むスライドがあります。\n"
            "   Marp PDFではコードブロックのレイアウトが崩れるため、\n"
            "   Mermaid等でSVG画像に変換し、![alt](path.svg) で参照してください。",
            file=sys.stderr,
        )
        for slide_num, preview in code_fences:
            print(f"   スライド {slide_num}: {preview}", file=sys.stderr)
        return 1

    missing_titles = find_missing_slide_titles(body)
    if missing_titles:
        joined = ", ".join(str(n) for n in missing_titles)
        print(
            f"ERROR: タイトル見出しがないスライドがあります: {joined}\n"
            "   各スライドの先頭に `# タイトル` を記載してください。",
            file=sys.stderr,
        )
        return 1

    sanitized_front_matter = sanitize_front_matter(front_body)
    locked_directives = build_locked_directives(args.theme_name, args.footer)

    prepared_markdown = (
        sanitized_front_matter + locked_directives + "\n\n" + body.strip() + "\n"
    )

    marp_cmd = resolve_marp_command()

    # 一時ファイルは入力ファイルと同じディレクトリに作成する。
    # Marp は相対パスをMarkdownファイルの位置から解決するため、
    # /tmp/ に置くと画像等の相対参照が壊れる。
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", encoding="utf-8", delete=False,
        dir=input_md.parent,
    ) as temp:
        temp_path = Path(temp.name)
        temp.write(prepared_markdown)

    try:
        cmd = marp_cmd + [
            str(temp_path),
            "--pdf",
            "--allow-local-files",
            "--theme-set",
            str(theme_path),
            "--theme",
            args.theme_name,
            "-o",
            str(output_pdf),
        ]
        if args.dry_run:
            print("INFO: Dry run mode: Marp は実行しません。")
            print("   " + " ".join(cmd))
            return 0

        run_env = os.environ.copy()
        chrome = resolve_chrome_path()
        if chrome:
            run_env["CHROME_PATH"] = chrome
            run_env["PUPPETEER_EXECUTABLE_PATH"] = chrome

        completed = subprocess.run(cmd, check=True, capture_output=True, text=True, env=run_env)
        if completed.stdout.strip():
            print(completed.stdout.strip())
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        if "No suitable browser found" in stderr:
            print(
                "ERROR: Marp 実行に必要なブラウザが見つかりません。"
                " Chrome / Edge / Firefox のいずれかをインストールしてください。",
                file=sys.stderr,
            )
        elif stderr:
            lines = "\n".join(stderr.splitlines()[:6])
            print(
                f"ERROR: Marp 実行に失敗しました: exit={exc.returncode}\n{lines}",
                file=sys.stderr,
            )
        else:
            print(f"ERROR: Marp 実行に失敗しました: exit={exc.returncode}", file=sys.stderr)
        return exc.returncode
    finally:
        temp_path.unlink(missing_ok=True)

    print(f"OK: PDF 出力完了: {output_pdf}")
    print(f"   Theme : {theme_path}")
    print(f"   Footer: {args.footer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
