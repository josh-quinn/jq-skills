# The badge workflow (every level)

Every openssf-* skill follows these phases. The level skill adds what is specific to its level.
`badge` below means the helper. Define it as a shell function in each Bash call that uses it
(a string in a variable doesn't split into words in zsh, so `$B ...` fails there):

    badge() { uv run --no-project --with pyyaml python -I <openssf-common>/scripts/badge.py "$@"; }

Keep `--no-project`: without it, `uv` run inside a Python repo attaches to that project and
leaves `.venv/` and `uv.lock` in the repo you're assessing. If `uv` isn't installed, use
`python3 -I <openssf-common>/scripts/badge.py` with PyYAML available.

There are two pauses where you stop and wait for the user. Don't merge or skip them, even when
the work looks obvious. The first pause hands over decisions only the user can make. The
second comes before anything is published.

## 0. Set up

1. Find the repository and its public URL: `git -C <repo> remote get-url origin`, written as
   `https://...` without `.git`. Use the repository's name as the project name.
   If `.github/repo-setup.yaml` exists, read it: it holds answers already given (visibility,
   project type, solo or team) and, under `badges.openssf`, the project's id and last level.
2. `badge init --project <name> --level <level> --repo-url <url>`. This creates the work folder
   (`<data_dir>/<project>/<level>/`, where `data_dir` is set in
   `~/.config/jq-tools/openssf-badge-skills/config.yaml`), snapshots the live criteria into it,
   writes a `gaps.md` skeleton, and, if the project is already on bestpractices.dev, saves its
   current answers to `project.json`. Tell the user where the work folder is. Running `init`
   again refreshes the criteria and `project.json`, and keeps your `gaps.md`.
   - `init` prints `project_status`: `registered`, `not registered on bestpractices.dev` (a
     normal state: `"project": null` then means that), or `not looked up`. Say which. (The
     separate `badge project --repo-url <url>` exits with code 3 when the project isn't
     registered; expect that and don't treat it as a failure.)
   - Add `--no-lookup` when the user says the project isn't registered or not to look it up.
   - Dry runs and tests: set `OPENSSF_BADGES_DATA_DIR` to a temp folder (and `JQ_TOOLS_CONFIG`
     to a temp root) so nothing lands in the real `data_dir` or config.
   - No network: say so and stop. Don't fall back on remembered criteria: the wording,
     flags and the set of criteria change, and an answer to an outdated criterion is wrong.
3. Read the repository's own rules before changing anything: CONTRIBUTING, AGENTS.md or
   CLAUDE.md, PR templates, and the user's instructions. They decide branch names, commit
   style, sign-off and attribution. These skills don't impose their own.
4. If `project.json` exists, its answers are a starting point, not evidence. Answers on the
   site can be stale, wrong, or filled in by the site's automation. Check each one again.

## 1. Assess

1. `badge list --criteria <work>/criteria --level <level> --details`. Read every criterion's
   wording and details, plus the level skill's notes.
2. Read the repository: top-level files, `docs/`, CI workflows, build files, tests,
   `SECURITY-INSIGHTS.yml`, the release setup. On GitHub, check settings with `gh api`
   (rulesets, private vulnerability reporting, secret scanning, open alerts). If you can't
   check something, mark it unverified. Don't assume it.
3. Run what you can: the tests (with coverage, if the criterion asks about it), the linters,
   the build. The command and its result are evidence.
4. Fill in `gaps.md`: edit it by hand, it's yours (`init` keeps it; `badge gaps` prints a fresh
   skeleton if you want to start over). Every criterion already has a row; give each a Proposed
   value:
   - **Met**: true today. Evidence: a file and line, a setting, a CI job, or a command's output.
   - **Fix**: not true yet, and a repo change would make it true. Say what the change is.
   - **Unmet**: leave unmet, for SHOULD and SUGGESTED only, with the reason. A MUST left Unmet
     blocks the badge, so a MUST is Unmet only when it truly can't be met yet. Explain why.
   - **N/A**: doesn't apply, and only where the N flag allows it. Say why.
   - **Ask**: only the user can say (statements about themselves, their commitments, or
     settings you can't see).
5. Above the tables, write a short summary: MUST blockers and the planned fix for each, the
   Ask items, SHOULD/SUGGESTED you suggest leaving Unmet, and places where the site's
   automated checks may disagree (see site.md).

**Pause 1.** Show the user the summary (the file path is enough for the full table) and ask:
the Ask questions; which fixes to make; and whether you may create a branch, push it and open a
pull request. Wait for the answers. Record them in `gaps.md` (e.g. "the user confirmed, <date>").

## 2. Change the repository

- Make only the agreed fixes, on a branch from the default branch, following the repository's
  rules. If it has none: small Conventional Commits, one purpose each, tests in the same commit,
  and the test written first for code changes.
- Keep docs true to the code (see honesty.md). A badge-motivated doc that overstates what the
  code does is worse than no doc.
- Run the project's own checks before each push. Open the pull request if it was agreed, and
  map each change to the criteria it serves in the PR description.
- Justification URLs point at the default branch, and the site's automated checks read the
  default branch. Answers that depend on this PR only hold once it is merged. Tell the user;
  draft the answers now, but propose them only after the merge.

## 3. Answer

1. Create `<work>/answers.yaml` with `badge answers --criteria <work>/criteria --level <level>
   --project <name> --repo-url <url> --out <work>/answers.yaml`: a skeleton with every
   criterion present and unknown (`?`). It never overwrites a file that exists. Fill in each
   entry (format below). `?` is the status for Ask items you haven't been able to put to the
   user: `check` warns about each, and a MUST left `?` blocks the badge.
2. Justifications are public, under CC-BY-3.0+, and read by people deciding whether to trust
   the project. Write one or two plain sentences, specific to this project: name the file,
   setting or tool, and add a URL to the evidence. The URL is required where the U flag is set
   and helps everywhere else. Never copy another project's justification; it has to be true
   for this one.
3. `badge check <work>/answers.yaml` until it reports no errors. Read the warnings too.

**Pause 2.** Give the user a summary: the counts, any MUST not Met (no badge until it is), the
Ask answers used, and any existing site answers that will be replaced. Then ask for a go-ahead
to propose the answers on bestpractices.dev, and whether the user will save or wants you to.

## 4. Propose and save (only on the user's go-ahead)

Read site.md first. In outline:

1. Not registered yet? The user creates the project at `https://www.bestpractices.dev/en/projects/new`
   (it needs their GitHub login; never log in for them). Then
   `badge project --repo-url <url> --out <work>/project.json`.
2. Refresh `project.json` just before building URLs, then `badge urls <work>/answers.yaml`. It
   writes `proposals.txt`: answers already on the site unchanged are left out, changed ones are
   forced, and long sets are split over several URLs.
3. Open the URLs one at a time. The user can open them, or you can with Claude in Chrome. The
   form shows the proposals highlighted. Whoever saves uses **Save** (stays on the page), not
   "Submit (and exit)". Save each URL's proposals before opening the next.
4. Afterwards, refresh `project.json` and compare it with `answers.yaml` and the badge
   percentage. For anything that didn't stick, find out why (site.md lists the usual causes).
5. Report the percentage, whether the badge was earned, and what's left and why. Offer to add
   the badge to the README:
   `[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/<id>/badge)](https://www.bestpractices.dev/projects/<id>)`
6. If the repo has a setup record, `.github/repo-setup.yaml` (left by jq-repo-setup), offer to
   record the badge in it, in the same commit as the README badge:

   ```yaml
   badges:
     openssf:
       project_id: <id>
       level: passing        # the level the site now shows: passing, silver or gold
       date: <today>
   ```

   Update that section only; the rest of the file belongs to other skills. jq-repo-setup's
   check reads it to confirm, later, that the site still shows that level. Don't create the
   file if it isn't there.

When testing a skill (evals, dry runs), stop after phase 3: never propose to or save on the
real site.

## answers.yaml

```yaml
level: passing
project: myproj
repo_url: https://github.com/OWNER/REPO
criteria_ref: 31325acd...          # "ref" from source.json
answers:
  description_good:
    status: Met                    # Met | Unmet | N/A | ?
    justification: >-              # submitted to the site; public
      The README opens with what myproj does: ... https://github.com/OWNER/REPO#readme
    evidence: README.md lines 1-4  # for the reviewer; never submitted
  know_secure_design:
    status: Met
    justification: The maintainer applies ...
    evidence: the user confirmed, 2026-11-15
    asked_user: true               # statements about the person need this
  dynamic_analysis:
    status: Unmet
    justification: No fuzzing or other dynamic analysis is run yet.
```

`badge check` enforces: every criterion answered, no unknown keys, a valid status, N/A only where
allowed, URLs and justifications where required, evidence for every Met, `asked_user` on
personal statements, and a reason for any SHOULD left Unmet. It also lists the MUSTs that block
the badge.
