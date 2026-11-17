# jq-repo-setup: instructions for AI coding agents

1. The skill is the `jq-repo-setup/` folder. **Never write into `~/.claude/skills` or
   `~/.copilot/skills`**: edit here; `make link` symlinks the skill there.
2. The skill stays generic: no user-specific names, commit rules or paths in it.
3. `make check` passes at every commit.
4. Small Conventional Commits, one purpose each. Ask the owner before outward-facing actions
   (pushing, publishing).

Config for the owner's tools lives under `~/.config/jq-tools/<tool>/`; the git-init prompt's is
`~/.config/jq-tools/git-init-prompt/config.yaml`.
