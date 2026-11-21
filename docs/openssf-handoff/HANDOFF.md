# Handoff: OpenSSF badge skills

This was written at the end of the session that took `fu` (https://github.com/josh-quinn/fu,
bestpractices.dev project 16725) to its badges by hand, 2026-11-15. Read it before designing
the skills. It holds what that session learned and won't otherwise reach a new session.

## The goal

Four skills, built one at a time with the `skill-creator` skill:

1. **openssf-passing**: get a project to the Best Practices "passing" badge. Build this first.
2. **openssf-silver**: builds on passing.
3. **openssf-gold**: builds on silver; mostly explains what a solo project can't meet.
4. **openssf-baseline**: OSPS Baseline levels 1, 2 and 3.

Where they live (the user's convention): the source goes in this repo,
`~/development/repos/jq-skills/openssf-badge-skills/`, one folder per skill. They are linked into
`~/.claude/skills` (and `~/.copilot/skills`), never written there directly. Shared material,
such as the form-filling helper and criteria fetching, should be one shared reference rather
than four copies.

## What fu reached, and why it stopped

| Level | Result | What blocks the rest |
|---|---|---|
| Passing | 100% | none |
| Silver | 98% | `access_continuity` (MUST): someone else must be able to continue the project. Fix: a real GitHub account successor, named in GOVERNANCE.md |
| Gold | 22% | Solo-blocked MUSTs: `bus_factor` >= 2, `contributors_unassociated` >= 2, `two_person_review` |
| Baseline 1 | 100% | none |
| Baseline 2 | 100% | none |
| Baseline 3 | 95% | OSPS-QA-07.01: non-author approval before merge |

`fu-project-16725.json` in this folder holds every answer and justification fu gave
(downloaded from `https://www.bestpractices.dev/projects/16725.json`). Use it as a worked
example and as a source of eval expectations, but don't copy it as a template: each
justification must be true for the project being assessed.

## Where the criteria come from (never answer from memory)

- `https://raw.githubusercontent.com/ossf/best-practices-badge/main/criteria/criteria.yml` lists
  each criterion. Levels are `'0'` passing, `'1'` silver, `'2'` gold. Per-criterion flags:
  `category` (MUST/SHOULD/SUGGESTED), `na_allowed`, `met_url_required`,
  `met_justification_required`, `na_justification_required`, `future`, `obsolete`.
- `.../config/locales/en.yml` has the wording, under `en.criteria.<level>.<key>.description`
  and `details`.
- `.../criteria/baseline_criteria.yml` is OSPS Baseline. `metal_to_baseline_map.yml` maps
  between the two series, so evidence can be reused across them.
- `list_criteria.py` (in this folder) prints one level with its flags:
  `uv run --with pyyaml python -I list_criteria.py criteria.yml en.yml 0`.
  The YAML uses `!!omap`, and the script handles that.
- A project's current answers are at `https://www.bestpractices.dev/projects/<id>.json`, with
  `<key>_status`, `<key>_justification`, and `badge_percentage_0|1|2|baseline_1|2|3`. Read this
  instead of scraping the form.

## The bestpractices.dev form, mechanically

- The edit URLs are `https://www.bestpractices.dev/en/projects/<id>/<level>/edit`, where level is one
  of `passing`, `silver`, `gold`, `baseline-1`, `baseline-2`, `baseline-3`. The page without
  `/edit` is read-only and has no form. A redirect after saving can leave you there.
- New project: `/en/projects/new`. It needs the user to be logged in (GitHub OAuth). If the repo
  is already registered, it redirects to the existing project and says "This project already
  exists!"
- Field names: radios `project[<key>_status]` with values `Met`, `Unmet`, `N/A`, `?`.
  Baseline keys are prefixed `osps_` (e.g. `osps_ac_03_01`). Textareas are
  `project[<key>_justification]`.
- Saving: the submit button with `name="continue" value="Save"` saves and stays on the page.
  `name="commit"` means "Submit (and exit)". After saving, the flash message says "Project was
  successfully updated." or "CONGRATULATIONS on earning a ... badge!".
- The fill helper used, run with Claude in Chrome's `javascript_tool` on the edit page:

  ```js
  const fill=(A)=>{const f=document.querySelector('form[id^=edit_project]'); const res=[];
    for(const [k,[s,j]] of Object.entries(A)){
      const r=f.querySelector(`input[name="project[${k}_status]"][value="${s}"]`);
      if(!r){res.push('NO '+k+' '+s);continue;} r.click();
      const t=f.querySelector(`[name="project[${k}_justification]"]`);
      if(t){t.value=j; t.dispatchEvent(new Event('input',{bubbles:true}));} else res.push('nojust '+k);}
    return res;};
  // then click [...f.querySelectorAll('[type=submit]')].find(b=>b.name==='continue'&&b.value==='Save')
  ```
  `NO key N/A` in the result means that option doesn't exist for this criterion.
- To check what's left after saving: count radios whose checked value isn't Met or N/A, plus
  images whose alt text contains "not enough" (Met is selected but the required URL or
  justification is missing).
- **Claude in Chrome blocks tool output containing URLs or query strings** (`[BLOCKED:
  Cookie/query string data]`). Return statuses and lengths, not justification text. Its output
  is also truncated at about 1,000 characters, so page through results or use the JSON export.

## Gotchas met on fu

- **The site runs automated checks ("detectives") that can contradict the user.** They read
  only top-level repository files. `documentation_basics` showed "Automation instead
  determined Unmet" until a file directly in `docs/` (fu added `docs/README.md`) mentioned
  installing, using and security. A user-set Met is kept when the check's confidence is low,
  but the mismatch is flagged. Fix the repo rather than argue.
- **Some criteria have no N/A option**: `report_responses` and `enhancement_responses` with no
  reports yet. Answer Met and say that no reports have been filed yet.
- **Met with a required URL but no URL in the justification** shows "not enough for a badge".
  This is how `vulnerability_report_process` sat at 99%: the SECURITY-INSIGHTS-autofilled
  justification had no URL.
- `SECURITY-INSIGHTS.yml` at the repo root autofills several answers.
- `know_secure_design` and `know_common_errors` are statements about the person. Ask the
  user; don't decide them.
- SHOULD and SUGGESTED criteria can be Unmet with a justification and still earn the badge.
  MUSTs can't.

## Honesty rules (the user agreed to these)

- Every Met must be true and backed by something checkable (a file, a setting, a CI job, a
  command's output). Verify before claiming: run the tests for coverage, check the ruleset
  with `gh api`, run `gh attestation verify`, rebuild to prove reproducibility.
- **Never meet review or bus-factor controls with a second account owned by the same person.**
  The user asked about using their second GitHub account. The answer was no, because it would
  be a false attestation. Mark these Unmet and explain what a real second person would change.
- If the docs claim something the code doesn't do, change the docs or fix the code. Twice in
  fu the security docs overstated things: they said no other programs are run, though `git`
  and the file opener are, and that no transcript content is stored, though session titles
  are. Both were corrected.
- Read the code before claiming a security property. Where a claim names a test, the test
  must exist; fu added the missing tests (hostile shell quoting, failed atomic save) rather
  than cite tests that weren't there.

## What a typical project needs added, by level

Starting from a repo already set up with the `jq-repo-setup` skill (README, LICENSE,
CONTRIBUTING, SECURITY.md, CODE_OF_CONDUCT, CI with tests, ruff/CodeQL/gitleaks/OSV-Scanner,
Dependabot, signed releases, a branch ruleset):

- **Passing**: mostly answering. Watch for a top-level `docs/` file (above); tests, a
  documented test policy and CI; a SECURITY.md with private reporting; a URL in each
  required-URL justification.
- **Baseline 1-3**:
  - `GOVERNANCE.md`: roles, access to sensitive resources, vetting before access is given.
  - DCO sign-off: a `prepare-commit-msg` hook, plus a CI check that skips bots (Dependabot signs
    off as support@github.com, not its author address), plus the `web_commit_signoff_required`
    repo setting.
  - Per-job `permissions:` in every workflow, and no `read-all` (Scorecard included).
  - `docs/architecture.md`, `docs/security/threat-model.md` (STRIDE), a secrets policy, and a
    VEX policy with a folder.
  - SECURITY.md covering end of life and how advisories are published.
  - CONTRIBUTING covering dependency selection and tracking, and building from source.
  - The README's verification command pins the signer:
    `gh attestation verify --signer-workflow OWNER/REPO/.github/workflows/release.yml`. Check
    it fails for the wrong workflow too.
  - The README lists related repositories.
- **Silver**:
  - `ROADMAP.md` covering at least a year, with "not planned" items. Draft it, but the user
    must review it, because it states their intent.
  - SECURITY.md "What you can expect": the security requirements.
  - An assurance case: threat model, trust boundaries, Saltzer and Schroeder principles, and
    CWE countermeasures each tied to a test or check.
  - Code style named in CONTRIBUTING, badges in the README (within 48 hours), and a quick
    start, upgrade and uninstall section.
  - Reproducible builds: rebuild the tag and compare SHA-256 with the release, plus a CI step
    that builds twice and runs `cmp`. Hatchling and uv were reproducible by default.
  - Input validation with an allowlist: fu added a session-id pattern, test first.
  - `access_continuity` needs a real person.
- **Gold**: solo-blocked (above). Otherwise:
  - SPDX licence and copyright headers in every file;
  - tasks labelled for new contributors;
  - required 2FA;
  - documented code review standards;
  - 90% statement and 80% branch coverage;
  - dynamic analysis before releases (e.g. Hypothesis or atheris);
  - hardened site headers;
  - a security review within 5 years.

## How the skills should behave (proposed; settle this in the interview)

- Work in phases: **assess**, then **change the repo**, then **answer the form**.
  - **Assess**: read the criteria live, read the repo, and produce a gap table (criterion,
    status, evidence or what's missing).
  - **Change the repo**: on a branch, as small Conventional Commits with tests first, then a
    PR.
  - **Answer the form**: produce a reviewable answers file (key, status, justification) before
    touching the site.
- Submitting the form is an outward-facing action: get the user's go-ahead before saving on
  bestpractices.dev, and never log in for them.
- Each user's repo rules apply. This user: no Claude or Co-Authored-By attribution, author
  Josh Quinn <150349082+josh-quinn@users.noreply.github.com>, small Conventional Commits, never
  push to group5 e-tivity GitLab repos.

## Testing the skills (for skill-creator's eval loop)

- Never let an eval run submit to the real bestpractices.dev. Evals should stop at the gap
  table, the repo changes and the answers file, so they can be graded offline.
- Good eval inputs:
  - a small throwaway repo with gaps planted on purpose: no docs/ file, a SECURITY.md without
    private reporting, no tests in CI, `permissions: read-all`;
  - a copy of fu at a commit before these changes (`git -C ~/development/repos/tools/fu log`;
    e.g. 306759c is v0.1.0 before the badge work);
  - a project with a second maintainer, to check the skill doesn't wrongly say "solo-blocked".
- Checkable assertions:
  - every MUST appears in the gap table;
  - no Met without evidence;
  - each required-URL criterion has a URL;
  - `know_*` items are routed to the user;
  - no review control is met by a same-owner account;
  - no claim about the code that the code contradicts.
