#!/usr/bin/env bash
# .claude/scripts/sync.sh — SSoT(projects/.claude/) → 各リポ + ~/.codex/ へのファイル同期
#
# 用途:
#   bash .claude/scripts/sync.sh        — ファイルコピーのみ（コミットなし）
#
# SSoT実体: projects/.claude/（非Gitディレクトリ。各リポへファイルコピーで配布）
# 同期方向: SSoT → 各リポへの一方向のみ
# 各リポ側の .claude/ を直接編集した場合、次回実行で上書きされる
# workspace-pm も他リポと同様に配布先として扱う
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLAUDE_DIR="$REPO_ROOT/.claude"

# ─── 0. Schema validation (Phase 5: v2.0 integrity gate) ───
echo "=== validate_schema_v2.py ==="
python3 "$CLAUDE_DIR/scripts/validate_schema_v2.py" || {
  echo "ERROR: Schema validation failed. Fix errors before syncing."
  exit 1
}
echo ""

# ─── 1. ~/.codex/ 同期（シンボリックリンク） ───
codex_home="${CODEX_HOME:-$HOME/.codex}"
if [ -d "$codex_home" ]; then
  bash "$CLAUDE_DIR/scripts/sync_codex_skills.sh" 2>/dev/null
  if [ ! -e "$codex_home/AGENTS.md" ] || [ -L "$codex_home/AGENTS.md" ]; then
    ln -sfn "$CLAUDE_DIR/CLAUDE.md" "$codex_home/AGENTS.md"
  fi
fi

# ─── 2. 各リポへファイルコピー（マルチリポ環境のみ） ───
REGISTRY="$CLAUDE_DIR/references/repo-registry.md"
[ -f "$REGISTRY" ] || exit 0

SYNCED=0
for repo_dir in "$REPO_ROOT"/*/; do
  [ -d "$repo_dir/.git" ] || continue
  # SSoT(.claude/) は隠しディレクトリなので */ にマッチしない。スキップ不要
  mkdir -p "$repo_dir/.claude"

  # 同期対象: CLAUDE.md, skills/(全スキル), references/(repo-registry.md除外), setup.sh, scripts/, hooks/, settings.json, slides/
  # settings.local.json はローカル専用のため同期対象外
  # repo-registry.md を除外する理由: 各リポに存在するとマルチリポ環境と誤判定するため
  cp "$CLAUDE_DIR/CLAUDE.md" "$repo_dir/.claude/CLAUDE.md"
  # Tier 1 スキルのみ配布（Tier 2 は platform CLI 必須のため projects/ 環境専用）
  rsync -a --delete \
    --exclude='ai-review' --exclude='ai-slides' --exclude='ai-task' \
    --exclude='ai-fix' --exclude='ai-spec-update' --exclude='ai-survey' \
    --exclude='ai-change-impact' --exclude='ai-pm-planning' \
    --exclude='slides-export' --exclude='ai-learn' \
    "$CLAUDE_DIR/skills/" "$repo_dir/.claude/skills/"
  # Tier 2 スキルを配布先から除去（--exclude は --delete 対象外のため明示削除）
  for _t2 in ai-review ai-slides ai-task ai-fix ai-spec-update ai-survey ai-change-impact ai-pm-planning slides-export ai-learn; do
    rm -rf "$repo_dir/.claude/skills/$_t2"
  done
  mkdir -p "$repo_dir/.claude/references"
  # IMP-072: rules/ ディレクトリはフィルタ配信するため rsync から除外
  rsync -a --delete --exclude='repo-registry.md' --exclude='learned-rules.yaml' \
    --exclude='rules/' \
    --exclude='development-guide.md' --exclude='github-projects-design.md' \
    "$CLAUDE_DIR/references/" "$repo_dir/.claude/references/"
  rm -f "$repo_dir/.claude/references/repo-registry.md"
  rm -f "$repo_dir/.claude/references/guides/development-guide.md"
  rm -f "$repo_dir/.claude/references/github-projects-design.md"

  # IMP-072: ドメイン別 YAML ディレクトリを scope.repos でフィルタ → 単一ファイルとして配信
  repo_name="$(basename "$repo_dir")"
  RULES_INPUT="$CLAUDE_DIR/references/rules"
  # ディレクトリが存在しなければ旧形式の単一ファイルを探す
  if [ ! -d "$RULES_INPUT" ] || [ -z "$(ls -A "$RULES_INPUT"/*.yaml 2>/dev/null | grep -v improvement-backlog)" ]; then
    RULES_INPUT="$CLAUDE_DIR/references/rules/learned-rules.yaml"
  fi
  mkdir -p "$repo_dir/.claude/references/rules"
  if python3 "$CLAUDE_DIR/scripts/filter_rules.py" \
    --input "$RULES_INPUT" \
    --registry "$REGISTRY" \
    --repo "$repo_name" \
    --output "$repo_dir/.claude/references/rules/learned-rules.yaml" \
    --manifest "$repo_dir/.claude/.filter-manifest.yaml" 2>/dev/null; then
    : # フィルタ成功
  else
    # フォールバック: フィルタ失敗時はドメインファイルを全コピー（PyYAML なし等）
    rsync -a --exclude='improvement-backlog.yaml' --exclude='*.bak' \
      "$CLAUDE_DIR/references/rules/" "$repo_dir/.claude/references/rules/"
  fi
  # improvement-backlog.yaml はフィルタ不要（SSoT参照用にそのままコピー）
  if [ -f "$CLAUDE_DIR/references/rules/improvement-backlog.yaml" ]; then
    cp "$CLAUDE_DIR/references/rules/improvement-backlog.yaml" "$repo_dir/.claude/references/rules/improvement-backlog.yaml"
  fi
  cp "$CLAUDE_DIR/setup.sh" "$repo_dir/.claude/setup.sh"
  if [ -d "$CLAUDE_DIR/scripts" ]; then
    mkdir -p "$repo_dir/.claude/scripts"
    rsync -a --delete --exclude='automation_engine' "$CLAUDE_DIR/scripts/" "$repo_dir/.claude/scripts/"
  fi
  # IMP-071: automation_engine/presets/ を全リポに配布（Tier 1/2 実装共有）
  # workflow_step.py が TeamsConfig / LearnedRulesConfig を直接 import する
  _AI_TEAM_PRESETS="$REPO_ROOT/platform/automation_engine/presets"
  _AI_TEAM_INIT="$REPO_ROOT/platform/automation_engine/__init__.py"
  if [ -d "$_AI_TEAM_PRESETS" ]; then
    mkdir -p "$repo_dir/.claude/scripts/automation_engine/presets"
    cp "$_AI_TEAM_INIT" "$repo_dir/.claude/scripts/automation_engine/__init__.py"
    rsync -a --delete "$_AI_TEAM_PRESETS/" "$repo_dir/.claude/scripts/automation_engine/presets/"
  fi
  if [ -d "$CLAUDE_DIR/hooks" ]; then
    mkdir -p "$repo_dir/.claude/hooks"
    rsync -a --delete "$CLAUDE_DIR/hooks/" "$repo_dir/.claude/hooks/"
  fi
  if [ -f "$CLAUDE_DIR/settings.json" ]; then
    cp "$CLAUDE_DIR/settings.json" "$repo_dir/.claude/settings.json"
  fi
  if [ -d "$CLAUDE_DIR/slides" ]; then
    mkdir -p "$repo_dir/.claude/slides"
    rsync -a --delete "$CLAUDE_DIR/slides/" "$repo_dir/.claude/slides/"
  fi
  if [ -d "$CLAUDE_DIR/.review-logs" ]; then
    mkdir -p "$repo_dir/.claude/.review-logs"
    rsync -a --delete "$CLAUDE_DIR/.review-logs/" "$repo_dir/.claude/.review-logs/"
  fi

  # development-guide.md を docs/ に配布（全リポ共通の運用 SSoT）
  if [ -f "$CLAUDE_DIR/references/guides/development-guide.md" ]; then
    mkdir -p "$repo_dir/docs"
    cp "$CLAUDE_DIR/references/guides/development-guide.md" "$repo_dir/docs/development-guide.md"
  fi

  # AGENTS.md シンボリックリンク（リポルート → .claude/CLAUDE.md）
  if [ -L "$repo_dir/AGENTS.md" ]; then
    : # 既にシンボリックリンク（スキップ）
  elif [ -e "$repo_dir/AGENTS.md" ]; then
    rm -f "$repo_dir/AGENTS.md"
    ln -s .claude/CLAUDE.md "$repo_dir/AGENTS.md"
  else
    ln -s .claude/CLAUDE.md "$repo_dir/AGENTS.md"
  fi

  # .claude/.claude/ 二重ネスト除去（auto_learn hook が誤作成する場合の安全策）
  rm -rf "$repo_dir/.claude/.claude"

  # Codex スキル検出: .agents/skills → .claude/skills シンボリックリンク
  # Codex は .agents/skills/ からスキルを検出する（Claude Code は .claude/skills/）
  mkdir -p "$repo_dir/.agents"
  ln -sfn ../.claude/skills "$repo_dir/.agents/skills"

  # .worktrees/ を .gitignore に追加（未設定の場合）
  # .gitignore が存在しなければ新規作成
  [ ! -f "$repo_dir/.gitignore" ] && touch "$repo_dir/.gitignore"
  if ! grep -qF '.worktrees/' "$repo_dir/.gitignore" 2>/dev/null; then
    [ -s "$repo_dir/.gitignore" ] && [ -n "$(tail -c 1 "$repo_dir/.gitignore")" ] && echo '' >> "$repo_dir/.gitignore"
    echo '.worktrees/' >> "$repo_dir/.gitignore"
  fi

  # .pending-feedback*.json を .gitignore に追加（ローカル専用ファイル）
  if ! grep -qF '.claude/.pending-feedback' "$repo_dir/.gitignore" 2>/dev/null; then
    echo '.claude/.pending-feedback*.json' >> "$repo_dir/.gitignore"
  fi

  # 旧アーキテクチャの platform スキル .gitignore エントリを除去（シンボリックリンク→コピーへ移行済み）
  for old_entry in '.claude/skills/ai-learn' '.claude/skills/ai-review' '.claude/skills/ai-slides' '.claude/skills/ai-task'; do
    if grep -qF "$old_entry" "$repo_dir/.gitignore" 2>/dev/null; then
      # macOS sed -i requires backup extension
      sed -i '' "\|${old_entry}|d" "$repo_dir/.gitignore"
    fi
  done

  SYNCED=$((SYNCED + 1))
done
echo "synced $SYNCED repos"
