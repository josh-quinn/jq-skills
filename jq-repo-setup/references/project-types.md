# Project types: release and runtime

## Contents
1. tool (CLI / desktop, binaries, Homebrew)
2. library (package registries)
3. app (long-lived service the owner deploys)
4. saas-b2b (customer data, customer security reviews)
5. Long-term development practices (any type)

## 1. tool

Release on tags `vX.Y.Z` that are on `main` (the workflow checks
`git merge-base --is-ancestor $GITHUB_SHA origin/main`), after running the tests.

- Build: GoReleaser / cargo-dist / PyInstaller etc. Archives per OS/arch, `checksums.txt`,
  LICENSE + README + man pages inside archives, SBOM per archive (syft).
- Sign: public repos - `actions/attest-build-provenance` on archives and checksums, plus
  `slsa-github-generator` (generic, `upload-assets: true`) for SLSA L3 `*.intoto.jsonl`
  (Scorecard Signed-Releases reads release assets). Private - cosign keyless on checksums
  only if the public Rekor entry is acceptable; otherwise checksums.
- Document verification in README: `gh attestation verify <file> --repo OWNER/REPO`,
  `slsa-verifier verify-artifact <file> --provenance-path x.intoto.jsonl --source-uri github.com/OWNER/REPO --source-tag vX`.
- Homebrew: a separate public tap repo `OWNER/homebrew-tap` (owner creates it) and a
  fine-grained PAT with Contents: write on the tap only, stored as a secret by the owner.
  GoReleaser `homebrew_casks` (casks replaced formulae for binaries). If unsigned/not
  notarized on macOS, clear quarantine in a post-install step using the declarative
  install-steps DSL (see lessons.md). Make the cask step skip, not fail, when the token is
  absent (`skip_upload` with `index .Env`).
- Private tools: a public tap cannot fetch private release assets. Use a private tap with
  `HOMEBREW_GITHUB_API_TOKEN` on users' machines, or skip Homebrew.
- CHANGELOG.md updated in a `docs(changelog)` PR before tagging; release notes grouped by
  commit type (GoReleaser `changelog.groups` or release-please).
- RELEASING.md: one-time setup, per-release steps, verification, what to do when a release
  breaks (never move a tag; next patch; delete the broken GitHub Release, keep the tag).

## 2. library

- SemVer and a documented compatibility policy (what is public API).
- Publish from CI with OIDC: PyPI trusted publishing, `npm publish --provenance`,
  crates.io trusted publishing; never a long-lived token on a laptop.
- Generate API docs (pkg.go.dev automatic, Sphinx/MkDocs, TypeDoc, docs.rs).
- Test against the supported version matrix; dependency ranges, not pins, in the
  published manifest; lockfile for dev only.
- release-please fits well: release PR, CHANGELOG, tag, publish job on release.

## 3. app (deployed service)

Everything in the base setup, plus:
- **Environments**: `staging` and `production` GitHub environments; production requires a
  reviewer and only deploys from `main` tags; secrets scoped to environments.
- **Cloud auth via OIDC** (`id-token: write`, `aws-actions/configure-aws-credentials` with a
  role, GCP Workload Identity Federation, Azure federated credentials); no static keys.
- **Containers**: Dockerfile best practice (languages.md); build once, promote the same
  digest; Trivy/Grype scan as a required check; sign images with cosign and attach SBOM
  attestations (`cosign attest --type spdxjson`); verify signatures at deploy (Kyverno /
  Sigstore policy-controller on Kubernetes).
- **IaC** in the repo (Terraform/OpenTofu, Helm): `fmt`, `validate`, Trivy config or
  Checkov on PRs; plan on PR, apply on merge with environment approval.
- **Config**: 12-factor env vars; `.env.example` committed, `.env` ignored; secrets from a
  manager (cloud secret manager, SOPS + age, or Vault/OpenBao (LF)).
- **Database migrations** versioned in the repo and run by the deploy pipeline.
- **Observability**: structured logs, health/readiness endpoints, OpenTelemetry (CNCF).
- **DAST**: ZAP baseline scan against the staging/preview URL after deploy (non-blocking at
  first, blocking once tuned).

## 4. saas-b2b

Everything in `app`, plus what customers' security questionnaires and SOC 2 / ISO 27001
auditors ask for. The repo cannot make a company compliant, but it can produce most of the
engineering evidence:
- **Change management evidence**: every production change via a PR with review and passing
  checks (rulesets, no bypass for production); deploy logs tied to commit SHAs; releases
  tagged. Turn off admin bypass once there is a second engineer.
- **Access**: CODEOWNERS for sensitive paths (auth, billing, infra, migrations); GOVERNANCE /
  access list (OSPS-GV-01); offboarding checklist.
- **Security docs** in `docs/security/`: threat model (STRIDE per component, OWASP Threat
  Dragon file), data-flow diagram, data classification and retention, secrets policy and
  rotation, incident response runbook, backup/restore runbook with a tested restore,
  vulnerability management policy with SLAs (e.g. critical 7 days, high 30 days).
- **Application security**: OWASP ASVS level 2 as the requirements checklist; OWASP Top 10
  tests; tenant isolation tests (one tenant cannot read another's data) as a named test
  suite; authz checks centralised; audit logging of security-relevant events visible to
  customers (Secure by Design); rate limiting; dependency and container scanning blocking
  on high/critical.
- **SBOM and VEX** per release; OWASP Dependency-Track ingesting SBOMs for continuous
  monitoring of deployed versions.
- **Pen-test readiness**: a `security.txt` (RFC 9116) on the product domain, a VDP page,
  and a staging environment that mirrors production.
- **Customer-facing**: a trust/security page listing the above; a subprocessors list.
- Map controls to OSPS Baseline L3 and NIST SSDF in `docs/security/controls.md` so
  questionnaires can be answered from one place.

### saas-b2b evidence docs: what each must contain
Short and specific beats long and generic; a reviewer should find an answer in under a
minute. Each doc: owner, last-reviewed date, and the review cadence.
- `threat-model.md`: assets, trust boundaries, data-flow list, STRIDE table per component
  with mitigation and the test or control that proves it.
- `secrets-policy.md`: where secrets live, who can read them, rotation periods, what to do
  on leak (rotate first, then investigate), no secrets in env files in git.
- `incident-response.md`: severity levels, who is paged, first-hour checklist, customer
  notification deadline, post-incident review template.
- `tenant-isolation-test-plan.md`: isolation mechanism (e.g. Postgres row-level security),
  every tenant-scoped table, the cross-tenant read/write/list cases, where the suite runs in CI.
- `backup-restore.md` (with the date of the last tested restore), `vulnerability-management.md`
  (SLAs), `data-classification.md`, `access-and-offboarding.md`, `environments.md`.
- `controls.md` (start from `assets/docs/security/controls.md`): one row per OSPS Baseline L3 / SSDF control: met / partly / not applicable,
  evidence path, reason. Skipped controls live here.

### Cloud auth without a third-party action
`assets/scripts/aws-oidc-login.sh` exchanges the job's OIDC token for short-lived AWS
credentials with the AWS CLI already on runners (needs `id-token: write` on that job only).
It avoids pinning and trusting `aws-actions/configure-aws-credentials`; use that action
instead if the owner prefers, pinned by SHA like any other. Either way: trust policy on the
IAM role restricted to this repo and the `environment:`/ref claim, never `repo:*`.
Image scanning/SBOM: `assets/github/workflows/container.yml` (Hadolint, Trivy, Syft as
digest-pinned images; free on private repos).

## 5. Long-term development practices (any type)

- ADRs (`docs/adr/NNNN-title.md`, template + index); supersede, never rewrite accepted ones.
- Specs before features for anything non-trivial (spec-kit or a `specs/NNN-feature/` folder
  with spec, plan, tasks); keep them in the repo.
- `CLAUDE.md` / `AGENTS.md`: the rules agents must follow (commits, tests first, ADRs,
  no secrets, scope), short and pointing at the constitution/CONTRIBUTING.
- Test-first with a regression test for every bug and security fix.
- Small, single-purpose Conventional Commits, green at every commit; enforced by hook + CI.
- Deprecation policy and supported-versions table (SECURITY.md).
- Scheduled maintenance: Dependabot grouped weekly; Scorecard weekly; a quarterly review
  of ADRs, threat model and access list.
