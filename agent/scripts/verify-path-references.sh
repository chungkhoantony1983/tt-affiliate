#!/usr/bin/env bash
# .claude/scripts/verify-path-references.sh — SSoT内のファイルパス参照の整合性を検証
#
# 用途:
#   bash .claude/scripts/verify-path-references.sh           — 全ファイルを検証
#   bash .claude/scripts/verify-path-references.sh --verbose  — 検証済みパスも表示
#
# 検証対象:
#   - CLAUDE.md の SSoT 索引テーブル内のパス
#   - skills/*/SKILL.md 内のファイルパス参照
#   - improvement-backlog.yaml の change_targets（proposed/in-progress のみ）
#   - references/ 内の README.md のファイルパス参照
#
# 除外:
#   - テンプレート変数（{PR番号} 等）を含むパス
#   - コマンド行（bash, git, python 等で始まる行）
#   - 取り消し線（~~）で囲まれたパス
#   - PJ固有のパス例示（docs/02_, docs/decision-records/ 等）
#   - 完了済み改善計画の change_targets
#
# 終了コード:
#   0 = 全パス参照が有効
#   1 = 不一致あり
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CLAUDE_DIR/.." && pwd)"

ERRORS=0
CHECKED=0
VERBOSE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true

red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

# パスがスキップ対象か判定
should_skip() {
  local ref_path="$1"
  local line="$2"

  # 空パス、URL、アンカーリンク
  [[ -z "$ref_path" || "$ref_path" == http* || "$ref_path" == "#"* ]] && return 0
  # テンプレート変数
  [[ "$ref_path" == *"{"* ]] && return 0
  # ワイルドカード
  [[ "$ref_path" == *"*"* ]] && return 0
  # ホームディレクトリ参照（~/.codex 等）
  [[ "$ref_path" == "~/"* ]] && return 0
  # 取り消し線
  [[ "$ref_path" == "~~"* || "$line" == *"~~"*"$ref_path"*"~~"* ]] && return 0
  # コマンド行（bash, git, python, echo, mkdir, rm 等）
  local trimmed
  trimmed="$(echo "$line" | sed 's/^[[:space:]]*//')"
  [[ "$trimmed" == "bash "* || "$trimmed" == "git "* || "$trimmed" == "python"* || \
     "$trimmed" == "echo "* || "$trimmed" == "mkdir "* || "$trimmed" == "rm "* || \
     "$trimmed" == "source "* || "$trimmed" == "curl "* ]] && return 0
  # コードブロック内のコマンド（`bash ...`）
  [[ "$line" == *'`bash '* || "$line" == *'`git '* || "$line" == *'`python'* ]] && return 0
  # PJ固有のパス例示（SSoTではなくPJリポ側に存在するパス）
  [[ "$ref_path" == docs/0* || "$ref_path" == docs/decision-records/* || \
     "$ref_path" == docs/exports/* || "$ref_path" == scripts/export* || \
     "$ref_path" == 0_Project/* ]] && return 0
  # ディレクトリなしのベアファイル名（/が含まれない）— SSoT索引は除く
  [[ "$ref_path" != */* ]] && return 0
  # 矢印（→）を含むパス（リネーム記述）
  [[ "$ref_path" == *"→"* || "$ref_path" == *" → "* ]] && return 0
  # 日本語を含むパス（説明文の一部）
  if echo "$ref_path" | grep -qP '[\x{3000}-\x{9FFF}]' 2>/dev/null; then
    return 0
  fi
  # 括弧付きの注記（`(削除)`, `(分割)` 等）
  [[ "$ref_path" == *"("* ]] && return 0

  return 1
}

# パスを解決して存在チェック
check_path() {
  local source_file="$1"
  local ref_path="$2"
  local line_num="${3:-?}"
  local line="${4:-}"

  # スキップ判定
  if should_skip "$ref_path" "$line"; then
    return 0
  fi

  CHECKED=$((CHECKED + 1))

  # 相対パスの解決
  local resolved_path
  if [[ "$ref_path" == ./* || "$ref_path" == ../* ]]; then
    local dir
    dir="$(cd "$(dirname "$source_file")" && cd "$(dirname "$ref_path")" 2>/dev/null && pwd)" || {
      red "  FAIL: $ref_path (line $line_num)"
      echo "        → cannot resolve relative path"
      echo "        ← $(basename "$source_file")"
      ERRORS=$((ERRORS + 1))
      return 0
    }
    resolved_path="$dir/$(basename "$ref_path")"
  elif [[ "$ref_path" == /* ]]; then
    resolved_path="$ref_path"
  else
    # skills/ や references/ で始まるパスは .claude/ 配下
    if [[ "$ref_path" == skills/* || "$ref_path" == references/* || \
          "$ref_path" == scripts/* || "$ref_path" == hooks/* || \
          "$ref_path" == docs/* ]]; then
      resolved_path="$CLAUDE_DIR/$ref_path"
    # platform/ で始まるパスは REPO_ROOT 配下
    elif [[ "$ref_path" == platform/* ]]; then
      resolved_path="$REPO_ROOT/$ref_path"
    # .claude/ で始まるパスは REPO_ROOT 配下
    elif [[ "$ref_path" == .claude/* ]]; then
      resolved_path="$REPO_ROOT/$ref_path"
    else
      # ソースファイルの親ディレクトリからの相対
      resolved_path="$(dirname "$source_file")/$ref_path"
    fi
  fi

  # ディレクトリ参照（末尾 /）の場合
  if [[ "$ref_path" == */ ]]; then
    if [[ ! -d "${resolved_path%/}" ]]; then
      red "  FAIL: $ref_path (line $line_num in $(basename "$source_file"))"
      ERRORS=$((ERRORS + 1))
    elif $VERBOSE; then
      echo "    OK: $ref_path"
    fi
    return 0
  fi

  # ファイル存在チェック
  if [[ ! -e "$resolved_path" && ! -d "$resolved_path" ]]; then
    red "  FAIL: $ref_path (line $line_num in $(basename "$source_file"))"
    ERRORS=$((ERRORS + 1))
  elif $VERBOSE; then
    echo "    OK: $ref_path"
  fi
}

# --- 1. CLAUDE.md SSoT 索引テーブルのパス検証 ---
bold "=== CLAUDE.md SSoT 索引 ==="
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
if [[ -f "$CLAUDE_MD" ]]; then
  in_ssot_table=false
  line_num=0
  while IFS= read -r line; do
    line_num=$((line_num + 1))
    # SSoT 索引テーブルの開始を検出
    if [[ "$line" == *"関心ごと"*"正本ファイル"* ]]; then
      in_ssot_table=true
      continue
    fi
    # テーブル終了検出（空行またはヘッダー）
    if $in_ssot_table && [[ "$line" != "|"* ]]; then
      in_ssot_table=false
      continue
    fi
    # 区切り行スキップ
    [[ "$line" == *"---"* ]] && continue

    if $in_ssot_table; then
      # 取り消し線の行をスキップ
      [[ "$line" == *"~~"* ]] && continue
      # バッククォート内のファイルパスを抽出（ディレクトリ区切りを含むもの）
      while read -r path; do
        [[ -n "$path" && "$path" == */* ]] && check_path "$CLAUDE_MD" "$path" "$line_num" "$line"
      done < <(echo "$line" | grep -oE '`[^`]+`' | tr -d '`' | grep '/' || true)
    fi
  done < "$CLAUDE_MD"
  green "  CLAUDE.md SSoT 索引: checked"
fi

# --- 2. SKILL.md 内のファイル参照 ---
bold "=== skills/*/SKILL.md ==="
for skill_md in "$CLAUDE_DIR"/skills/*/SKILL.md; do
  [[ -f "$skill_md" ]] || continue
  skill_name="$(basename "$(dirname "$skill_md")")"
  in_code_block=false
  line_num=0
  while IFS= read -r line; do
    line_num=$((line_num + 1))
    # コードブロックのトグル
    if [[ "$line" == '```'* ]]; then
      if $in_code_block; then in_code_block=false; else in_code_block=true; fi
      continue
    fi
    # コードブロック内はスキップ
    $in_code_block && continue

    # バッククォート内のパス参照を抽出（ディレクトリ区切りを含むもの）
    while read -r path; do
      if [[ -n "$path" && "$path" == */* ]]; then
        check_path "$skill_md" "$path" "$line_num" "$line"
      fi
    done < <(echo "$line" | grep -oE '`[^`]+/[^`]+\.(md|yaml|yml|py|js|sh|html|json)`' | tr -d '`' || true)
  done < "$skill_md"
  green "  $skill_name: checked"
done

# --- 3. improvement-backlog.yaml の change_targets（未完了のみ） ---
bold "=== improvement-backlog.yaml (proposed/in-progress only) ==="
BACKLOG="$CLAUDE_DIR/references/rules/improvement-backlog.yaml"
if [[ -f "$BACKLOG" ]]; then
  # Pass 1: done IMP の ID を一時ファイルに収集（bash 3 互換）
  DONE_IDS="$(mktemp)"
  trap "rm -f '$DONE_IDS'" EXIT
  current_id=""
  while IFS= read -r line; do
    if [[ "$line" =~ ^-[[:space:]]*id:[[:space:]]*(IMP-[0-9]+) ]]; then
      current_id="${BASH_REMATCH[1]}"
    fi
    if [[ "$line" =~ ^[[:space:]]*status:[[:space:]]*(done|completed) && -n "$current_id" ]]; then
      echo "$current_id" >> "$DONE_IDS"
    fi
  done < "$BACKLOG"

  # Pass 2: 未完了 IMP の change_targets のみ検証
  current_id=""
  line_num=0
  in_targets=false
  while IFS= read -r line; do
    line_num=$((line_num + 1))
    if [[ "$line" =~ ^-[[:space:]]*id:[[:space:]]*(IMP-[0-9]+) ]]; then
      current_id="${BASH_REMATCH[1]}"
      in_targets=false
    fi
    if [[ "$line" =~ ^[[:space:]]*change_targets: ]]; then
      in_targets=true
      continue
    fi
    if $in_targets && [[ "$line" =~ ^[[:space:]]*-[[:space:]]+ ]]; then
      # 完了済み IMP はスキップ
      if grep -qx "$current_id" "$DONE_IDS" 2>/dev/null; then
        continue
      fi
      path="$(echo "$line" | sed 's/^[[:space:]]*-[[:space:]]*//' | tr -d "'" | tr -d '"')"
      if [[ -n "$path" ]]; then
        check_path "$BACKLOG" "$path" "$line_num" "$line"
      fi
    elif $in_targets && [[ ! "$line" =~ ^[[:space:]]*- ]]; then
      in_targets=false
    fi
  done < "$BACKLOG"
  green "  improvement-backlog.yaml: checked"
fi

# --- 4. references/ README.md のファイル参照 ---
bold "=== references/ README.md ==="
for readme in "$CLAUDE_DIR"/references/README.md "$CLAUDE_DIR"/references/*/README.md; do
  [[ -f "$readme" ]] || continue
  rel_readme="${readme#"$CLAUDE_DIR"/}"
  in_code_block=false
  line_num=0
  while IFS= read -r line; do
    line_num=$((line_num + 1))
    if [[ "$line" == '```'* ]]; then
      if $in_code_block; then in_code_block=false; else in_code_block=true; fi
      continue
    fi
    $in_code_block && continue

    # バッククォート内のファイルパスを抽出
    while read -r path; do
      if [[ -n "$path" && "$path" == */* ]]; then
        check_path "$readme" "$path" "$line_num" "$line"
      fi
    done < <(echo "$line" | grep -oE '`[^`]+/[^`]+\.(md|yaml|yml|py|js|sh|html|json)`' | tr -d '`' || true)
  done < "$readme"
  green "  $rel_readme: checked"
done

# --- 結果サマリ ---
echo ""
bold "=== 結果 ==="
echo "  検証数: $CHECKED"
if [[ $ERRORS -gt 0 ]]; then
  red "  エラー: $ERRORS 件"
  exit 1
else
  green "  全パス参照 OK"
  exit 0
fi
