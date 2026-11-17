# git-init-prompt: after you run `git init` in an interactive zsh, offer to set the new repository
# up with agent skills (jq-repo-setup first, then any others listed in the config), in Claude Code,
# Copilot CLI or Antigravity. Git has no hook that runs on init, so this wraps the `git` command.
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
  local target existed=0 rc
  if target=$(_gip_target "$@") && [[ -n $target ]]; then
    [[ -e $target/.git ]] && existed=1
  else
    target=
  fi
  command git "$@"; rc=$?
  if [[ -n $target && $rc -eq 0 && $existed -eq 0 && -d $target/.git ]]; then
    _gip_offer $target
  fi
  return $rc
}

_gip_offer() {
  emulate -L zsh; setopt extended_glob
  local target=$1 cfg=$(_gip_config) agent reply d s skill_dirs skills found missing prompt i
  case ${JQ_GIT_INIT_PROMPT:-} in
    off|0|no) return 0 ;;
    always) ;;
    *) [[ -o interactive && -t 0 && -t 1 ]] || return 0 ;;
  esac
  [[ -f $cfg ]] || _gip_write_default $cfg || return 0
  [[ $(_gip_read $cfg enabled) == false ]] && return 0

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

  print -n "Set up ${target:t} with ${(j:, then :)${found:t}}? [y/N] "
  read -r reply || return 0
  [[ $reply == [yY]* ]] || return 0

  agent=$(_gip_read $cfg agent)
  if [[ -z $agent || $agent == ask ]]; then
    print "Which agent?  1) Claude Code  2) Copilot CLI  3) Antigravity  [1] "
    read -r reply || return 0
    case ${reply:-1} in 1) agent=claude ;; 2) agent=copilot ;; 3) agent=antigravity ;; *) return 0 ;; esac
  fi

  prompt="This is a new git repository. Use these skills in order, reading each skill's SKILL.md and following it:"
  i=1
  for d in $found; do prompt+=" $i. ${d:t} ($d/SKILL.md)."; (( i++ )); done
  prompt+=" Start by asking me what you need to know about the project."

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
