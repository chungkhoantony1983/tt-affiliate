"""Path discovery and scope normalization for teams.yaml / learned-rules.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

TEAMS_FILENAME = "teams.yaml"
LEARNED_RULES_FILENAME = "learned-rules.yaml"
LEARNED_RULES_DIR = "rules"  # ドメイン別 YAML を格納するディレクトリ名


def normalize_scope(scope: Any) -> dict[str, Any] | None:
    """scope フィールドを v1.3 構造化形式に正規化。

    Canonical implementation: scripts/filter_rules.py. Keep in sync.

    - None / 未設定 → None
    - str ("project-poc") → {"project": "project-poc"}  (v1.2 後方互換)
    - dict → そのまま
    """
    if scope is None:
        return None
    if isinstance(scope, str):
        return {"project": scope}
    if isinstance(scope, dict):
        return scope
    return None


def _find_teams_yaml() -> Path | None:
    """teams.yaml を探索。

    検索優先順位:
      1. CWD/teams.yaml (直下)
      2. CWD/.claude/references/config/teams.yaml (SSoT統合パス)
      3. CWD/platform/teams.yaml (旧配置 / 開発時)
      4. CWD/../.claude/references/config/teams.yaml (リポ内実行)
      5. CWD/../../.claude/references/config/teams.yaml (worktree内実行)
      6. ~/.platform/teams.yaml (ユーザーホーム)
    """
    candidates = [
        Path.cwd() / TEAMS_FILENAME,
        Path.cwd() / ".claude" / "references" / "config" / TEAMS_FILENAME,
        Path.cwd() / "platform" / TEAMS_FILENAME,
        Path.cwd().parent / ".claude" / "references" / "config" / TEAMS_FILENAME,
        Path.cwd().parent.parent / ".claude" / "references" / "config" / TEAMS_FILENAME,
        Path.home() / ".platform" / TEAMS_FILENAME,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _find_learned_rules_yaml() -> Path | None:
    """learned-rules.yaml を探索。.claude/references/ を期待。

    worktree 内（repo/.worktrees/branch/）での実行も考慮し、
    親の親ディレクトリまで遡って探索する。

    IMP-072: ディレクトリ分割後も後方互換維持。
    単一ファイルが見つかればそのパスを返す。
    見つからなければ _find_learned_rules_dir() を使う。
    """
    candidates = [
        Path.cwd() / ".claude" / "references" / "rules" / LEARNED_RULES_FILENAME,
        Path.cwd().parent / ".claude" / "references" / "rules" / LEARNED_RULES_FILENAME,
        # worktree: repo/.worktrees/branch/ → repo/.claude/references/
        Path.cwd().parent.parent / ".claude" / "references" / "rules" / LEARNED_RULES_FILENAME,
        Path.home() / ".claude" / "references" / "rules" / LEARNED_RULES_FILENAME,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _find_learned_rules_dir() -> Path | None:
    """ドメイン別 YAML ファイルが格納された rules/ ディレクトリを探索。

    IMP-072: learned-rules.yaml のドメイン別分割対応。
    rules/ ディレクトリ内に *.yaml（improvement-backlog.yaml を除く）が
    1つ以上存在するディレクトリを返す。
    """
    candidates = [
        Path.cwd() / ".claude" / "references" / LEARNED_RULES_DIR,
        Path.cwd().parent / ".claude" / "references" / LEARNED_RULES_DIR,
        Path.cwd().parent.parent / ".claude" / "references" / LEARNED_RULES_DIR,
        Path.home() / ".claude" / "references" / LEARNED_RULES_DIR,
    ]
    for c in candidates:
        if c.is_dir():
            # ドメイン YAML が1つ以上あるか確認
            yamls = [
                f for f in c.glob("*.yaml")
                if f.name != "improvement-backlog.yaml"
                and f.name != "learned-rules.yaml"
                and not f.name.endswith(".bak")
            ]
            if yamls:
                return c
    return None
