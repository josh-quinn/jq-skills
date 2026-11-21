# <PROJECT>: instructions for AI coding agents

The rules for every change:

1. **Small, green, Conventional Commits.** One purpose per commit, `type(scope): subject`,
   tests in the same commit, `make check` passes at every commit.
2. **Test first**, including a regression test for every bug and security fix.
3. **ADRs** in `docs/adr/` for hard-to-reverse decisions, in the same commit; keep the
   index current; supersede, never rewrite.
4. **No secrets in history.** Run `make hooks` once per clone; never use `--no-verify`.
5. **Scope and dependencies**: <what is in and out of scope; dependency policy>.
6. Ask the owner before outward-facing actions (releases, settings, publishing).

Commands: `make build`, `make test`, `make check` (everything CI runs), `make hooks`.
