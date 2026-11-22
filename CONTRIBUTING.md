# Contributing

Security problems: report them privately as described in [SECURITY.md](SECURITY.md).
Rules for coding agents are in [AGENTS.md](AGENTS.md).

## Ground rules

- **New functionality gets tests** in the same change, added to the automated suite that
  `make check` runs. **Test first** for `privacy.py`, `sandbox.py`, `badge.py` and `check-setup.py`. Tests use `TOOLS_CONFIG` and
  `tmp_path`, never the network, Docker or the real config.
- **Small, single-purpose commits** written as [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat(jq-privacy-audit): ...`, `fix(jq-privacy-common): ...`). A `commit-msg` hook and CI enforce this.
- **Decisions** that are hard to reverse get an ADR in [`docs/adr/`](docs/adr) in the same change.
- **Skills stay generic** and shared material lives once in `jq-privacy-common/`.
- **Never write into `~/.claude/skills`**; use `make link`.

## Getting started

```sh
brew install uv gitleaks shellcheck
make hooks    # once per clone: commit messages checked, pushes scanned for secrets
make check    # everything CI runs
```

If the pre-push scan blocks you, remove the secret from **history** (amend or rebase) and
rotate the credential. Record genuine false positives by fingerprint in `.gitleaksignore`.
