#!/usr/bin/env zsh
# Tests for jq-repo-setup/scripts/git-init-prompt.zsh. Uses a temporary config and stub agents,
# never the real ~/.config/jq-tools or a real agent. Run: zsh tests/test-git-init-prompt.zsh
emulate -L zsh
setopt pipe_fail

here=${0:A:h}
tmp=$(mktemp -d)
trap 'rm -rf $tmp' EXIT
fails=0

# Stub agents record their arguments and working directory.
mkdir -p $tmp/bin
for a in claude copilot agy; do
  print -r -- "#!/bin/sh
{ echo \"agent=$a\"; echo \"cwd=\$(pwd -P)\"; for x in \"\$@\"; do echo \"arg=\$x\"; done; } > $tmp/called" > $tmp/bin/$a
  chmod +x $tmp/bin/$a
done
path=($tmp/bin $path)

# Fake skill folders.
for s in jq-repo-setup jq-openssf-passing; do
  mkdir -p $tmp/skills/$s && print -- "---\nname: $s\n---" > $tmp/skills/$s/SKILL.md
done

export JQ_TOOLS_CONFIG=$tmp/cfg JQ_GIT_INIT_PROMPT=always
cfg=$JQ_TOOLS_CONFIG/git-init-prompt/config.yaml
source $here/../scripts/git-init-prompt.zsh

write_cfg() {  # agent [enabled]
  mkdir -p ${cfg:h}
  print -r -- "enabled: ${2:-true}
agent: $1
skills:
  - jq-repo-setup
  - jq-openssf-passing
  - not-installed
skill_dirs:
  - $tmp/skills" > $cfg
}

ok() { print "ok   $1" }
bad() { print "FAIL $1"; (( fails++ )) || true }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi }
reset() { rm -f $tmp/called; rm -rf $tmp/r; mkdir -p $tmp/r }

# 1. First run writes a default config and leaves it alone afterwards.
reset; rm -rf $JQ_TOOLS_CONFIG
git init -q $tmp/r/a <<< "n" > /dev/null
check "default config is created" "[[ -f $cfg ]] && grep -q '^agent: ask' $cfg && grep -q 'jq-repo-setup' $cfg"
print "# mine" >> $cfg
git init -q $tmp/r/a2 <<< "n" > /dev/null
check "existing config is not rewritten" "grep -q '^# mine' $cfg"

# 2. Yes with a fixed agent starts it in the new repo with each skill's SKILL.md.
reset; write_cfg claude
out=$(git init -q $tmp/r/b <<< "y" 2>&1)
check "the question names every skill in order" '[[ $out == *"with jq-repo-setup, then jq-openssf-passing?"* ]]'
check "claude is started" "grep -q '^agent=claude' $tmp/called"
check "agent runs in the new repo" "grep -qx 'cwd=${tmp:A}/r/b' $tmp/called"
check "prompt names jq-repo-setup first, then jq-openssf-passing" \
  "grep '^arg=' $tmp/called | head -1 | grep -q 'jq-repo-setup/SKILL.md.*jq-openssf-passing/SKILL.md'"
check "skill folder is added for the agent" "grep -qx 'arg=${tmp:A}/skills' $tmp/called"
check "a skill that isn't installed is skipped and reported" '[[ $out == *not-installed* ]] && ! grep -q not-installed/SKILL $tmp/called'

# 3. No means nothing is started; git's result is kept.
reset; write_cfg claude
git init -q $tmp/r/c <<< "n" > /dev/null; rc=$?
check "no starts nothing" "[[ ! -e $tmp/called && $rc -eq 0 && -d $tmp/r/c/.git ]]"

# 4. agent: ask offers the installed agents.
reset; write_cfg ask
git init -q $tmp/r/d <<< $'y\n2' > /dev/null
check "ask: choice 2 starts copilot interactively" "grep -q '^agent=copilot' $tmp/called && grep -qx 'arg=-i' $tmp/called"
reset; write_cfg ask
git init -q $tmp/r/e <<< $'y\n3' > /dev/null
check "ask: choice 3 starts antigravity interactively" "grep -q '^agent=agy' $tmp/called && grep -qx 'arg=-i' $tmp/called"
reset; write_cfg ask
git init -q $tmp/r/f <<< $'y\n' > /dev/null
check "ask: Enter picks claude" "grep -q '^agent=claude' $tmp/called"

# 5. No prompt where there's nothing new to set up.
reset; write_cfg claude
git init -q --bare $tmp/r/h.git <<< "y" > /dev/null
check "bare repos don't prompt" "[[ ! -e $tmp/called ]]"
write_cfg claude false
git init -q $tmp/r/i <<< "y" > /dev/null
check "enabled: false turns it off" "[[ ! -e $tmp/called ]]"
write_cfg claude
JQ_GIT_INIT_PROMPT=off git init -q $tmp/r/j <<< "y" > /dev/null
check "JQ_GIT_INIT_PROMPT=off turns it off" "[[ ! -e $tmp/called ]]"
JQ_GIT_INIT_PROMPT= git init -q $tmp/r/k <<< "y" > /dev/null
check "no prompt without a terminal" "[[ ! -e $tmp/called ]]"

# 6. Where the new repo is.
reset; write_cfg claude; mkdir -p $tmp/r/base
git -C $tmp/r/base init -q -b trunk sub <<< "y" > /dev/null
check "-C dir and option values are followed to the new repo" "grep -qx 'cwd=${tmp:A}/r/base/sub' $tmp/called"
reset; write_cfg claude; mkdir -p $tmp/r/here
(cd $tmp/r/here && git init -q <<< "y" > /dev/null)
check "no directory means the current one" "grep -qx 'cwd=${tmp:A}/r/here' $tmp/called"

# 7. Other git commands and failures pass straight through.
reset; write_cfg claude
git --version > /dev/null; rc=$?
check "other commands pass through" "[[ $rc -eq 0 && ! -e $tmp/called ]]"
print -n > $tmp/r/file
git init -q $tmp/r/file <<< "y" > /dev/null 2>&1; rc=$?
check "a failed init keeps git's exit code and doesn't prompt" "[[ $rc -ne 0 && ! -e $tmp/called ]]"

# 8. Re-init: no record is treated as an existing repo to set up; with a record, the check runs.
reset; write_cfg claude
git init -q $tmp/r/g <<< "n" > /dev/null
out=$(git init -q $tmp/r/g <<< "y" 2>&1)
check "re-init without a record says so and offers setup" '[[ $out == *"No setup record"* ]]'
check "  ...and the agent is told it's an existing repo" "grep -q '^arg=This is an existing git repository' $tmp/called"

reset; write_cfg claude
git init -q $tmp/r/m <<< "n" > /dev/null
mkdir -p $tmp/r/m/.github && print "schema: 1" > $tmp/r/m/.github/repo-setup.yaml
_gip_check() { print "PASS everything"; return 0 }
out=$(git init -q $tmp/r/m <<< "y" 2>&1)
check "record + passing check: report, no question, no agent" \
  '[[ $out == *"PASS everything"* && $out == *"nothing to do"* && $out != *"[y/N]"* && ! -e $tmp/called ]]'

_gip_check() { print "FAIL hooks  missing .githooks/pre-push"; return 1 }
out=$(git init -q $tmp/r/m <<< "n" 2>&1)
check "record + failing check: asks to fix" '[[ $out == *"Fix the failed checks"* && ! -e $tmp/called ]]'
git init -q $tmp/r/m <<< "y" > /dev/null 2>&1
check "  ...and yes gives the agent the failures" "grep -q 'arg=.*FAIL hooks  missing .githooks/pre-push.*fix only what failed' $tmp/called"

_gip_check() { print "boom"; return 3 }
out=$(git init -q $tmp/r/m <<< "y" 2>&1); rc=$?
check "a check that can't run is reported, git still succeeds" '[[ $rc -eq 0 && $out == *"exit 3"* ]]'

# Agent shells keep the `git` function but drop helpers that start with an underscore: git
# must still run, silently.
out=$( unfunction _gip_target; git --version 2>&1 ); rc=$?
check "git still works, silently, when the helpers are missing" '[[ $rc -eq 0 && $out == "git version"* ]]'

print
(( fails == 0 )) && print "all passed" || { print "$fails failed"; exit 1 }
