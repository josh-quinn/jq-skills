# OpenSSF badge skills

Agent skills (Claude Code, GitHub Copilot) that take a project to the
[OpenSSF Best Practices](https://www.bestpractices.dev) badges, honestly: every answer is
checked against the repository, and nothing is submitted without the owner's go-ahead.

| Skill | Status | Does |
|---|---|---|
| [`openssf-passing`](openssf-passing/SKILL.md) | tested | The passing badge |
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

## Verification (2026-11-21)

- **Dry run on a real repo** (this one, up to `answers.yaml` passing `badge check`, nothing sent to
  bestpractices.dev): the skill worked as written; the gaps it found in the instructions and the
  helper are fixed.
- **Evals**, one run each, with the skill: `planted-gaps` 0.92, `fu-v0-1-0` 0.92,
  `two-maintainers` 0.82. Every failed grader is a judge verdict on "every Met answer is backed"
  (or its URL twin), which `badge check` already enforces mechanically and whose recorded evidence
  was specific and complete. Treat them as the judge, not the skill, until a stronger judge
  (`--judge-model`) says otherwise.
- Not yet run: the no-skill baseline arm since the helper changes, and silver, gold and baseline
  (they don't exist yet).

### Running the evals

The skills read `openssf-common` from beside their own folder, so evaluate a **plugin** that holds
both, not the skill folder alone (its sandbox can't see the sibling). Build a throwaway copy:

```sh
P=$(mktemp -d); mkdir -p $P/.claude-plugin $P/evals
cp -R openssf-common openssf-passing $P/ && cp -R openssf-passing/evals/* $P/evals/ && rm -rf $P/openssf-passing/evals
echo '{"name":"openssf-badges","version":"0.1.0","description":"eval copy","skills":["./openssf-common","./openssf-passing"]}' > $P/.claude-plugin/plugin.json
cd $P && claude plugin eval . --runs 1 --ablation none --scaffold --trust-plugin --no-publish -j 3 \
  --max-cost-usd 20 --allow-tools Bash Write Edit "WebFetch(domain:pypi.org)" \
  "WebFetch(domain:files.pythonhosted.org)" "WebFetch(domain:api.github.com)" \
  "WebFetch(domain:raw.githubusercontent.com)"
```

- The run's sandbox blocks the network unless hosts are granted like this. Without them the skill
  stops, correctly, because it won't answer from remembered criteria. Never grant
  bestpractices.dev: evals must not touch it.
- `--no-publish` keeps the report off claude.ai. A full run is about 12 minutes and $5 to $6.

