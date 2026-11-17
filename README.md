# jq-repo-setup

The `jq-repo-setup` agent skill: set up or harden a repository with professional engineering,
security and supply-chain practices using free and open-source tooling.

    make link            # symlink the skill into ~/.claude/skills and ~/.copilot/skills
    make unlink          # remove those links
    make check           # tests and syntax checks

## Asked after every `git init`

Git has no hook that runs on `git init`, so this is a small zsh wrapper around `git`. After a
`git init` that creates a new work tree in an interactive terminal, it asks:

    Set up myproject with jq-repo-setup, then openssf-passing? [y/N]
    Which agent?  1) Claude Code  2) Copilot CLI  3) Antigravity  [1]

and starts that agent in the new repo with a prompt to follow each skill's `SKILL.md` in turn.
It stays quiet for re-inits, bare repos, other git commands, scripts and agents' own shells.

    make install-shell     # add one marked block to ~/.zshrc that sources the wrapper
    make uninstall-shell   # remove the block

Settings are in `~/.config/jq-tools/git-init-prompt/config.yaml`, written on first use and never
rewritten: `enabled`, `agent` (`claude`, `copilot`, `antigravity` or `ask`), the `skills` to run
in order, and the `skill_dirs` to find them in. `JQ_GIT_INIT_PROMPT=off git init` skips it once.
