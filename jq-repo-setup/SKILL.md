---
name: jq-repo-setup
description: Set up or harden a software repository with professional engineering, security and supply-chain practices using free and open-source tooling (OpenSSF/Linux Foundation, OWASP, CNCF, NSA/CISA/NIST guidance) - governance docs, ADRs, conventional commits, git hooks, CI quality and security gates, dependency updates, branch protection, signed releases, SBOMs, Homebrew or container delivery. Adapts to public or private repos and to the kind of project - a small CLI tool, a library, a long-lived app, or a B2B SaaS product. Use this whenever the user wants to start a new repo "properly", bootstrap or scaffold a project with CI, add security scanning or quality gates, protect main, set up releases/Homebrew/containers, improve an OpenSSF Scorecard or best-practices badge, meet OSPS Baseline / SSDF / SOC 2-style expectations, or make an existing repo "production ready" - even if they never say "security".
---

# Repository setup and hardening

You are setting up (or hardening) a repository so that it starts with the habits mature
projects take years to adopt: every change reviewed and gated, secrets kept out of
history, dependencies pinned and updated, releases reproducible and verifiable, and
decisions written down. Everything here is free and open source, and where possible
comes from bodies whose guidance carries weight: OpenSSF / Linux Foundation (OSPS
Baseline, Scorecard, Sigstore, SLSA), OWASP, CNCF, NIST (SSDF), and NSA/CISA (CI/CD
hardening, SBOM minimum elements, Secure by Design).

The point is proportion. A weekend CLI does not need a threat model and DAST; a B2B
SaaS handling customer data does. Pick the profile first, then apply only what it calls
for, and explain the choices so the owner can disagree.

## Step 1: Understand the project (ask only what you cannot infer)

Inspect the directory first (`git status`, manifests such as `go.mod`, `package.json`,
`pyproject.toml`, `Cargo.toml`, existing `.github/`). Then settle these, asking the user
in one short batch for anything you cannot infer:

1. **Visibility**: public or private. Changes which GitHub features are free (see
   `references/github-plans.md`).
2. **GitHub plan**: Free, Pro (includes students via the Student Developer Pack), Team,
   Enterprise, and whether GitHub Advanced Security (Code Security / Secret Protection)
   is bought. Check what you can: `gh api user --jq .plan.name` (may be hidden).
3. **Project type**, which drives the release and runtime sections:
   - **tool**: a CLI or desktop utility released as binaries (Homebrew, archives).
   - **library**: published to a package registry (npm, PyPI, crates.io, Go modules).
   - **app**: a long-lived service or web app deployed by the owner (containers, cloud).
   - **saas-b2b**: an app holding customer data, with customers who will ask security
     questionnaires (SOC 2 / ISO 27001 style evidence, audit trails, tenant isolation).
4. **Languages** and package managers (see `references/languages.md`).
5. **Team**: solo or several maintainers (decides review rules and CODEOWNERS).
6. **Security contact**: the email or form that goes in SECURITY.md and security.txt.
   Ask for it; never lift an address from `git config`, which is often a personal
   address the owner does not want published. If it is not known yet, write SECURITY.md
   around a clearly named interim address the owner chose, and list "replace the security
   contact" in the final report.
7. **Process appetite**: does the owner want spec-driven development (e.g. spec-kit) and
   ADRs from day one? Default: ADRs yes; spec-kit only if they ask or the project is
   long-lived.

Write back a 4-6 line summary of the profile and what you will set up, and get a yes
before creating files. That summary is the contract for the rest of the work; record it
in the repo too (an ADR, or the top of `docs/security/controls.md` for saas-b2b) so the
next person sees why choices were made. If the user has already stated the answers, say
so in the summary and proceed on their yes.

## Step 2: Choose the target level

Use the **OpenSSF OSPS Baseline** levels as the yardstick, because they are concrete,
current, mapped to NIST SSDF, the EU Cyber Resilience Act and other regimes, and checkable
by tools. `references/frameworks.md` lists every control and how to meet it.

| Profile | Target |
|---|---|
| tool / library, solo, public | Level 1 fully, Level 2 mostly, Level 3 release integrity (signing, SBOM, verification docs) |
| tool / library, private | Level 1 + 2 controls that make sense privately (no public disclosure items) |
| app, private | Level 2, plus the runtime section of `references/project-types.md` |
| saas-b2b | Level 3, plus runtime, data-protection and evidence items in `references/project-types.md` |

Say which controls you are deliberately skipping and why (e.g. "OSPS-QA-07.01 needs a
second human reviewer; you are solo"). Skipped-with-reason beats silently missing.

## Step 3: Apply, in this order

Order matters: protections that stop mistakes (secret scanning, hooks) go in before the
first real push; settings that block merging go in last, once CI is green, or the owner
locks themselves out.

1. **Foundations**: README (what, install, use), LICENSE (public: OSI-approved, ask
   which; private: proprietary notice or none), CONTRIBUTING, SECURITY, CODE_OF_CONDUCT
   (public), CHANGELOG, `.gitignore`, `.editorconfig`, CODEOWNERS, issue and PR templates,
   ADR folder with template and index, a short `CLAUDE.md`/`AGENTS.md` stating the project
   rules for coding agents. Templates are in `assets/` - adapt names, contacts, commands;
   never leave placeholders.
2. **Local gates**: git hooks for secret scanning (gitleaks) on pre-push and Conventional
   Commits on commit-msg (`assets/githooks/`), enabled with `git config core.hooksPath
   .githooks` behind a `make hooks` (or `npm run`/`just`) target. For polyglot repos the
   `pre-commit` framework is fine instead; keep one mechanism, not two.
3. **Build entry points**: one command each for build, test, lint, format check, and an
   aggregate `check` that runs everything CI runs, so contributors can reproduce CI
   locally.
4. **CI quality and security gates** (`references/tooling.md`, `assets/github/workflows/`):
   tests on every PR, linters, SAST, dependency vulnerability scan, secret scan of full
   history, workflow linting (actionlint + zizmor), license policy, plus fuzzing where
   inputs are parsed. Top-level `permissions: contents: read`; `persist-credentials:
   false` on checkout; no `pull_request_target` with checkout of PR code.
5. **Supply chain**: pin every third-party action by full commit SHA with a version
   comment (`scripts/pin-actions.sh` does this), Dependabot or Renovate for every
   ecosystem including `github-actions`, a lockfile committed, dependency review on PRs.
6. **Release pipeline** for the project type (`references/project-types.md`): tag-driven,
   reproducible, signed (Sigstore), with SBOM and provenance, and documented
   verification commands.
7. **Repository settings** via `gh` (`references/github-plans.md`): branch ruleset,
   required checks, review rules, secret scanning/push protection, private vulnerability
   reporting, Dependabot alerts, environments. These are outward-facing changes to the
   owner's account: show what you will change and get explicit approval first.
8. **Verify** (Step 4).

Commit in small Conventional Commits as you go (`chore: add security policy`, `ci: add
secret scanning`), each one green. If the repo already has history, do this on a branch
and open a PR.

## Step 4: Verify before claiming done

Run what you set up rather than assuming it works. If you may not install packages or
reach the network, run the offline subset and say plainly that the rest is unverified:
hooks (bad message, runtime fake secret), `gitleaks` on history and tree, `shellcheck` on
hooks/scripts/workflow `run:` blocks, YAML parse, grep for unpinned `uses:`, leftover
placeholders and paid-only features, and whatever tests need no dependencies.

Full verification:

- `make check` (or equivalent) passes locally when dependencies can be installed (otherwise
  the offline subset above, with the gap stated); the hooks reject a bad commit message and
  a fake secret (generate a fake token at runtime in a temp repo; never commit one).
- `actionlint` and `zizmor .github/workflows` report nothing; every `uses:` is SHA-pinned.
- CI runs green on a PR; then the ruleset is applied and a direct push to `main` is refused.
- For releases, cut a snapshot/dry run (`goreleaser release --snapshot`, `npm pack
  --dry-run`, `python -m build`) and check the artifacts; for a real release, verify the
  signature/attestation with the documented command.
- Public repos: run Scorecard (`scorecard --repo=github.com/OWNER/REPO` or the action)
  and, optionally, the OpenSSF Privateer GitHub scanner for Baseline coverage; report the
  score and the checks you chose not to satisfy.

Report faithfully: what is in place, what was verified and how, what was skipped and
why, and what needs the owner (e.g. registering at bestpractices.dev, creating a tap
repo or a token, pushing release tags, approving setting changes).

## Lessons that cost real time (read before building releases)

`references/lessons.md` has the details. The short version:

- GoReleaser publish-time fields are not validated by `goreleaser check` or snapshots:
  `token` must be exactly `{{ .Env.NAME }}`; there is no `envOrDefault`. Add a test that
  lints these fields, and a snapshot build in CI.
- Homebrew casks: post-install hooks must use Homebrew's declarative install steps
  (`run ..., args: [...], writable_paths: [...]` with `{{staged_path}}` tokens), not Ruby
  `system_command`/`#{staged_path}`, or the cask is unreadable. Load the generated cask
  with `brew` in a test.
- Never move or reuse a published tag; ship the next patch. Delete a broken GitHub
  Release (keep the tag) so every release on the page is complete and signed.
- SLSA's generator must be referenced by tag, not SHA; it is the one accepted exception
  to SHA pinning (Scorecard deducts a point; record the trade-off in an ADR).
- Agents are often not permitted to push tags or change account settings; prepare the
  exact commands for the owner instead of looking for workarounds.

## Reference files

- `references/frameworks.md` - OSPS Baseline controls by level with how to meet each;
  NIST SSDF, NSA/CISA CI/CD, CISA SBOM and Secure by Design in brief.
- `references/tooling.md` - the tool catalogue: what each covers, licence, steward
  (OpenSSF/LF/OWASP/CNCF/government), and whether it works on private repos for free.
- `references/github-plans.md` - which GitHub features need which plan; ruleset JSON and
  `gh` commands; solo-maintainer review pattern.
- `references/languages.md` - per-language lint, test, vulnerability, fuzz and release tools.
- `references/project-types.md` - release and runtime setup for tool, library, app and
  saas-b2b, including containers, IaC, DAST, secrets and evidence for customers.
- `references/lessons.md` - detailed pitfalls and their fixes.
- `scripts/pin-actions.sh` - pin every GitHub Action in a repo to a commit SHA.
- `assets/` - templates for docs, hooks, workflows (security, container scan/SBOM, and
  public-only CodeQL/Scorecard/dependency-review), Dependabot, Security Insights, and
  `scripts/aws-oidc-login.sh`, `sast-opengrep.yml` (Opengrep with pinned binary and rules),
  and `docs/security/controls.md`. There is no ci/release/deploy template because those depend
  on the stack; follow `references/project-types.md` and `references/languages.md`.
