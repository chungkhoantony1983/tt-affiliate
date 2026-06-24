#!/bin/bash
# verify-readme-coverage.sh
# .claude/ 配下の全ディレクトリに README.md が存在するか検証する。
# スキル個別ディレクトリ（skills/*/）は SKILL.md で代替するため除外。
# __pycache__ および隠しディレクトリ（.context-locks 等）も除外。
#
# Usage: bash scripts/verify-readme-coverage.sh [target_dir]
#   target_dir: 検証対象ディレクトリ（デフォルト: スクリプトの親の親 = .claude/）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="${1:-$(dirname "$SCRIPT_DIR")}"

TOTAL=0
COVERED=0
MISSING=()

while IFS= read -r dir; do
  # 除外: skills/ 配下のスキル個別ディレクトリ（SKILL.md で代替）
  rel_path="${dir#"$TARGET_DIR"/}"
  if [[ "$rel_path" =~ ^skills/[^/]+$ ]]; then
    continue
  fi
  # 除外: スキル内サブディレクトリ（skills/*/references/ 等）
  if [[ "$rel_path" =~ ^skills/[^/]+/.+ ]]; then
    continue
  fi

  TOTAL=$((TOTAL + 1))
  if [ -f "$dir/README.md" ]; then
    COVERED=$((COVERED + 1))
  else
    MISSING+=("$rel_path")
  fi
done < <(find "$TARGET_DIR" -type d \
  ! -path '*/__pycache__' \
  ! -path '*/__pycache__/*' \
  ! -path '*/.context-locks' \
  ! -path '*/.context-locks/*' \
  ! -path "$TARGET_DIR/*/.claude" \
  ! -path "$TARGET_DIR/*/.claude/*" \
  | sort)

if [ "$TOTAL" -eq 0 ]; then
  echo "No directories found in $TARGET_DIR"
  exit 1
fi

RATE=$(echo "scale=1; $COVERED * 100 / $TOTAL" | bc)

echo "==============================="
echo " README カバー率レポート"
echo "==============================="
echo "対象: $TARGET_DIR"
echo "ディレクトリ数: $TOTAL"
echo "README あり:    $COVERED"
echo "README なし:    $((TOTAL - COVERED))"
echo "カバー率:       ${RATE}%"
echo ""

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "--- README 欠損ディレクトリ ---"
  for m in "${MISSING[@]}"; do
    echo "  $m"
  done
  echo ""
fi

if [ "$COVERED" -eq "$TOTAL" ]; then
  echo "OK: 全ディレクトリに README.md が存在します"
  exit 0
else
  echo "WARN: ${#MISSING[@]} ディレクトリに README.md がありません"
  exit 1
fi
