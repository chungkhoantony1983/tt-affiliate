#!/usr/bin/env bash
# .claude/scripts/validate-pj-config.sh — 各リポの PJ固有パス設定を標準フォーマットに対して検証
#
# 用途:
#   bash .claude/scripts/validate-pj-config.sh        — 全リポを検証
#   bash .claude/scripts/validate-pj-config.sh ea     — 指定リポのみ検証
#
# 検証項目:
#   1. {DR_PATH} が {PR番号}/ を含むか（PR番号サブフォルダ方式）
#   2. {REVIEW_LOG_PATH} が {DR_PATH} 配下の review-logs/ を指すか
#   3. {BASE_BRANCH} が repo-registry.md のベースブランチと一致するか
#   4. 非標準変数（{CONSTRAINTS_PATH} 等）の検出
#
# 終了コード:
#   0 = 全リポ準拠
#   1 = 警告あり
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGISTRY="$REPO_ROOT/.claude/references/repo-registry.md"

[ -f "$REGISTRY" ] || { echo "ERROR: repo-registry.md not found"; exit 1; }

FILTER="${1:-}"
WARNINGS=0
CHECKED=0

# repo-registry.md からベースブランチを取得する関数
get_registry_base_branch() {
  local repo_name="$1"
  # テーブル行からベースブランチ列（4番目）を抽出
  grep -E "^\| ${repo_name} " "$REGISTRY" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $5); print $5}' || echo ""
}

for repo_dir in "$REPO_ROOT"/*/; do
  [ -d "$repo_dir/.git" ] || continue
  repo_name="$(basename "$repo_dir")"

  if [ -n "$FILTER" ] && [ "$repo_name" != "$FILTER" ]; then
    continue
  fi

  claude_md="$repo_dir/CLAUDE.md"
  if [ ! -f "$claude_md" ]; then
    echo "SKIP  $repo_name (CLAUDE.md not found)"
    continue
  fi

  # PJ固有パス設定テーブルの存在確認
  if ! grep -q "PJ固有パス設定" "$claude_md" 2>/dev/null; then
    echo "SKIP  $repo_name (PJ固有パス設定 section not found)"
    continue
  fi

  CHECKED=$((CHECKED + 1))
  REPO_WARNS=0
  REPO_MSGS=""

  # テーブル行から値列（2番目の |...| ）を抽出するヘルパー
  extract_value() {
    local line="$1"
    # | `{VAR}` | `value` | → value
    echo "$line" | awk -F'|' '{print $3}' | sed 's/`//g; s/^[[:space:]]*//; s/[[:space:]]*$//'
  }

  # --- 検証1: {DR_PATH} が {PR番号}/ を含むか ---
  dr_line=$(grep '{DR_PATH}' "$claude_md" | grep '^|' | head -1 || true)
  dr_path=""
  if [ -n "$dr_line" ]; then
    dr_path=$(extract_value "$dr_line")
  fi
  if [ -n "$dr_path" ]; then
    if ! echo "$dr_path" | grep -q '{PR番号}'; then
      REPO_MSGS="${REPO_MSGS}  WARN  {DR_PATH} missing {PR番号}/ suffix: '$dr_path'\n"
      REPO_MSGS="${REPO_MSGS}        expected: docs/decision-records/{PR番号}/\n"
      REPO_WARNS=$((REPO_WARNS + 1))
    fi
  else
    REPO_MSGS="${REPO_MSGS}  WARN  {DR_PATH} not found in table\n"
    REPO_WARNS=$((REPO_WARNS + 1))
  fi

  # --- 検証2: {REVIEW_LOG_PATH} ---
  rl_line=$(grep '{REVIEW_LOG_PATH}' "$claude_md" | grep '^|' | head -1 || true)
  rl_path=""
  if [ -n "$rl_line" ]; then
    rl_path=$(extract_value "$rl_line")
  fi
  if [ -n "$rl_path" ]; then
    if ! echo "$rl_path" | grep -q '{PR番号}.*review-logs'; then
      REPO_MSGS="${REPO_MSGS}  WARN  {REVIEW_LOG_PATH} non-standard: '$rl_path'\n"
      REPO_MSGS="${REPO_MSGS}        expected: docs/decision-records/{PR番号}/review-logs/ or {DR_PATH}/review-logs/\n"
      REPO_WARNS=$((REPO_WARNS + 1))
    fi
  fi

  # --- 検証3: {BASE_BRANCH} と registry の一致 ---
  bb_line=$(grep '{BASE_BRANCH}' "$claude_md" | grep '^|' | head -1 || true)
  base_branch=""
  if [ -n "$bb_line" ]; then
    base_branch=$(extract_value "$bb_line")
  fi
  registry_branch=$(get_registry_base_branch "$repo_name")
  if [ -n "$base_branch" ] && [ -n "$registry_branch" ]; then
    if [ "$base_branch" != "$registry_branch" ]; then
      REPO_MSGS="${REPO_MSGS}  WARN  {BASE_BRANCH} mismatch: CLAUDE.md='$base_branch' vs registry='$registry_branch'\n"
      REPO_WARNS=$((REPO_WARNS + 1))
    fi
  fi

  # --- 検証4: 非標準変数の検出 ---
  non_std=$(grep -oE '`\{[A-Z_]+\}`' "$claude_md" | grep -v -E '(DR_PATH|REVIEW_LOG_PATH|BASE_BRANCH|PR番号|PJフォルダ)' | sort -u || true)
  if [ -n "$non_std" ]; then
    REPO_MSGS="${REPO_MSGS}  INFO  non-standard variables: $non_std\n"
  fi

  # --- 結果出力 ---
  if [ "$REPO_WARNS" -eq 0 ]; then
    echo "OK    $repo_name"
  else
    echo "WARN  $repo_name ($REPO_WARNS warning(s))"
    printf "%b" "$REPO_MSGS"
    WARNINGS=$((WARNINGS + REPO_WARNS))
  fi
done

echo ""
echo "--- validated: $CHECKED repos, warnings: $WARNINGS ---"
[ "$WARNINGS" -eq 0 ] || exit 1
