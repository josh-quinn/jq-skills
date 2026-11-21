# Passing: notes per criterion

What to check, the usual fix, and the traps, grouped as on the form. The criteria text itself
comes from `badge.py list --details`. These notes don't replace it; if the two disagree, the live
text wins. `O/R` is the GitHub owner/repo. Flags: N = N/A allowed, U = URL required, J =
justification required.

## Contents
- Basics: website, licence, documentation, other
- Change control: repository, versions, release notes
- Reporting: bugs, vulnerabilities
- Quality: build, tests, warnings
- Security: knowledge, cryptography, delivery, vulnerabilities, credentials
- Analysis: static, dynamic
- Common fixes
- Example justifications (style, not text to copy)

## Basics

- `description_good`, `interact`: "the project website" may be the README. It must say what the
  software does (what problem it solves), and how to get it, give feedback, and contribute.
- `contribution` (U), `contribution_requirements` (U): CONTRIBUTING.md (top level or `.github/`)
  explaining the process (PRs?) and what makes a contribution acceptable (tests, style, sign-off).
  The site forces `contribution` to Unmet when there is no contribution file.
- `floss_license`, `floss_license_osi`, `license_location` (U): `gh api repos/O/R/license --jq .license.spdx_id`.
  A LICENSE file at the root. "NOASSERTION" or no licence file is a Fix, but choosing a licence is
  the user's decision: Ask.
- `documentation_basics` (N): **the site's automation reads only top-level files and files directly
  in `docs/`.** A docs tree with nothing directly in `docs/` reads as "Automation instead
  determined Unmet", and fu showed it even with a top-level README covering install and use.
  The fix that worked is a file directly in `docs/` (`docs/README.md`) that covers installing,
  starting, using, and using securely (the security part can be short), linking to the README
  sections rather than repeating them. Add it whenever the repo has no `docs/README.md`: other
  files directly in `docs/` may not satisfy the automation, and the one known fix is this file
  by this name. Cite its URL in the justification. Until the site has been seen to accept the
  alternative, mark `documentation_basics` as a place the automation may disagree.
- `documentation_interface` (N): reference docs for inputs and outputs: `--help`, API docs, a
  config reference. Check that they exist and are current.
- `sites_https`: every project URL (homepage, repo, downloads) is https.
- `discussion`: GitHub issues and PRs count (searchable, URL-addressable, no proprietary client).
- `english` (SHOULD): docs in English, and English reports accepted.
- `maintained`: recent commits or releases, and responses to issues. `SECURITY-INSIGHTS.yml`
  `status: active` autofills this, but check that it's true.

## Change control

- `repo_public`, `repo_track`, `repo_distributed`: true for any public git forge.
- `repo_interim`: interim work is in the public history (commits and PRs between releases), not
  just release dumps.
- `version_unique`: **no N/A.** A project with no release yet has nothing to point at. That's a
  Fix: the user decides whether to cut a first tagged release, which is outward-facing.
- `version_semver`, `version_tags` (SUGGESTED): `git tag --list`; SemVer or CalVer.
- `release_notes` (NU): a CHANGELOG or GitHub release notes per release, readable by humans,
  not a raw git log. N/A only if there are no releases.
- `release_notes_vulns` (N): N/A when no release has fixed a publicly known vulnerability (CVE),
  or when users can't practically update the software themselves.
  Check the advisories (`gh api repos/O/R/security-advisories`) before saying so.

## Reporting

- `report_process` (U), `report_tracker` (SHOULD), `report_archive` (U): the issues URL works for
  all three if issues are enabled (`gh api repos/O/R --jq .has_issues`).
- `report_responses`, `enhancement_responses`: **no N/A.** Check the record:
  `gh issue list --state all --limit 200 --json number,createdAt,comments,author`. Reports in
  the last 2 to 12 months: did a majority get a response? None at all: Met, "No bug reports have
  been filed yet". Don't count the maintainer's own issues as reports needing a response.
- `vulnerability_report_process` (U): SECURITY.md (root, `.github/` or `docs/`) saying how to
  report. The justification **must include the SECURITY.md URL**. The autofill from
  `SECURITY-INSIGHTS.yml` often has none.
- `vulnerability_report_private` (NU): if private reports are accepted, say how.
  `gh api repos/O/R/private-vulnerability-reporting --jq .enabled` shows whether GitHub
  private vulnerability reporting is on. Turning it on is a repo setting: ask before changing it.
  A SECURITY.md that says "open an issue" for vulnerabilities is a Fix.
- `vulnerability_report_response` (N): an initial response within 14 days for reports in the
  last 6 months. N/A if none were received; check the advisories. SECURITY.md stating a response
  time is good, but it's a promise, not the evidence.

## Quality

- `build` (N), `build_common_tools` (N), `build_floss_tools` (N): a working build (Makefile,
  pyproject, package.json, Cargo, go build). N/A only if nothing needs building; most packaged
  projects do build.
- `test`: an automated test suite, released as FLOSS (in the repo is fine).
  `test_invocation` (SHOULD): the standard command for the language (`pytest`, `npm test`,
  `go test ./...`, `cargo test`).
- `test_most` (SUGGESTED): **measure, then quote the number** (`pytest --cov`, `go test -cover`,
  `c8`/`nyc`). Don't estimate. If the project doesn't have the coverage tool, run it without
  installing anything into the repo, e.g. `uv run --no-project --with pytest-cov --with <deps>
  pytest --cov=<package>`.
- `test_continuous_integration` (SUGGESTED): the CI workflow that runs the tests on pushes and
  PRs. Link the workflow.
- `test_policy`: a policy, formal or not, that major new functionality gets tests. Word of mouth
  counts (the user says so), but a written line in CONTRIBUTING.md gives evidence anyone can
  check, and costs little. `tests_are_added`: evidence the policy was followed in recent major
  changes. Look at `git log --stat` for recent features: did tests change with them? If not,
  this is Unmet until that's true, and a doc alone won't fix it. `tests_documented_added`
  (SUGGESTED): the policy appears in the instructions for change proposals (CONTRIBUTING, PR
  template).
- `warnings` (N), `warnings_fixed` (N), `warnings_strict` (SUGGESTED): a linter or compiler
  warnings enabled, warnings addressed (CI fails on them is the strongest evidence), and as
  strict as practical. Run the linter and record the result.

## Security

- `know_secure_design`, `know_common_errors`: **ask the user.** Explain what the criteria mean
  (the details text lists the design principles and the common error classes), offer a draft
  justification from what the code shows, and let them answer. Record `asked_user: true`.
- Cryptography (`crypto_published`, `crypto_call`, `crypto_floss`, `crypto_keylength`,
  `crypto_working`, `crypto_weaknesses`, `crypto_pfs`, `crypto_password_storage`,
  `crypto_random`, all N): grep before answering N/A, e.g. for `hashlib|hmac|ssl|tls|crypto|bcrypt|argon|random|secrets|jwt|openssl|https`.
  Software that makes TLS connections through a standard library *uses* cryptography: the
  relevant items are Met ("uses the platform TLS library, which verifies certificates"), not
  N/A. Signing releases in CI (Sigstore) isn't part of the software. `crypto_random`: security
  tokens must come from a CSPRNG (`secrets`, `crypto.randomBytes`), not `random`.
- `delivery_mitm`: downloads over HTTPS (or ssh). `delivery_unsigned`: no hash fetched over
  http and trusted without a signature. Homebrew formulas with a SHA-256 over https, PyPI and
  npm over https all qualify.
- `vulnerabilities_fixed_60_days`, `vulnerabilities_critical_fixed` (SHOULD): open alerts are
  evidence; look rather than assume: `gh api repos/O/R/dependabot/alerts?state=open`,
  `gh api repos/O/R/code-scanning/alerts?state=open`, or run `osv-scanner`. A medium-or-higher
  vulnerability public for more than 60 days and unpatched is Unmet (a MUST: fix or upgrade it).
- `no_leaked_credentials`: run `gitleaks detect` (whole history) if it's installed, and check
  that secret scanning is on (`gh api repos/O/R --jq .security_and_analysis`). Test fixtures
  with obviously fake keys are fine.

## Analysis

- `static_analysis` (NJ): a static analysis tool beyond compiler warnings, run before major
  releases: CodeQL, Semgrep, bandit, gosec, clippy, or ruff with security rules. Name the tool
  and where it runs.
- `static_analysis_common_vulnerabilities` (SUGGESTED): its rules look for vulnerabilities
  (CodeQL security queries, bandit `S` rules).
- `static_analysis_fixed` (N): open medium-or-higher findings are fixed, or documented as
  deliberate exceptions or false positives. Check the open code-scanning alerts.
- `static_analysis_often` (SUGGESTED): every commit or PR, or at least daily.
- `dynamic_analysis` (SUGGESTED), `dynamic_analysis_unsafe` (SUGGESTED, N),
  `dynamic_analysis_enable_assertions` (SUGGESTED): fuzzing or similar. Unmet is fine at passing.
  `dynamic_analysis_unsafe` is N/A for memory-safe languages.
- `dynamic_analysis_fixed` (MUST, N): N/A when no dynamic analysis is run; say so.

## Common fixes at passing

Roughly in order of how often they come up. Each one is a small commit.

1. A `docs/README.md` covering install, use and secure use, directly
   where the site's automation reads it.
2. A SECURITY.md giving a private reporting route (GitHub private vulnerability reporting, or
   an email address) and the expected first response time. Enabling private reporting on
   GitHub is a setting to ask about.
3. A test policy in CONTRIBUTING.md, and in the PR template if there is one.
4. Tests running in CI on push and pull request, failing the build on failure.
5. A linter in CI that fails on warnings; a static analysis workflow (CodeQL is free for
   public repos).
6. A CHANGELOG, and tagged SemVer releases (cutting a release needs the user's say).

If a repository lacks most of the basics (no CI, no licence, no CONTRIBUTING), say so at pause
1 and suggest the `jq-repo-setup` skill for the groundwork, rather than bolting it all on here.

## Example justifications

Taken from a real project's passing entry. They show the style: specific, short, with evidence
and a URL. Write your own, true for the project in front of you.

- `documentation_basics`: "docs/README.md covers how to install, use and securely use fu,
  linking to the README sections: https://github.com/josh-quinn/fu/blob/main/docs/README.md"
- `vulnerability_report_private`: "Private reporting through GitHub private vulnerability
  reporting, described in SECURITY.md. https://github.com/josh-quinn/fu/security/advisories/new"
- `report_responses`: "No bug reports have been filed yet (new project); the maintainer watches
  GitHub Issues and will respond."
- `test_most`: "The suite covers 90% of the code (pytest-cov), including the CLI, the board
  logic and the TUI driven headlessly."
- `crypto_published` (N/A): "fu does not use cryptography. (Releases are signed in CI with
  Sigstore, which is not part of the software.)"
- `dynamic_analysis` (Unmet): "No fuzzing or other dynamic analysis tool is used beyond the
  test suite."
