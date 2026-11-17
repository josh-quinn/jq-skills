#!/bin/sh
# Link (or unlink) every skill in this repo into the agents' skill folders.
# Skills are linked, never copied: edit them here and every agent sees the change.
#
#   scripts/link-skills.sh          link
#   scripts/link-skills.sh --unlink remove the links that point into this repo
#
# SKILL_DIRS overrides the target folders (space-separated), e.g. for tests.
set -eu

repo=$(cd "$(dirname "$0")/.." && pwd -P)
targets=${SKILL_DIRS:-"$HOME/.claude/skills $HOME/.copilot/skills"}
mode=${1:-link}

for target in $targets; do
  if [ ! -d "$(dirname "$target")" ]; then
    echo "skip $target (no $(dirname "$target"))"
    continue
  fi
  mkdir -p "$target"
  for skill_md in "$repo"/*/SKILL.md; do
    src=$(dirname "$skill_md")
    name=$(basename "$src")
    dest="$target/$name"
    if [ "$mode" = "--unlink" ]; then
      if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
        rm "$dest" && echo "unlinked $dest"
      fi
      continue
    fi
    if [ -L "$dest" ]; then
      if [ "$(readlink "$dest")" = "$src" ]; then
        echo "ok       $dest"
      else
        echo "SKIP     $dest links to $(readlink "$dest"), not this repo" >&2
      fi
    elif [ -e "$dest" ]; then
      echo "SKIP     $dest exists and is not a link; move it aside first" >&2
    else
      ln -s "$src" "$dest" && echo "linked   $dest -> $src"
    fi
  done
done
