# OpenSSF badge skills

Agent skills (Claude Code, GitHub Copilot) that take a project to the
[OpenSSF Best Practices](https://www.bestpractices.dev) badges, honestly: every answer is
checked against the repository, and nothing is submitted without the owner's go-ahead.

| Skill | Status | Does |
|---|---|---|
| [`openssf-passing`](openssf-passing/SKILL.md) | draft | The passing badge |
| `openssf-silver` | planned | Silver, building on passing |
| `openssf-gold` | planned | Gold; mostly explains what a solo project can't meet |
| `openssf-baseline` | planned | OSPS Baseline levels 1 to 3 |
| [`openssf-common`](openssf-common/SKILL.md) | shared | The parts every level uses: live criteria, answers checker, proposal URLs, form fallback, workflow and honesty rules |

Each level skill reads `openssf-common` from beside its own folder, so install them together.

## How a run goes

1. **Assess**: fetch the criteria live, read the repo, and write a gap table. Pause for the
   owner's decisions.
2. **Change the repo**: the agreed fixes, on a branch, as a pull request.
3. **Answer**: an `answers.yaml` with evidence for every Met, checked by `badge.py check`.
   Pause for the go-ahead.
4. **Propose**: bestpractices.dev
   [automation proposal URLs](https://github.com/ossf/best-practices-badge/blob/main/docs/automation-proposals.md)
   open the form with the answers filled in for review; a person saves.

Work folders (gap table, answers, criteria snapshot) go to `~/development/openssf-badges/<project>/<level>/`
by default. Change `data_dir` in `~/.config/jq-tools/openssf-badge-skills/config.yaml`.

## Install

```sh
make link     # symlinks each skill into ~/.claude/skills and ~/.copilot/skills
make unlink   # removes those links
```

The script never overwrites a folder or a link it didn't make. Requires `uv` (or Python 3 with
PyYAML) and, for most checks, an authenticated `gh`.

## Develop

```sh
make check    # helper tests and basic skill checks
```

Skill evals live in each skill's `evals/` folder (the `claude plugin eval` layout). They stop
before the site, so they never submit anything. `handoff/` holds the notes and the worked
example (fu, project 16725) these skills were designed from.
