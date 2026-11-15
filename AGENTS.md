# openssf-badge-skills: instructions for AI coding agents

1. **One folder per skill** at the top level, each with a `SKILL.md`. Shared material goes in
   `openssf-common/`, once; level skills refer to it as `../openssf-common`. Don't copy it into
   a level skill.
2. **Never write into `~/.claude/skills` or `~/.copilot/skills`.** Edit here; `make link`
   symlinks the skills there.
3. **Skills stay generic.** No user-specific commit rules, names or paths in a skill: they defer
   to the target repo's rules and the user's own instructions.
4. **Criteria are read live** (`openssf-common/scripts/badge.py`). Don't hard-code criterion
   lists or counts into a skill as facts.
5. **Test first** for `badge.py`: `make check` passes at every commit. Tests use
   `JQ_TOOLS_CONFIG` and fixtures, never the network or the real config.
6. **Evals never touch bestpractices.dev.** They stop at the gap table, repo changes and
   `answers.yaml`. Eval workspaces (`*-workspace/`) are git-ignored.
7. Small Conventional Commits, one purpose each. Ask the owner before outward-facing actions
   (pushing, publishing, anything on bestpractices.dev).

Config for the owner's tools lives under `~/.config/jq-tools/<tool>/`; here that's
`~/.config/jq-tools/openssf-badge-skills/config.yaml`.
