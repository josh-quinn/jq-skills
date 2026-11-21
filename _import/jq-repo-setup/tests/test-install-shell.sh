#!/bin/sh
# Tests for scripts/install-shell.sh against a temporary rc file.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
export ZSHRC="$tmp/zshrc"
printf 'export A=1\n' > "$ZSHRC"
fail() { echo "FAIL $1"; exit 1; }

sh "$here/../scripts/install-shell.sh" > /dev/null
sh "$here/../scripts/install-shell.sh" > /dev/null
[ "$(grep -c '>>> git-init-prompt >>>' "$ZSHRC")" = 1 ] || fail "installs once"
grep -q 'git-init-prompt.zsh' "$ZSHRC" || fail "sources the script"
zsh -n "$ZSHRC" || fail "rc still parses"
sh "$here/../scripts/install-shell.sh" --uninstall > /dev/null
[ "$(cat "$ZSHRC")" = "$(printf 'export A=1\n')" ] || fail "uninstall leaves the rest as it was"
echo "install-shell: all passed"
