# git-init-prompt: after you run `git init` in an interactive zsh, offer to set the repository up
# with agent skills (jq-repo-setup first, then any others listed in the config), in Claude Code,
# Copilot CLI or Antigravity. Git has no hook that runs on init, so this wraps the `git` command.
#
#   new repo                         ask, then start the agent with the skills
#   re-init, no .github/repo-setup.yaml   the same, told it's an existing repo
#   re-init, with that setup record   run check-setup.py; offer an agent only if something fails
#
# Source it from ~/.zshrc (scripts/install-shell.sh does that). Settings:
#   ${JQ_TOOLS_CONFIG:-~/.config/jq-tools}/git-init-prompt/config.yaml (written on first use)
#   JQ_GIT_INIT_PROMPT=off   don't ask (e.g. for one command: JQ_GIT_INIT_PROMPT=off git init)

_gip_skill_home=${${(%):-%x}:A:h:h}   # this skill's folder, through any symlink

_gip_config() {
  print -r -- "${JQ_TOOLS_CONFIG:-$HOME/.config/jq-tools}/git-init-prompt/config.yaml"
}

_gip_write_default() {
  emulate -L zsh; setopt extended_glob
  local cfg=$1
  mkdir -p ${cfg:h} || return
  print -r -- "# git-init-prompt (from the jq-repo-setup skill): asked after each \`git init\` you type.
enabled: true
# Which agent to start: claude, copilot, antigravity, or ask.
agent: ask
# Skills to run, in order, by folder name. Each is looked up in skill_dirs; missing ones are skipped.
skills:
  - jq-repo-setup
  - openssf-passing
skill_dirs:
  - ~/.claude/skills
  - ~/.copilot/skills" > $cfg
}

# _gip_read <file> <key>: a scalar value, or a list's items one per line (a small YAML subset).
_gip_read() {
  emulate -L zsh; setopt extended_glob
  local line key=$2 in_list=0
  while IFS= read -r line; do
    line=${line%%[[:space:]]#}
    if (( in_list )); then
      if [[ $line == [[:space:]]##-[[:space:]]* ]]; then
        print -r -- "${${line#*-}##[[:space:]]#}"
        continue
      fi
      [[ -z $line || $line == [[:space:]]#\#* ]] && continue
      return 0
    fi
    if [[ $line == "$key:"* ]]; then
      local val=${${line#$key:}##[[:space:]]#}
      if [[ -n $val ]]; then print -r -- $val; return 0; fi
      in_list=1
    fi
  done < $1
}

# _gip_target <git args...>: the work tree `git init` will create, or nothing if it isn't an init
# with a work tree.
_gip_target() {
  emulate -L zsh; setopt extended_glob
  local base=$PWD dir= a init=0
  while (( $# )); do
    case $1 in
      -C) base=${2:-}; [[ $base == /* ]] || base=$PWD/$base; shift 2 ;;
      -c|--git-dir|--work-tree|--namespace|--exec-path) shift 2 ;;
      -*) shift ;;
      init) init=1; shift; break ;;
      *) return 1 ;;
    esac
  done
  (( init )) || return 1
  while (( $# )); do
    a=$1; shift
    case $a in
      --bare) return 1 ;;
      --template|--separate-git-dir|-b|--initial-branch|--object-format|--ref-format) shift ;;
      --) [[ -n ${1:-} ]] && dir=$1; break ;;
      -*) ;;
      *) [[ -z $dir ]] && dir=$a ;;
    esac
  done
  [[ -z $dir ]] && dir=.
  [[ $dir == /* ]] || dir=$base/$dir
  print -r -- ${dir:a}
}

git() {
  # Some shells (agents' snapshots) keep this function but not the helpers beside it.
  (( $+functions[_gip_target] )) || { command git "$@"; return }
  local target existed=0 rc
  if target=$(_gip_target "$@") && [[ -n $target ]]; then
    [[ -e $target/.git ]] && existed=1
  else
    target=
  fi
  command git "$@"; rc=$?
  if [[ -n $target && $rc -eq 0 && -d $target/.git ]]; then
    if (( existed )); then _gip_review $target; else _gip_offer $target new; fi
  fi
  return $rc
}

# _gip_check <repo>: the read-only setup check (scripts/check-setup.py).
_gip_check() {
  local script=$_gip_skill_home/scripts/check-setup.py
  if (( $+commands[uv] )); then
    command uv run -q --no-project --with pyyaml python -I $script $1
  else
    command python3 -I $script $1
  fi
}

_gip_allowed() {
  case ${JQ_GIT_INIT_PROMPT:-} in
    off|0|no) return 1 ;;
    always) ;;
    *) [[ -o interactive && -t 0 && -t 1 ]] || return 1 ;;
  esac
  local cfg=$(_gip_config)
  [[ -f $cfg ]] || _gip_write_default $cfg || return 1
  [[ $(_gip_read $cfg enabled) != false ]]
}

# A re-init: check a repo that has a setup record; treat one without as unset-up.
_gip_review() {
  emulate -L zsh
  local target=$1 report rc
  _gip_allowed || return 0
  if [[ ! -f $target/.github/repo-setup.yaml ]]; then
    print "No setup record (.github/repo-setup.yaml) in ${target:t}."
    _gip_offer $target existing
    return
  fi
  print "Checking ${target:t} against its setup record..."
  report=$(_gip_check $target 2>&1); rc=$?
  print -r -- $report
  case $rc in
    0) print "Still up to standard; nothing to do." ;;
    1) _gip_offer $target failed $report ;;
    *) print -u2 "git-init-prompt: the check couldn't run (exit $rc)" ;;
  esac
}

# _gip_offer <repo> <new|existing|failed> [report]
_gip_offer() {
  emulate -L zsh; setopt extended_glob
  local target=$1 mode=$2 report=${3:-} cfg agent reply d s skill_dirs skills found missing prompt i
  _gip_allowed || return 0
  cfg=$(_gip_config)

  skill_dirs=(${(f)"$(_gip_read $cfg skill_dirs)"})
  skill_dirs=(${skill_dirs/#\~/$HOME})
  skills=(${(f)"$(_gip_read $cfg skills)"})
  found=() missing=()
  for s in $skills; do
    d=
    for i in $skill_dirs; do
      [[ -f $i/$s/SKILL.md ]] && { d=${i:A}/$s; break; }
    done
    if [[ -n $d ]]; then found+=($d); else missing+=($s); fi
  done
  (( ${#missing} )) && print -u2 "git-init-prompt: skipping skills not found in skill_dirs: ${(j:, :)missing}"
  (( ${#found} )) || return 0

  local -a names=(${found:t})
  if [[ $mode == failed ]]; then
    print -n "Fix the failed checks with ${(j:, then :)names}? [y/N] "
  else
    print -n "Set up ${target:t} with ${(j:, then :)names}? [y/N] "
  fi
  read -r reply || return 0
  [[ $reply == [yY]* ]] || return 0

  agent=$(_gip_read $cfg agent)
  if [[ -z $agent || $agent == ask ]]; then
    print "Which agent?  1) Claude Code  2) Copilot CLI  3) Antigravity  [1] "
    read -r reply || return 0
    case ${reply:-1} in 1) agent=claude ;; 2) agent=copilot ;; 3) agent=antigravity ;; *) return 0 ;; esac
  fi

  case $mode in
    new) prompt="This is a new git repository." ;;
    existing) prompt="This is an existing git repository with no setup record (.github/repo-setup.yaml). Assess what is already in place before changing anything." ;;
    failed) prompt="This repository was set up before; .github/repo-setup.yaml records the answers. check-setup.py reports these results: <<< $report >>> Confirm the recorded answers still hold, then fix only what failed." ;;
  esac
  prompt+=" Use these skills in order, reading each skill's SKILL.md and following it:"
  i=1
  for d in $found; do prompt+=" $i. ${d:t} ($d/SKILL.md)."; (( i++ )); done
  [[ $mode == failed ]] || prompt+=" Start by asking me what you need to know about the project."

  local -a dirs=(${(u)found:h})
  (
    cd $target || exit
    case $agent in
      claude) command claude $prompt ${dirs:+--add-dir} $dirs ;;
      copilot) command copilot ${${dirs/#/--add-dir=}} -i $prompt ;;
      antigravity) command agy ${${dirs/#/--add-dir=}} -i $prompt ;;
      *) print -u2 "git-init-prompt: unknown agent '$agent' in $cfg" ;;
    esac
  )
}
