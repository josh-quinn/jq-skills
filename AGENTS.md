# jq-skills: instructions for AI coding agents

One repo for all the owner's agent skills. Each skill is a top-level folder with a `SKILL.md`.

1. **One folder per skill** at the top level. Shared material goes in a `*-common/` folder,
   once (`jq-privacy-common/`, `jq-openssf-common/`); the skills that use it refer to it as
   `../<name>-common`. Don't copy it.
2. **Never write into `~/.claude/skills` or `~/.copilot/skills`.** Edit here; `make link`
   symlinks the skills there.
3. **Skills stay generic.** No user-specific names, commit rules, hosts or paths in a skill:
   the user's settings live in their config, and skills defer to the target repo's rules and
   the user's own instructions.
4. **`make check` passes at every commit.** Tests sit beside the code (`<skill>/tests/`), use
   `TOOLS_CONFIG` and `tmp_path`, and never touch the network, Docker or the real config.
   Write the test first for `privacy.py`, `sandbox.py`, `badge.py` and `check-setup.py`.
5. **Small Conventional Commits, one purpose each.** Ask the owner before outward-facing
   actions (pushing, publishing, anything on bestpractices.dev). Run `make hooks` once per
   clone (Conventional Commits on commit, gitleaks on push); decisions go in `docs/adr/`.
6. Eval workspaces (`*-workspace/`) are git-ignored. Evals use planted fixtures and stop at
   the report; they never touch real services.

## jq-privacy-audit, jq-privacy-sandbox, jq-privacy-common

- Patterns and host lists live in `jq-privacy-common/scripts/signatures.yaml`, not in code or
  prose. Keep it ASCII: write invisible characters as `\uXXXX` escapes so they can be reviewed.
- `make sandbox-smoke` runs a real sandbox against a planted leaky package (needs Docker).
- Nothing under audit is ever run outside the sandbox, and the sandbox never runs without the
  user's go-ahead.

## jq-openssf-common, jq-openssf-passing

- Criteria are read live (`jq-openssf-common/scripts/badge.py`). Don't hard-code criterion lists
  or counts into a skill as facts.
- Evals never touch bestpractices.dev: they stop at the gap table, repo changes and
  `answers.yaml`.
- Background and lessons from the first manual run: `docs/openssf-handoff/HANDOFF.md`.

## jq-repo-setup

- The skill's own tests are in `jq-repo-setup/tests/`. The git-init prompt (a zsh wrapper
  around `git`) is `jq-repo-setup/scripts/git-init-prompt.zsh`; `make install-shell` adds it to
  `~/.zshrc`. See `docs/jq-repo-setup.md`.

Config for the owner's tools lives under `~/.config/jq-tools/<tool>/`: `privacy-audit`,
`openssf-badge-skills` and `git-init-prompt` each have a `config.yaml` there.
