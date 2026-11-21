# jq-repo-setup

The `jq-repo-setup` agent skill: set up or harden a repository with professional engineering,
security and supply-chain practices using free and open-source tooling.

    make link            # symlink the skill into ~/.claude/skills and ~/.copilot/skills
    make unlink          # remove those links
    make check           # tests and syntax checks

## Asked after every `git init`

Git has no hook that runs on `git init`, so this is a small zsh wrapper around `git`. It only
speaks up in an interactive terminal, so scripts and agents' own shells never see it.

- **New repo**: asks whether to set it up, and with which agent, then starts that agent in the
  repo with a prompt to follow each skill's `SKILL.md` in turn:

      Set up myproject with jq-repo-setup, then openssf-passing? [y/N]
      Which agent?  1) Claude Code  2) Copilot CLI  3) Antigravity  [1]

- **Re-init** (git says "Reinitialized existing Git repository"):
  - no `.github/repo-setup.yaml`: the same offer, with the agent told it's an existing repo;
  - with one: runs the setup check. If everything passes it says so and stops. If something
    fails it asks "Fix the failed checks…?" and gives the agent only those failures.

    make install-shell     # add one marked block to ~/.zshrc that sources the wrapper
    make uninstall-shell   # remove the block

Settings are in `~/.config/jq-tools/git-init-prompt/config.yaml`, written on first use and never
rewritten: `enabled`, `agent` (`claude`, `copilot`, `antigravity` or `ask`), the `skills` to run
in order, and the `skill_dirs` to find them in. `JQ_GIT_INIT_PROMPT=off git init` skips it once.

## The setup record and the check

jq-repo-setup writes `.github/repo-setup.yaml` in each repo it sets up: the answers it was given
(visibility, project type, team), the target, the controls skipped and why, and, from the
openssf-* skills, the badge's project id and level. Agents read it instead of asking again.

The record says what was decided; `check-setup.py` says what is true now, so nothing is ever
skipped on the record's word. Run it any time (it changes nothing):

    uv run --no-project --with pyyaml python -I jq-repo-setup/scripts/check-setup.py <repo>

It checks the foundation files, template placeholders, git hooks, a `check` target, CI on pull
requests, workflow permissions and SHA pinning, Dependabot or Renovate, lockfiles, gitleaks, the
GitHub ruleset and security settings (via `gh`), and the recorded badge level on
bestpractices.dev. Exit 0 all pass, 1 something failed, 2 no record; `--json` for agents,
`--offline` to skip GitHub and the badge.
