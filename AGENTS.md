# privacy-audit-skills: instructions for AI coding agents

1. **One folder per skill** at the top level, each with a `SKILL.md`. Shared material goes in
   `privacy-common/`, once; the other skills refer to it as `../privacy-common`. Don't copy it.
2. **Never write into `~/.claude/skills` or `~/.copilot/skills`.** Edit here; `make link`
   symlinks the skills there.
3. **Skills stay generic.** No user-specific names, hosts or paths in a skill: the user's trust
   lists live in their config, not in the skill.
4. **Patterns and host lists live in `privacy-common/scripts/signatures.yaml`**, not in code
   or prose. Keep it ASCII: write invisible characters as `\uXXXX` escapes so they can be
   reviewed.
5. **Test first** for `privacy.py` and `sandbox.py`: `make check` passes at every commit. Tests
   use `JQ_TOOLS_CONFIG` and `tmp_path`, never the network, Docker or the real config.
   `make sandbox-smoke` runs a real sandbox against a planted leaky package (needs Docker).
6. **Nothing under audit is ever run outside the sandbox**, and the sandbox never runs without
   the user's go-ahead. Evals use planted fixtures and stop at the report.
7. Eval workspaces (`*-workspace/`) are git-ignored. Small Conventional Commits, one purpose
   each. Ask the owner before outward-facing actions (pushing, publishing). Run `make hooks` once per
   clone (Conventional Commits on commit, gitleaks on push); decisions go in `docs/adr/`.

Config for the owner's tools lives under `~/.config/jq-tools/<tool>/`; here that's
`~/.config/jq-tools/privacy-audit/config.yaml`.
