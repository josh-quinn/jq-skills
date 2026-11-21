#!/bin/sh
# Add (or remove) the git-init prompt to your zsh startup file: one marked block that sources
# jq-repo-setup/scripts/git-init-prompt.zsh from this repo. Nothing else in the file is touched.
#
#   scripts/install-shell.sh              add the block (does nothing if it's already there)
#   scripts/install-shell.sh --uninstall  remove the block
#
# ZSHRC overrides the file, e.g. for tests.
set -eu

repo=$(cd "$(dirname "$0")/.." && pwd -P)
rc=${ZSHRC:-$HOME/.zshrc}
begin='# >>> git-init-prompt >>>'
end='# <<< git-init-prompt <<<'
script="$repo/jq-repo-setup/scripts/git-init-prompt.zsh"

if [ "${1:-}" = "--uninstall" ]; then
  [ -f "$rc" ] || exit 0
  if grep -qxF "$begin" "$rc"; then
    tmp=$(mktemp)
    awk -v b="$begin" -v e="$end" '$0==b{skip=1} !skip{print} $0==e{skip=0}' "$rc" > "$tmp"
    cat "$tmp" > "$rc" && rm -f "$tmp"
    echo "removed the git-init-prompt block from $rc"
  fi
  exit 0
fi

if [ -f "$rc" ] && grep -qxF "$begin" "$rc"; then
  echo "ok       $rc already sources git-init-prompt"
  exit 0
fi
cat >> "$rc" <<BLOCK

$begin
# After \`git init\`, offer to set the repo up with agent skills (jq-repo-setup skill).
[ -f "$script" ] && source "$script"
$end
BLOCK
echo "added    git-init-prompt to $rc (open a new terminal, or: source $rc)"
