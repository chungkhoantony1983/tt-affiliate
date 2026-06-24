#!/usr/bin/env bash
# .claude/scripts/verify-sync.sh — SSoT と各リポの .claude/ の一致を検証
#
# 用途:
#   bash .claude/scripts/verify-sync.sh        — 全リポを検証
#   bash .claude/scripts/verify-sync.sh ea     — 指定リポのみ検証
#
# 終了コード:
#   0 = 全リポ一致
#   1 = 不一致あり
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLAUDE_DIR="$REPO_ROOT/.claude"
REGISTRY="$CLAUDE_DIR/references/repo-registry.md"

[ -f "$REGISTRY" ] || { echo "ERROR: repo-registry.md not found (not a multi-repo environment)"; exit 1; }

FILTER="${1:-}"
ERRORS=0
CHECKED=0

for repo_dir in "$REPO_ROOT"/*/; do
  [ -d "$repo_dir/.git" ] || continue
  repo_name="$(basename "$repo_dir")"

  # フィルタ指定がある場合、一致するリポのみ検証
  if [ -n "$FILTER" ] && [ "$repo_name" != "$FILTER" ]; then
    continue
  fi

  # .claude/ が存在しないリポはスキップ
  if [ ! -d "$repo_dir/.claude" ]; then
    echo "SKIP  $repo_name (.claude/ not found)"
    continue
  fi

  # 同期対象ファイルの一致検証
  # 除外: repo-registry.md（SSoTにのみ存在）、settings.local.json（ローカル専用）
  # 除外: learned-rules.yaml（IMP-035: filter_rules.py でフィルタ配信のため SSoT と異なる可能性）
  # 除外: .filter-manifest.yaml（フィルタ結果のマニフェスト、SSoT には存在しない）
  # 除外: development-guide.md, github-projects-design.md（docs/ に配布 or SSoTのみ保持）
  DIFF_OUTPUT=$(diff -rq \
    --exclude='repo-registry.md' \
    --exclude='settings.local.json' \
    --exclude='.pending-feedback.json' \
    --exclude='.pending-feedback-archive.json' \
    --exclude='learned-rules.yaml' \
    --exclude='.filter-manifest.yaml' \
    --exclude='.context-locks' \
    --exclude='.hook-hash' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='automation_engine' \
    --exclude='development-guide.md' \
    --exclude='github-projects-design.md' \
    "$CLAUDE_DIR/" "$repo_dir/.claude/" 2>&1 \
    | grep -v "^Only in $CLAUDE_DIR" || true)

  # learned-rules.yaml の検証: フィルタマニフェストが存在すればフィルタ済みとして扱う
  # マニフェストがなければ SSoT と一致することを確認
  LR_SSoT="$CLAUDE_DIR/references/rules/learned-rules.yaml"
  LR_REPO="$repo_dir/.claude/references/rules/learned-rules.yaml"
  if [ -f "$LR_REPO" ]; then
    if [ -f "$repo_dir/.claude/.filter-manifest.yaml" ]; then
      : # フィルタ済み（差異は期待通り）
    elif ! diff -q "$LR_SSoT" "$LR_REPO" >/dev/null 2>&1; then
      DIFF_OUTPUT="${DIFF_OUTPUT:+$DIFF_OUTPUT
}Files $LR_SSoT and $LR_REPO differ (no filter manifest)"
    fi
  fi

  # IMP-071: automation_engine/presets/ の一致検証（Tier 1/2 実装共有）
  AI_TEAM_SRC="$REPO_ROOT/platform/automation_engine"
  AI_TEAM_DST="$repo_dir/.claude/scripts/automation_engine"
  if [ -d "$AI_TEAM_SRC/presets" ]; then
    if [ ! -d "$AI_TEAM_DST/presets" ]; then
      DIFF_OUTPUT="${DIFF_OUTPUT:+$DIFF_OUTPUT
}Missing automation_engine/presets/ in $repo_name/.claude/scripts/"
    else
      AT_DIFF=$(diff -rq \
        --exclude='__pycache__' \
        "$AI_TEAM_SRC/presets/" "$AI_TEAM_DST/presets/" 2>&1 || true)
      # __init__.py も検証
      if [ -f "$AI_TEAM_SRC/__init__.py" ] && [ -f "$AI_TEAM_DST/__init__.py" ]; then
        if ! diff -q "$AI_TEAM_SRC/__init__.py" "$AI_TEAM_DST/__init__.py" >/dev/null 2>&1; then
          AT_DIFF="${AT_DIFF:+$AT_DIFF
}Files automation_engine/__init__.py differ"
        fi
      elif [ -f "$AI_TEAM_SRC/__init__.py" ]; then
        AT_DIFF="${AT_DIFF:+$AT_DIFF
}Missing automation_engine/__init__.py in $repo_name"
      fi
      if [ -n "$AT_DIFF" ]; then
        DIFF_OUTPUT="${DIFF_OUTPUT:+$DIFF_OUTPUT
}$AT_DIFF"
      fi
    fi
  fi

  # docs/development-guide.md の一致検証
  DG_SSoT="$CLAUDE_DIR/references/guides/development-guide.md"
  DG_REPO="$repo_dir/docs/development-guide.md"
  if [ -f "$DG_SSoT" ] && [ -f "$DG_REPO" ]; then
    if ! diff -q "$DG_SSoT" "$DG_REPO" >/dev/null 2>&1; then
      DIFF_OUTPUT="${DIFF_OUTPUT:+$DIFF_OUTPUT
}Files $DG_SSoT and $DG_REPO differ"
    fi
  elif [ -f "$DG_SSoT" ] && [ ! -f "$DG_REPO" ]; then
    DIFF_OUTPUT="${DIFF_OUTPUT:+$DIFF_OUTPUT
}Only in SSoT: development-guide.md (missing in $repo_name/docs/)"
  fi

  CHECKED=$((CHECKED + 1))

  if [ -z "$DIFF_OUTPUT" ]; then
    echo "OK    $repo_name"
  else
    echo "FAIL  $repo_name"
    echo "$DIFF_OUTPUT" | sed 's/^/  /'
    ERRORS=$((ERRORS + 1))
  fi
done

echo ""
echo "--- verified: $CHECKED repos, errors: $ERRORS ---"

# 参照ファイル存在チェック（SSoT内のみ）
REF_ERRORS=0
echo ""
echo "--- reference file existence check ---"

# SKILL.md と CLAUDE.md から references/ への参照を抽出して存在確認
for f in "$CLAUDE_DIR"/CLAUDE.md "$CLAUDE_DIR"/skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  # references/xxx.md, references/xxx.yaml パターンを検出
  while IFS= read -r ref; do
    ref_file="$CLAUDE_DIR/$ref"
    if [ ! -f "$ref_file" ]; then
      rel_f="${f#"$CLAUDE_DIR"/}"
      echo "MISSING  $rel_f -> $ref"
      REF_ERRORS=$((REF_ERRORS + 1))
    fi
  done < <(grep -oP 'references/[a-zA-Z0-9_.-]+\.(md|yaml|yml)' "$f" 2>/dev/null | sort -u)
done

if [ "$REF_ERRORS" -eq 0 ]; then
  echo "OK  all references exist"
else
  echo "FAIL  $REF_ERRORS missing reference(s)"
  ERRORS=$((ERRORS + REF_ERRORS))
fi

echo ""
echo "--- total errors: $ERRORS ---"
[ "$ERRORS" -eq 0 ] || exit 1
