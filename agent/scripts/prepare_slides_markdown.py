#!/usr/bin/env python3
"""
通常Markdownをスライド向けMarkdown（Marp形式）へ前処理するスクリプト。

設計方針:
- エクスポート都度の重処理を避けるため、ハッシュキャッシュを利用
- 生成物は `docs/exports/.cache/slides/` 配下へ保存（Git管理外）
- mode=fast はルールベース変換
- mode=ai は将来拡張用。現時点では fast へフォールバック
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SCRIPT_VERSION = "1.8"
DEFAULT_THEME = "project-slide"
DEFAULT_FOOTER = "TikTok Affiliate Automation"
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


# スライド変換時に除外するセクション（H1/H2 タイトルの前方一致で判定）
EXCLUDED_SECTION_TITLES = [
    "更新履歴",
    "改訂履歴",
]
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CODE_FENCE_PATTERN = re.compile(r"^([`~]{3,})")
MERMAID_PATTERN = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)

# === Mermaid 描画設定（project-slide パレット準拠・日本語フォント） ===
MERMAID_CONFIG: dict = {
    "theme": "base",
    "themeVariables": {
        "primaryColor": "#E0F2F4",
        "primaryTextColor": "#002020",
        "primaryBorderColor": "#008587",
        "lineColor": "#006970",
        "secondaryColor": "#B1DFE2",
        "tertiaryColor": "#F7FAF9",
        "fontFamily": "BIZ UDPGothic, Noto Sans CJK JP, Noto Sans JP, sans-serif",
        "fontSize": "14px",
    },
}

# 内部参照検出パターン（Stage 1 で警告を出力し、Stage 2 で AI が除去する）
INTERNAL_REF_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b[\w-]+\.md\b"), ".md 拡張子"),
    (re.compile(r"\b[\w-]+\.csv\b"), ".csv 拡張子"),
    (re.compile(r"\b[\w-]+\.xlsx?\b"), ".xls/xlsx 拡張子"),
    (re.compile(r"\b\d_\w+/"), "内部ディレクトリパス (N_xxx/)"),
    (re.compile(r"\[([^\]]+)\]\([^)]*\.md\)"), "MD ファイルへのリンク"),
]


def estimate_mermaid_complexity(mermaid_code: str) -> tuple[int, str]:
    """Mermaid コードの複雑度からレンダリング幅と Marp 幅ヒントを推定する。

    Returns:
        (mmdc_width_px, marp_width_hint)
    """
    lines = [
        ln for ln in mermaid_code.splitlines()
        if ln.strip() and not ln.strip().startswith("%%")
    ]
    line_count = len(lines)

    first_line = lines[0].strip().lower() if lines else ""
    is_er = first_line.startswith("erdiagram")
    is_sequence = first_line.startswith("sequencediagram")

    if is_er and line_count > 80:
        return 1200, "w:1100"
    if is_sequence and line_count > 30:
        return 1200, "w:1100"

    if line_count >= 40:
        return 1200, "w:1100"
    if line_count >= 15:
        return 1100, "w:1000"
    return 1000, "w:950"


def write_mermaid_config(figures_dir: Path) -> Path:
    """mmdc 用の一時設定 JSON を figures/ に書き出し、パスを返す。"""
    config_path = figures_dir / "_mermaid_config.json"
    config_path.write_text(
        json.dumps(MERMAID_CONFIG, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config_path


# テキスト図（ASCII アート等）検出用パターン
_DIAGRAM_INDICATORS = re.compile(
    r"[→←↑↓┌┐└┘├┤┬┴┼│─]"   # Box-drawing / 矢印 Unicode
    r"|-->"                       # Mermaid / ASCII 矢印
    r"|<--"
    r"|\+---\+"                   # ASCII ボックス
    r"|\|.*\|.*\|"               # パイプ区切りのレイアウト
    r"|[■█▓▒]"                   # バーチャート記号
    r"|\d+\s*\|"                 # Y軸パターン (数字 + パイプ)
)
_CODE_BLOCK_PATTERN = re.compile(
    r"```(?:text|plaintext|)\s*\n(.*?)```", re.DOTALL
)


def detect_text_diagrams(content: str) -> list[tuple[int, int, str]]:
    """テキスト図（ASCII art / ボックス描画）を含むコードブロックを検出する。

    Returns:
        list of (start_line, line_count, summary) — Stage 2 への警告用
    """
    findings: list[tuple[int, int, str]] = []
    for match in _CODE_BLOCK_PATTERN.finditer(content):
        block = match.group(1)
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 3:
            continue
        indicator_count = sum(1 for ln in lines if _DIAGRAM_INDICATORS.search(ln))
        # ブロック内の30%以上がダイアグラム的な文字を含む場合に検出
        if indicator_count / len(lines) >= 0.3:
            start_line = content[: match.start()].count("\n") + 1
            max_width = max((len(ln) for ln in lines), default=0)
            summary = f"{len(lines)}行, 幅{max_width}文字"
            if max_width > 70:
                summary += " (⚠ 70文字超: スライド右端切れの可能性)"
            findings.append((start_line, len(lines), summary))
    return findings


# ── Text diagram → Mermaid auto-conversion ──

_BAR_CHAR_RE = re.compile(r'[■█▓▒]')
_AXIS_SEP_RE = re.compile(r'^\s*\+[-+]+[→>]?\s*$')
_Y_AXIS_RE = re.compile(r'^\s*(\d+)\s*\|(.*)')
_TWO_GROUP_RE = re.compile(r'\[([^\]]+)\].*\[([^\]]+)\]')


def _char_display_width(ch: str) -> int:
    """CJK 表示幅（全角=2, 半角=1）を返す。"""
    eaw = unicodedata.east_asian_width(ch)
    return 2 if eaw in ('F', 'W', 'A') else 1


def _display_col_positions(line: str, target_chars: str) -> list[int]:
    """行内の指定文字の表示列位置リストを返す。"""
    positions: list[int] = []
    col = 0
    for ch in line:
        if ch in target_chars:
            positions.append(col)
        col += _char_display_width(ch)
    return positions


def _segment_has_char(line: str, disp_start: int, disp_end: int, pattern: re.Pattern) -> bool:
    """表示列範囲 [start, end) 内に pattern にマッチする文字が存在するか判定する。"""
    col = 0
    for ch in line:
        w = _char_display_width(ch)
        if col >= disp_end:
            break
        if col + w > disp_start and pattern.search(ch):
            return True
        col += w
    return False


def _extract_bar_values_from_table(context_before: str, num_labels: int) -> list[int] | None:
    """コードブロック直前のテーブルから太字数値（合計行等）を抽出する。"""
    for line in reversed(context_before.rstrip().splitlines()[-30:]):
        if not line.strip().startswith('|'):
            continue
        bold_nums = re.findall(r'\*\*(\d+)\*\*', line)
        if len(bold_nums) >= num_labels:
            return [int(n) for n in bold_nums[:num_labels]]
    return None


def _convert_bar_chart_to_mermaid(text: str, context_before: str = "") -> str | None:
    """ASCII bar chart (■ blocks with axis) → Mermaid xychart-beta."""
    lines = text.strip().splitlines()

    # Find axis separator line (+--+---+...→)
    sep_idx = None
    for i, line in enumerate(lines):
        if _AXIS_SEP_RE.match(line):
            sep_idx = i
            break
    if sep_idx is None or sep_idx + 1 >= len(lines):
        return None

    sep_line = lines[sep_idx]
    plus_pos = _display_col_positions(sep_line, '+')
    if len(plus_pos) < 3:
        return None

    # Parse y-axis values (existence check)
    has_y_axis = any(_Y_AXIS_RE.match(lines[i]) for i in range(sep_idx))
    if not has_y_axis:
        return None

    # Parse x-axis labels
    x_labels = re.findall(r'\S+', lines[sep_idx + 1])
    if not x_labels:
        return None

    # 値の取得: テーブルの合計行 → ASCII art からの推定の優先順
    values = _extract_bar_values_from_table(context_before, len(x_labels))

    if values is None:
        # フォールバック: ASCII art から表示幅ベースで推定
        arrow_cols = _display_col_positions(sep_line, '→>')
        if arrow_cols and arrow_cols[-1] > plus_pos[-1]:
            plus_pos.append(arrow_cols[-1] + 2)

        y_data: list[tuple[int, str]] = []
        for i in range(sep_idx):
            m = _Y_AXIS_RE.match(lines[i])
            if m:
                y_data.append((int(m.group(1)), lines[i]))
        y_data.sort(key=lambda x: x[0], reverse=True)

        num_cols = len(plus_pos) - 1
        values = []
        for col_idx in range(num_cols):
            left, right = plus_pos[col_idx], plus_pos[col_idx + 1]
            max_y = 0
            for y_val, full_line in y_data:
                if _segment_has_char(full_line, left, right, _BAR_CHAR_RE):
                    max_y = y_val
                    break
            values.append(max_y)

    # Align columns to labels
    count = min(len(x_labels), len(values))
    x_labels, values = x_labels[:count], values[:count]
    if not values:
        return None

    # Extract title (first non-axis line)
    title = ""
    for i in range(sep_idx):
        s = lines[i].strip()
        if s and not _Y_AXIS_RE.match(lines[i]):
            title = s
            break

    labels_str = ", ".join(f'"{lbl}"' for lbl in x_labels)
    values_str = ", ".join(str(v) for v in values)
    max_val = max(values) + 2

    result = "xychart-beta\n"
    if title:
        result += f'    title "{title}"\n'
    result += f"    x-axis [{labels_str}]\n"
    result += f'    y-axis "{title or "値"}" 0 --> {max_val}\n'
    result += f"    bar [{values_str}]"
    return result


def _convert_org_chart_to_mermaid(text: str) -> str | None:
    """Two-column org/tree chart → Mermaid graph LR with subgraphs.

    Produces side-by-side layout with direction TB inside each subgraph
    and edges placed inside subgraph blocks for proper layout.
    """
    lines = text.strip().splitlines()

    # Detect two-group header: [Group1] ... [Group2]
    header_match = None
    header_idx = None
    for i, line in enumerate(lines):
        m = _TWO_GROUP_RE.search(line)
        if m:
            header_match = m
            header_idx = i
            break
    if not header_match:
        return None

    g1_name = header_match.group(1)
    g2_name = header_match.group(2)
    split_col = lines[header_idx].index(f'[{g2_name}]')

    g1_roles: list[str] = []
    g2_roles: list[str] = []
    g2_hierarchy: dict[str, str] = {}  # child → parent
    cross_links: list[tuple[str, str]] = []
    # Track the vertical-bar root (─┐ starts, ─┤/─┘ connects)
    vbar_root: str | None = None
    vbar_children: list[str] = []
    last_g2_parent: str | None = None

    for line in lines[header_idx + 1:]:
        if not line.strip():
            continue

        left = line[:split_col] if split_col <= len(line) else line
        right = line[split_col:] if split_col < len(line) else ""

        # Clean left side (remove connectors at edges)
        left_clean = re.sub(r'[─►◄┐┤┘│├└\s]+$', '', left).strip()
        left_clean = re.sub(r'^[│\s]+', '', left_clean).strip()

        # Clean right side (remove trailing vertical connectors)
        right_clean = right.strip()
        right_clean = re.sub(r'[─┐┤┘│\s]+$', '', right_clean).strip()

        # Detect vertical-bar connectors: ─┐ (start), ─┤ (middle), ─┘ (end)
        has_start = '┐' in right
        has_mid = '┤' in right
        has_end = '┘' in right

        # Detect child node (├─ or └─)
        is_child = bool(re.match(r'[├└]─', right_clean))
        if is_child:
            name = re.sub(r'^[├└]─\s*', '', right_clean).strip()
            if name:
                g2_roles.append(name)
                if last_g2_parent:
                    g2_hierarchy[name] = last_g2_parent
        elif right_clean:
            g2_roles.append(right_clean)
            last_g2_parent = right_clean
            # Vertical bar: ─┐ marks root, ─┤/─┘ marks direct report
            if has_start:
                vbar_root = right_clean
            elif (has_mid or has_end) and vbar_root and right_clean != vbar_root:
                vbar_children.append(right_clean)

        if left_clean:
            g1_roles.append(left_clean)

        # Cross-group bidirectional link
        if '◄' in line and '►' in line and left_clean:
            # Extract the right-side role name for cross-link
            cr = re.sub(r'[─┐┤┘│\s]+$', '', right.strip()).strip()
            if cr:
                cross_links.append((left_clean, cr))

    if not g1_roles and not g2_roles:
        return None

    # Merge vertical-bar hierarchy into g2_hierarchy
    for child in vbar_children:
        if child not in g2_hierarchy and vbar_root:
            g2_hierarchy[child] = vbar_root

    # Build the full parent→children map for g2
    children_of: dict[str, list[str]] = {}
    for child, parent in g2_hierarchy.items():
        children_of.setdefault(parent, []).append(child)
    # Find root nodes (not a child of anyone)
    g2_roots = [r for r in g2_roles if r not in g2_hierarchy]

    # Generate node IDs
    node_ids: dict[str, str] = {}
    _counter = [0]

    def nid(key: str) -> str:
        if key not in node_ids:
            _counter[0] += 1
            node_ids[key] = f"N{_counter[0]}"
        return node_ids[key]

    out = ["graph LR"]

    # Left subgraph — no internal edges (direction TB not reliable in mmdc)
    out.append(f'    subgraph SG1["{g1_name}"]')
    for role in g1_roles:
        out.append(f'        {nid("L_" + role)}["{role}"]')
    out.append("    end")

    # Right subgraph — hierarchy with edges inside
    out.append(f'    subgraph SG2["{g2_name}"]')
    for role in g2_roles:
        out.append(f'        {nid("R_" + role)}["{role}"]')
    # Hierarchy edges inside subgraph
    # Emit direct-report edges first (non-hierarchy roots → first root),
    # then hierarchy edges — this influences dagre's vertical ordering
    first_root = g2_roots[0] if g2_roots else None
    # 1) Direct reports: other roots connect to first root
    for root in g2_roots[1:]:
        if root not in g2_hierarchy:
            out.append(f"        {nid('R_' + first_root)} --> {nid('R_' + root)}")
    # 2) Hierarchy children of roots
    for root in g2_roots:
        if root in children_of:
            for child in children_of[root]:
                out.append(f"        {nid('R_' + root)} --> {nid('R_' + child)}")
    # 3) Non-root parents → their children
    for parent, kids in children_of.items():
        if parent in g2_roots:
            continue
        for child in kids:
            out.append(f"        {nid('R_' + parent)} --> {nid('R_' + child)}")
    out.append("    end")

    # Cross links (between subgraphs — dotted for visual distinction)
    cross_connected_left: set[str] = set()
    for left_role, right_role in cross_links:
        out.append(f"    {nid('L_' + left_role)} <-.-> {nid('R_' + right_role)}")
        cross_connected_left.add(left_role)

    # Alignment edges: connect first and last unconnected g1 roles to
    # g2 first/last roles — forces side-by-side layout without over-constraining
    if g1_roles and g2_roles:
        if g1_roles[0] not in cross_connected_left:
            out.append(f"    {nid('L_' + g1_roles[0])} ~~~ {nid('R_' + g2_roles[0])}")
        if len(g1_roles) > 1 and g1_roles[-1] not in cross_connected_left:
            out.append(f"    {nid('L_' + g1_roles[-1])} ~~~ {nid('R_' + g2_roles[-1])}")

    return "\n".join(out)


def convert_text_diagrams_to_mermaid(content: str) -> tuple[str, int]:
    """Detect text/plaintext code blocks with diagrams and convert to Mermaid."""
    count = 0

    def _repl(match: re.Match) -> str:
        nonlocal count
        block = match.group(1)
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 3:
            return match.group(0)

        # Check diagram indicator density
        hits = sum(1 for ln in lines if _DIAGRAM_INDICATORS.search(ln))
        if hits / len(lines) < 0.3:
            return match.group(0)

        # Try bar chart first (pass context before the code block)
        context_before = content[:match.start()]
        result = _convert_bar_chart_to_mermaid(block, context_before)
        if result:
            count += 1
            return f"```mermaid\n{result}\n```"

        # Try org chart
        result = _convert_org_chart_to_mermaid(block)
        if result:
            count += 1
            return f"```mermaid\n{result}\n```"

        return match.group(0)

    replaced = _CODE_BLOCK_PATTERN.sub(_repl, content)
    return replaced, count


def detect_mermaid_flow_direction(content: str) -> list[tuple[int, str, str]]:
    """Mermaid ブロックのフロー方向を検出し、縦長フローチャートに警告を出す。

    Returns:
        list of (start_line, direction, suggestion)
    """
    findings: list[tuple[int, str, str]] = []
    for match in MERMAID_PATTERN.finditer(content):
        code = match.group(1).strip()
        first_line = code.splitlines()[0].strip().lower() if code else ""
        start_line = content[: match.start()].count("\n") + 1
        lines = [ln for ln in code.splitlines()
                 if ln.strip() and not ln.strip().startswith("%%")]
        line_count = len(lines)

        # graph TD / flowchart TD は縦方向（Top-Down）で縦長になりやすい
        is_vertical = any(first_line.startswith(p) for p in [
            "graph td", "graph tb", "flowchart td", "flowchart tb",
        ])
        if is_vertical and line_count >= 10:
            findings.append((
                start_line,
                "TD (縦方向)",
                f"{line_count}行 → Stage 2 で LR (横方向) への変換またはサブグラフ分割を検討",
            ))
    return findings


def detect_internal_references(content: str) -> list[tuple[int, str, str]]:
    """内部参照パターンを検出し、(行番号, マッチ文字列, パターン名) のリストを返す。"""
    findings: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for pattern, label in INTERNAL_REF_PATTERNS:
            for match in pattern.finditer(line):
                findings.append((line_no, match.group(0), label))
    return findings


@dataclass
class Section:
    title: str
    lines: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Markdown をスライド向け Marp 形式へ前処理します。"
    )
    parser.add_argument("input_md", type=Path, help="入力 Markdown ファイル")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="PJルート（省略時は入力パスから推定）",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="生成キャッシュディレクトリ（省略時: docs/exports/.cache/slides）",
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "ai"],
        default="fast",
        help="変換モード（既定: fast）",
    )
    parser.add_argument(
        "--theme",
        default=DEFAULT_THEME,
        help=f"生成するMarpテーマ（既定: {DEFAULT_THEME}）",
    )
    parser.add_argument(
        "--footer",
        default=DEFAULT_FOOTER,
        help=f"生成するフッター（既定: {DEFAULT_FOOTER}）",
    )
    parser.add_argument("--force", action="store_true", help="キャッシュを無視して再生成")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="変換は実行せず、キャッシュ判定と出力先確認のみ表示",
    )
    return parser.parse_args()


def normalize_newlines(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


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


def resolve_project_root(args: argparse.Namespace, input_md: Path) -> Path:
    if args.project_root:
        return args.project_root.resolve()

    inferred = infer_project_root(input_md)
    if inferred:
        return inferred

    raise ValueError(
        "PJルートを推定できませんでした。`--project-root <path>` を指定してください。"
    )


def resolve_cache_dir(args: argparse.Namespace, project_root: Path) -> Path:
    if args.cache_dir:
        return args.cache_dir.resolve()
    return project_root / "docs" / "exports" / ".cache" / "slides"


def render_mermaid_to_svg(
    mermaid_code: str, figures_dir: Path, index: int, config_path: Path,
) -> tuple[str, str]:
    """Mermaid コードを SVG に描画し、(figures相対パス, marp_width_hint) を返す。"""
    mmdc_path = shutil.which("mmdc")
    if not mmdc_path:
        raise RuntimeError(
            "mmdc が見つかりません。`npm install -g @mermaid-js/mermaid-cli` を実行してください。"
        )

    figures_dir.mkdir(parents=True, exist_ok=True)
    mmd_file = figures_dir / f"_mermaid_{index}.mmd"
    svg_file = figures_dir / f"mermaid_{index}.svg"
    mmd_file.write_text(mermaid_code, encoding="utf-8")

    mmdc_width, marp_hint = estimate_mermaid_complexity(mermaid_code)

    try:
        result = subprocess.run(
            [
                mmdc_path,
                "-i", str(mmd_file),
                "-o", str(svg_file),
                "-e", "svg",
                "-b", "transparent",
                "-w", str(mmdc_width),
                "-c", str(config_path),
                "-q",
            ],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0 or not svg_file.exists():
            details = (result.stderr or "").strip()
            if details:
                details = "\n".join(details.splitlines()[:6])
            raise RuntimeError(
                f"Mermaid描画に失敗しました (diagram {index}): {details or 'unknown error'}"
            )
    finally:
        mmd_file.unlink(missing_ok=True)

    return f"figures/mermaid_{index}.svg", marp_hint


_MERMAID_TD_RE = re.compile(r'\b(TD|TB)\b')


def _auto_convert_td_to_lr(mermaid_code: str) -> tuple[str, bool]:
    """10行以上の縦長 TD/TB フローチャートを LR (横方向) に自動変換する。"""
    lines = [ln for ln in mermaid_code.splitlines()
             if ln.strip() and not ln.strip().startswith("%%")]
    if len(lines) < 10:
        return mermaid_code, False

    first = lines[0].strip().lower()
    if not any(first.startswith(p) for p in [
        "graph td", "graph tb", "flowchart td", "flowchart tb",
    ]):
        return mermaid_code, False

    all_lines = mermaid_code.splitlines()
    for i, line in enumerate(all_lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("%%"):
            all_lines[i] = _MERMAID_TD_RE.sub("LR", line, count=1)
            break

    return "\n".join(all_lines), True


def replace_mermaid_blocks(content: str, output_dir: Path) -> tuple[str, int, int]:
    """Mermaid コードブロックを描画済み SVG 画像参照に置換する。

    Returns:
        (replaced_content, total_count, lr_converted_count)
    """
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    config_path = write_mermaid_config(figures_dir)
    count = 0
    lr_count = 0

    def repl(match: re.Match) -> str:
        nonlocal count, lr_count
        count += 1
        code = match.group(1).strip()
        code, converted = _auto_convert_td_to_lr(code)
        if converted:
            lr_count += 1
        rel_path, marp_hint = render_mermaid_to_svg(
            code, figures_dir, count, config_path,
        )
        return f"\n![mermaid-{count} {marp_hint} center]({rel_path})\n"

    replaced = MERMAID_PATTERN.sub(repl, content)
    config_path.unlink(missing_ok=True)
    return replaced, count, lr_count


def strip_front_matter(content: str) -> str:
    match = FRONT_MATTER_PATTERN.match(content)
    if not match:
        return content
    return content[match.end() :]


def extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        match = HEADING_PATTERN.match(line.strip())
        if match:
            return match.group(2).strip()
    return fallback


HR_PATTERN = re.compile(r"^\s{0,3}(?:[-*_]\s*){3,}$")


def is_horizontal_rule(line: str) -> bool:
    """Markdown の水平線（---/***/___ 等）を判定する。

    Marp ではこれらがスライド区切りと衝突するため、
    スライド変換時に除外する必要がある。
    """
    return bool(HR_PATTERN.match(line))


def split_sections(content: str, default_title: str) -> list[Section]:
    sections: list[Section] = []
    current_title = default_title
    current_lines: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        heading = HEADING_PATTERN.match(line.strip())
        if heading and len(heading.group(1)) <= 2:
            if current_lines:
                sections.append(Section(title=current_title, lines=current_lines))
            current_title = heading.group(2).strip()
            current_lines = []
            continue
        # 水平線はMarpスライド区切りと衝突するため除外
        if is_horizontal_rule(line):
            continue
        current_lines.append(line)

    if current_lines:
        sections.append(Section(title=current_title, lines=current_lines))

    if not sections:
        sections.append(Section(title=default_title, lines=[]))

    return sections


def split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    in_code_fence = False
    fence_char = ""
    fence_len = 0

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append(current)
            current = []

    for line in lines:
        stripped = line.strip()
        fence = CODE_FENCE_PATTERN.match(stripped)
        if fence:
            marker = fence.group(1)
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

        if not in_code_fence and stripped == "":
            flush()
            continue

        current.append(line)

    flush()
    return blocks


_MERMAID_IMAGE_PATTERN = re.compile(r"!\[mermaid-\d+")
_SUB_HEADING_PATTERN = re.compile(r"^#{3,6}\s+")


def block_weight(block: list[str]) -> int:
    lines = [ln for ln in block if ln.strip()]
    if not lines:
        return 1

    # Mermaid SVG 画像はスライド内で大きなスペースを占めるため高い重みを与える。
    has_mermaid = any(_MERMAID_IMAGE_PATTERN.search(ln) for ln in lines)
    if has_mermaid:
        # 見出し等の追加コンテンツがある場合はスライド全体を使う (weight=4)
        # 画像単体なら weight=3 で見出しブロック (weight=1) と結合可能
        non_mermaid = [ln for ln in lines if not _MERMAID_IMAGE_PATTERN.search(ln)]
        return 4 if non_mermaid else 3

    is_table = all(("|" in ln) for ln in lines[: min(3, len(lines))]) and any(
        ln.strip().startswith("|") for ln in lines
    )
    if is_table:
        return max(2, (len(lines) + 4) // 5)

    is_list = all(ln.strip().startswith(("-", "*", "+", "1.", "2.", "3.")) for ln in lines[: min(4, len(lines))])
    if is_list:
        return max(1, (len(lines) + 5) // 6)

    return max(1, (len(lines) + 6) // 7)


def _merge_heading_groups(blocks: list[list[str]]) -> list[list[str]]:
    """h3-h6 見出しブロックを直後のコンテンツブロックと結合する。

    スライド内でサブセクション見出しが本文・図と分離して
    孤立するのを防ぐ（タイトル＋説明＋画像は必ずセットで1ページ）。
    """
    groups: list[list[str]] = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        first_line = next((ln for ln in block if ln.strip()), "")
        is_sub_heading = bool(_SUB_HEADING_PATTERN.match(first_line.strip()))

        if is_sub_heading and i + 1 < len(blocks):
            merged = block + [""] + blocks[i + 1]
            groups.append(merged)
            i += 2
        else:
            groups.append(block)
            i += 1
    return groups


def chunk_section(section: Section, max_weight: int = 4) -> list[list[str]]:
    blocks = split_blocks(section.lines)
    blocks = _merge_heading_groups(blocks)
    if not blocks:
        return [[]]

    chunks: list[list[str]] = []
    current: list[str] = []
    weight = 0

    for block in blocks:
        w = block_weight(block)
        if current and weight + w > max_weight:
            chunks.append(current)
            current = []
            weight = 0

        current.extend(block)
        current.append("")
        weight += w

    if current:
        if current and current[-1] == "":
            current.pop()
        chunks.append(current)

    return chunks


def _is_table_block(block: list[str]) -> bool:
    """ブロックがテーブル（| で始まる行のみ）かどうかを判定する。"""
    non_empty = [ln for ln in block if ln.strip()]
    if not non_empty:
        return False
    return all("|" in ln for ln in non_empty) and any(
        ln.strip().startswith("|") for ln in non_empty
    )


def _strip_tables_from_section(section: Section) -> Section:
    """セクションからテーブルブロックを除去した新しい Section を返す。"""
    blocks = split_blocks(section.lines)
    filtered = [b for b in blocks if not _is_table_block(b)]
    lines: list[str] = []
    for b in filtered:
        lines.extend(b)
        lines.append("")
    return Section(title=section.title, lines=lines)


def _should_exclude_section(title: str) -> bool:
    """除外対象セクション（更新履歴等）かどうかを判定する。"""
    for excluded in EXCLUDED_SECTION_TITLES:
        if title.startswith(excluded):
            return True
    return False


def build_slide_markdown(source_path: Path, content: str, theme: str, footer: str) -> str:
    clean = normalize_newlines(strip_front_matter(content))
    doc_title = extract_title(clean, source_path.stem)
    sections = split_sections(clean, doc_title)

    # 更新履歴・改訂履歴セクションを除外する（顧客向け成果物には不要）
    sections = [s for s in sections if not _should_exclude_section(s.title)]

    # 表紙（最初のセクション）からテーブルを除去する
    if sections:
        sections[0] = _strip_tables_from_section(sections[0])

    slides: list[str] = []
    for section in sections:
        chunks = chunk_section(section)
        for idx, chunk in enumerate(chunks, start=1):
            title = section.title if idx == 1 else f"{section.title}（続き{idx}）"
            body = "\n".join(chunk).strip()
            if not body:
                body = "- "
            slide = f"# {title}\n\n{body}\n"
            slides.append(slide)

    header = (
        "---\n"
        "marp: true\n"
        f"theme: {theme}\n"
        "size: 16:9\n"
        "paginate: true\n"
        f"footer: {footer}\n"
        "---\n\n"
        f"<!-- generated-from: {source_path.name} / mode: fast / version: {SCRIPT_VERSION} -->\n\n"
    )
    return header + "\n---\n\n".join(slides).rstrip() + "\n"


def file_hash(text: str, mode: str) -> str:
    digest = hashlib.sha256()
    digest.update(text.encode("utf-8"))
    digest.update(mode.encode("utf-8"))
    digest.update(SCRIPT_VERSION.encode("utf-8"))
    return digest.hexdigest()


def load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        return {"version": 1, "items": {}}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "items": {}}


def save_manifest(manifest_path: Path, manifest: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def resolve_relative_path(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.name


def build_output_path(cache_dir: Path, relative_source: str) -> Path:
    rel = Path(relative_source)
    return (cache_dir / rel).with_suffix(".slides.md")


def main() -> int:
    args = parse_args()

    ensure_japanese_fonts()

    input_md = args.input_md.resolve()
    if not input_md.exists():
        print(f"ERROR: 入力ファイルが見つかりません: {input_md}", file=sys.stderr)
        return 1

    try:
        project_root = resolve_project_root(args, input_md)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    mode = args.mode
    # ai モードでも Stage 1 は fast と同じルールベース変換を行う。
    # Stage 2（エージェントによる構成最適化）はスクリプト外で実施される。
    generation_mode = "fast"

    cache_dir = resolve_cache_dir(args, project_root)
    manifest_path = cache_dir / "manifest.json"
    relative_source = resolve_relative_path(input_md, project_root)
    output_path = build_output_path(cache_dir, relative_source)

    source_text = normalize_newlines(input_md.read_text(encoding="utf-8"))
    source_hash = file_hash(source_text, mode)

    manifest = load_manifest(manifest_path)
    manifest.setdefault("items", {})
    item = manifest["items"].get(relative_source, {})

    cache_hit = (
        not args.force
        and item.get("source_hash") == source_hash
        and item.get("mode") == mode
        and output_path.exists()
    )

    if not cache_hit:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mermaid_count = 0
        lr_converted = 0
        text_diagram_count = 0
        preprocessed = source_text

        # テキスト図（ASCII art）→ Mermaid コードブロック変換
        preprocessed, text_diagram_count = convert_text_diagrams_to_mermaid(preprocessed)

        # Mermaid コードブロックを事前描画して SVG 画像参照に置換する
        if MERMAID_PATTERN.search(preprocessed):
            try:
                preprocessed, mermaid_count, lr_converted = replace_mermaid_blocks(
                    preprocessed, output_path.parent
                )
            except RuntimeError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1

        prepared = build_slide_markdown(input_md, preprocessed, args.theme, args.footer)
        output_path.write_text(prepared, encoding="utf-8")

        # ソースMDの figures/ ディレクトリをキャッシュ先にマージコピーする
        # Marp は .slides.md からの相対パスで画像を解決するため必須
        # 注意: replace_mermaid_blocks() が先にキャッシュの figures/ へ
        #       mermaid_*.svg を出力済みなので、rmtree してはいけない
        source_figures = input_md.parent / "figures"
        output_figures = output_path.parent / "figures"
        if source_figures.is_dir():
            if output_figures.is_symlink():
                output_figures.unlink()
            output_figures.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_figures, output_figures, dirs_exist_ok=True)

        manifest["items"][relative_source] = {
            "source_hash": source_hash,
            "mode": mode,
            "output_path": str(output_path),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        save_manifest(manifest_path, manifest)
    else:
        mermaid_count = 0
        lr_converted = 0
        text_diagram_count = 0

    status = "cache-hit" if cache_hit else "generated"
    if args.dry_run:
        status = "dry-run:" + status

    needs_review = mode == "ai"
    review_tag = " (agent-review-required)" if needs_review else ""

    print(f"OK: Slide markdown prepared ({status}{review_tag})")
    print(f"   source : {input_md}")
    print(f"   output : {output_path}")
    print(f"   mode   : {mode}")
    if text_diagram_count:
        print(f"   text→mermaid: {text_diagram_count} text diagrams auto-converted")
    if mermaid_count:
        lr_info = f" ({lr_converted} TD→LR auto-converted)" if lr_converted else ""
        print(f"   mermaid: {mermaid_count} diagrams rendered to SVG{lr_info}")
    # figures コピーの報告（キャッシュヒット時も figures/ が存在すればコピー済みと見なす）
    output_figures = output_path.parent / "figures"
    if output_figures.is_dir():
        fig_count = sum(1 for f in output_figures.iterdir() if f.is_file())
        if fig_count:
            print(f"   figures: {fig_count} files in cache")
    # 内部参照パターンを検出し警告を出力する
    # （自動除去はしない。Stage 2 で AI が文脈を考慮して除去する）
    ref_findings = detect_internal_references(source_text)
    if ref_findings:
        print(f"WARNING: 内部参照の可能性 ({len(ref_findings)}件検出):")
        for line_no, matched, label in ref_findings[:20]:
            print(f'   L{line_no}: "{matched}" ({label})')
        if len(ref_findings) > 20:
            print(f"   ... 他 {len(ref_findings) - 20} 件")

    # テキスト図（ASCII art 等）のうち未変換のものを警告する
    text_diagram_findings = detect_text_diagrams(source_text)
    unconverted = max(0, len(text_diagram_findings) - text_diagram_count)
    if unconverted > 0:
        print(f"WARNING: 未変換テキスト図 ({unconverted}件):")
        for start_ln, ln_count, summary in text_diagram_findings[:unconverted]:
            print(f"   L{start_ln}: コードブロック ({summary})")
        print("   → Stage 2 で Mermaid 変換・フォント縮小・箇条書き化を検討してください")
    # Mermaid フロー方向を検出し、縦長レイアウトに警告を出力する
    flow_findings = detect_mermaid_flow_direction(source_text)
    if flow_findings:
        print(f"WARNING: 縦長 Mermaid フローチャート ({len(flow_findings)}件検出):")
        for start_ln, direction, suggestion in flow_findings:
            print(f"   L{start_ln}: {direction} — {suggestion}")

    if needs_review:
        print("   review: slide-composition-guide.md に従いエージェントが構成を最適化してください")
    print(f"OUTPUT: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
