"""Preset loader — teams.yaml / learned-rules.yaml プリセット。

teams.yaml はビジネスドメイン設定の SSoT。config.yaml（インフラ設定）とは分離し、
ペルソナ・モデル割り当て・テーマ等のプリセットを一元管理する。

読み込み優先順位: CLI引数 > config.yaml上書き > teams.yaml > Pythonハードコードデフォルト

ワークフロープリミティブ:
  consensus  — ペルソナ分離 × 相互チェック × 収束判定（複数ラウンド）
  vote       — 複数モデルが独立回答 → ジャッジが最良を選定
  pipeline   — 設計→実装→レビュー→テスト等の順次実行
  specialty  — タスクタイプに基づく単一モデルルーティング
"""

from .discovery import (
    LEARNED_RULES_FILENAME,
    TEAMS_FILENAME,
    _find_learned_rules_dir,
    _find_learned_rules_yaml,
    _find_teams_yaml,
    normalize_scope,
)
from .learned_rules import DomainRules, LearnedRulesConfig
from .teams_config import (
    VALID_WORKFLOW_TYPES,
    DomainPreset,
    TeamsConfig,
    ValidationError,
)

__all__ = [
    "DomainPreset",
    "DomainRules",
    "LearnedRulesConfig",
    "TeamsConfig",
    "ValidationError",
    "VALID_WORKFLOW_TYPES",
    "TEAMS_FILENAME",
    "LEARNED_RULES_FILENAME",
    "normalize_scope",
    "_find_teams_yaml",
    "_find_learned_rules_yaml",
    "_find_learned_rules_dir",
]
