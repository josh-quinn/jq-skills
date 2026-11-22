---
name: jq-openssf-common
description: Shared scripts and reference used by the jq-openssf-passing, jq-openssf-silver, jq-openssf-gold and jq-openssf-baseline skills (OpenSSF Best Practices badges on bestpractices.dev). It holds the live criteria fetcher, the answers checker, the proposal-URL builder, the form-filling fallback, and the workflow and honesty rules. Read it when one of those skills points here; for badge work itself, use the level skill (start with jq-openssf-passing).
---

# OpenSSF badge skills: shared parts

This folder supports the level skills. On its own it doesn't take a project anywhere. If you
arrived here directly, use `jq-openssf-passing` (or the level the user asked for) and come back
when it points here.

## What's here

| Path | Use it for |
|---|---|
| `references/workflow.md` | The phases and pauses every level follows, and the `answers.yaml` format. Read it at the start. |
| `references/honesty.md` | What may be claimed and how to back it. Read it at the start. |
| `references/site.md` | Criteria sources, project JSON, proposal URLs, form mechanics, the site's automation, and Claude in Chrome caveats. Read it before phase 4, or when the site surprises you. |
| `scripts/badge.py` | Helper: `config`, `init`, `list`, `gaps`, `answers`, `check`, `urls`, `payload`, `project`. Run `--help` on any command. |
| `scripts/fill-form.js` | Fallback filler for the edit form, for when proposal URLs don't work. |
| `tests/` | The helper's tests: `uv run --no-project --with pyyaml --with pytest pytest <this folder>/tests` |

Run the helper as `uv run --no-project --with pyyaml python -I <this folder>/scripts/badge.py <command>`.

## Settings

`~/.config/jq-tools/openssf-badge-skills/config.yaml` is created with defaults on first run and
never rewritten. `data_dir` sets where the work folders go (default
`~/development/openssf-badges`), and `max_url_length` sets where proposal URLs are split. Set
`TOOLS_CONFIG` to another root to keep tests away from the real settings, and
`OPENSSF_BADGES_DATA_DIR` to override `data_dir` for one run (dry runs, tests).
