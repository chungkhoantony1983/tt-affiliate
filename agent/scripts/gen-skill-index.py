#!/usr/bin/env python3
"""SKILL.md の frontmatter からスキル一覧テーブルを自動生成する (IMP-015)。

Usage:
    python .claude/scripts/gen-skill-index.py              # テーブルを stdout に出力
    python .claude/scripts/gen-skill-index.py --update      # CLAUDE.md を直接更新
    python .claude/scripts/gen-skill-index.py --check       # 差分があれば exit 1
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
CLAUDE_MD = Path(__file__).resolve().parent.parent / "CLAUDE.md"

# スキル一覧テーブルの開始/終了マーカー
TABLE_START = "| スキル | 用途 | Tier | 実行環境 |"
TABLE_END_PATTERN = re.compile(r"^\s*$|^[^|]")  # 空行 or テーブル行でない行

# Tier のデフォルト値（frontmatter に tier がない場合は CLAUDE.md 側から取得）
DEFAULT_TIER_MAP: dict[str, tuple[str, str]] = {}  # populated from CLAUDE.md if needed


def parse_frontmatter(path: Path) -> dict[str, str]:
    """SKILL.md の YAML frontmatter を簡易パースする。"""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.index("---", 3)
    fm_text = text[3:end]
    result: dict[str, str] = {}
    for line in fm_text.strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def collect_skills() -> list[dict[str, str]]:
    """全 SKILL.md から情報を収集する。"""
    skills = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        fm = parse_frontmatter(skill_md)
        if not fm.get("name"):
            continue
        skills.append({
            "dir": skill_dir.name,
            "name": fm.get("name", skill_dir.name),
            "description": fm.get("description", ""),
            "tier": fm.get("tier", ""),
            "runtime": fm.get("runtime", ""),
        })
    # Sort: Tier 1 → Tier 2 → infra, then alphabetical within each tier
    tier_order = {"1": 0, "2": 1, "infra": 2, "": 3}
    skills.sort(key=lambda s: (tier_order.get(s["tier"], 3), s["name"]))
    return skills


def generate_table(skills: list[dict[str, str]]) -> str:
    """スキル一覧の Markdown テーブルを生成する。"""
    lines = [
        "| スキル | 用途 | Tier | 実行環境 |",
        "|--------|------|:---:|------|",
    ]
    for s in skills:
        name = s["name"]
        desc = s["description"]
        tier = s["tier"]
        runtime = s["runtime"] or ""

        # Tier 表示: "infra" → "—"
        tier_display = {"1": "1", "2": "2", "infra": "—"}.get(tier, "—")

        lines.append(f"| `/{name}` | {desc} | {tier_display} | {runtime} |")
    return "\n".join(lines)


def find_table_range(text: str) -> tuple[int, int] | None:
    """CLAUDE.md 内のスキル一覧テーブルの開始行と終了行を特定する。"""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if TABLE_START in line:
            start = i
            break
    if start is None:
        return None

    # テーブルの終了を探す（ヘッダー + セパレータ行 + データ行...）
    end = start + 2  # skip header + separator
    while end < len(lines):
        if not lines[end].startswith("|"):
            break
        end += 1
    return (start, end)


def update_claude_md(table: str) -> bool:
    """CLAUDE.md のスキル一覧テーブルを更新する。変更があれば True。"""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    rng = find_table_range(text)
    if rng is None:
        print("ERROR: CLAUDE.md にスキル一覧テーブルが見つかりません", file=sys.stderr)
        return False

    lines = text.splitlines()
    old_table = "\n".join(lines[rng[0]:rng[1]])
    if old_table == table:
        return False

    new_lines = lines[:rng[0]] + table.splitlines() + lines[rng[1]:]
    CLAUDE_MD.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description="スキル一覧テーブル自動生成")
    parser.add_argument("--update", action="store_true", help="CLAUDE.md を直接更新")
    parser.add_argument("--check", action="store_true", help="差分チェック（CI用）")
    args = parser.parse_args()

    skills = collect_skills()
    if not skills:
        print("ERROR: SKILL.md が見つかりません", file=sys.stderr)
        sys.exit(1)

    table = generate_table(skills)

    if args.update:
        changed = update_claude_md(table)
        if changed:
            print(f"CLAUDE.md のスキル一覧を更新しました（{len(skills)} スキル）")
        else:
            print(f"CLAUDE.md のスキル一覧は最新です（{len(skills)} スキル）")
    elif args.check:
        text = CLAUDE_MD.read_text(encoding="utf-8")
        rng = find_table_range(text)
        if rng is None:
            print("ERROR: テーブルが見つかりません", file=sys.stderr)
            sys.exit(1)
        lines = text.splitlines()
        current = "\n".join(lines[rng[0]:rng[1]])
        if current != table:
            print("CLAUDE.md のスキル一覧が古くなっています。")
            print("  実行: python .claude/scripts/gen-skill-index.py --update")
            sys.exit(1)
        print("OK: スキル一覧は最新です")
    else:
        print(table)


if __name__ == "__main__":
    main()
