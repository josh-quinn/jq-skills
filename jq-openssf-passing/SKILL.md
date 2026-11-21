---
name: jq-openssf-passing
description: Take a software project to the OpenSSF Best Practices "passing" badge on bestpractices.dev (formerly the CII Best Practices badge). Reads the criteria live, assesses the repository against every one, makes the missing fixes on a branch, drafts honest evidence-backed answers, and proposes them on the site for the user to review and save. Use this whenever someone wants an OpenSSF or CII best practices badge, asks what their repo needs for the passing level, wants to fill in or update the bestpractices.dev questionnaire, or says "get us the best practices badge", even if they don't say "passing". Not for OpenSSF Scorecard, and not for general repo hardening without the badge (that's jq-repo-setup); silver, gold and OSPS Baseline have their own skills, and passing comes first.
---

# OpenSSF Best Practices: passing

Passing is the first level of the badge, and silver and gold require it. Most of it is about
whether the project is honest and usable in public: someone can find out what it does, get it,
report a bug or a vulnerability privately, see that tests and analysis run, and trust that
releases aren't tampered with. A well-set-up repository is often close already. The work is to
prove each criterion with evidence, fix the few real gaps, and answer the form truthfully.

## Before you start

The shared parts sit beside this skill's folder, at `<this skill's directory>/../jq-openssf-common`.
If that folder is missing, tell the user to link it (the skills repo's `make link`) and stop.
Read these two files now, because they are the procedure and its limits:

- `jq-openssf-common/references/workflow.md`: the phases, the two pauses, and the answers format
- `jq-openssf-common/references/honesty.md`: what may be claimed and how to back it

Then follow the workflow with level `passing`, using this file's notes. In short:

1. **Set up**: `badge.py init --project <name> --level passing --repo-url <url>`. Read the
   repository's own contribution and commit rules.
2. **Assess**: `badge.py list ... --level passing --details`. Check every criterion against
   the repository, run the tests and checks, and fill in `gaps.md`, using
   `references/passing.md` for per-criterion pitfalls. **Pause 1**: the Ask questions, the
   fixes to make, and permission to branch, push and open a PR.
3. **Change the repo**: only the agreed fixes, following the repository's rules, as a PR.
4. **Answer**: write `answers.yaml`, then `badge.py check` until it has no errors.
   **Pause 2**: the go-ahead to propose on bestpractices.dev.
5. **Propose and save**: read `jq-openssf-common/references/site.md` first. Build proposal URLs
   with `badge.py urls`, then the user (or you, if they said so) reviews and saves. Refresh the
   project JSON and report what stuck.

## What matters most at passing

- **Criteria are read live, never from memory.** At the time of writing passing had 67
  criteria (43 MUST, 10 SHOULD, 14 SUGGESTED), but trust `badge.py`'s count, not this one.
- **Every MUST must be Met or N/A** for the badge. SHOULD and SUGGESTED can stay Unmet with an
  honest justification and the badge is still earned. Don't make large changes just to tick a
  SUGGESTED item unless the user wants them.
- **Required URLs** (flag U): a Met without a URL in its justification shows "not enough for a
  badge", even when the evidence exists. This is the most common reason a project sits at 99%.
- **The site checks the repository itself**, on the default branch, mostly top-level files and
  files directly in `docs/`. Put the evidence where it looks (see the notes on
  `documentation_basics`), and expect answers that depend on an unmerged PR to be contradicted
  until it merges.
- **`know_secure_design` and `know_common_errors` are questions for the user.** Ask; don't
  answer for them.
- **Some criteria have no N/A** even when nothing has happened yet (`report_responses`,
  `enhancement_responses`). Answer from the record: "No reports have been filed yet" is Met.

## Finishing

Tell the user, briefly: the badge percentage before and after (from `project.json`), whether
passing was earned, what's still open and why, where the work folder is, and the PR link if one
was opened. If the badge was earned, offer to add it to the README (workflow.md has the
markdown). Mention that silver builds on this when the user is ready.

When this skill runs as a test or a dry run, stop after `answers.yaml` passes `badge.py check`.
Never propose to or save on the real site.
