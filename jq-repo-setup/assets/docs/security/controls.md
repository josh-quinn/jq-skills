# Security controls map

- **Owner**: {name}
- **Last reviewed**: {date}
- **Review cadence**: quarterly, and whenever a control changes

One place to answer security questionnaires. Yardstick: OpenSSF OSPS Baseline (state the
version you checked against, see references/frameworks.md) with NIST SSDF (SP 800-218)
mapping. Profile and target level are recorded in {ADR link}: {visibility, plan, team size,
stack, hosting}.

Status values: **met** (in the repo, verified or mechanically checked), **configured-by-owner**
(exact commands in OWNER-COMMANDS.md; met once applied), **partly**, **planned**, **n/a**
(with reason). "Not run yet" means a workflow exists but has not run on GitHub.

## Skipped or not applicable, with reasons

| Control | Status | Reason |
|---|---|---|
| {control id and name} | n/a or partly | {why, and the compensating control or revisit trigger} |

Start from the preset in references/frameworks.md ("solo maintainer, private repo,
saas-b2b") and delete rows that do not apply to this profile.

## OSPS Baseline Level 1 / 2 / 3

One table per level, one row per control from references/frameworks.md:

| Control | Status | Evidence / reason |
|---|---|---|
| {AC-01.01 MFA} | configured-by-owner | {path, workflow job, or setting that proves it} |

## NIST SSDF mapping

| Practice group | Where it is met |
|---|---|
| PO (prepare the organisation) | {docs, ADRs, CONTRIBUTING} |
| PS (protect the software) | {rulesets, signing, SBOM, pinned CI} |
| PW (produce well-secured software) | {tests, SAST, threat model, reviews} |
| RV (respond to vulnerabilities) | {SECURITY.md, vulnerability SLAs, Dependabot} |
