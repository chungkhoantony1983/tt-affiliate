#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

# Sync .claude/skills into Codex's local skills directory, cleaning stale links.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
skill_src="${SKILL_SRC:-$repo_root/.claude/skills}"
codex_home="${CODEX_HOME:-$HOME/.codex}"
dest="$codex_home/skills/local"

if [[ ! -d "$skill_src" ]]; then
  echo "Skill source directory not found: $skill_src" >&2
  exit 1
fi

mkdir -p "$dest"

for link in "$dest"/*; do
  [[ -L "$link" ]] || continue
  target="$(readlink "$link")"
  # Remove stale links (different source tree or broken)
  if [[ "$target" != "$skill_src"/* || ! -e "$link" ]]; then
    rm "$link"
  fi
done

for dir in "$skill_src"/*; do
  [[ -d "$dir" ]] || continue
  name="$(basename "$dir")"
  dest_link="$dest/$name"
  if [[ -e "$dest_link" && ! -L "$dest_link" ]]; then
    echo "Skipping $name: $dest_link exists and is not a symlink" >&2
    continue
  fi
  ln -sfn "$dir" "$dest_link"
done

echo "Synced skills from $skill_src into $dest"
