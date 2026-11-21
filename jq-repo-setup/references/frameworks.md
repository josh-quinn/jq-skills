# Frameworks and how to meet them

## Contents
1. OpenSSF OSPS Baseline (primary yardstick)
2. NIST SSDF (SP 800-218)
3. NSA/CISA: Defending CI/CD Environments
4. CISA SBOM minimum elements
5. CISA Secure by Design and memory safety
6. OpenSSF Scorecard and Best Practices badge
7. EU Cyber Resilience Act (if distributing to the EU)

Check for newer versions at run time when it matters (baseline.openssf.org lists
versions; this file reflects v2026.02.19, with a 2026.08.28 release also published).

## 1. OSPS Baseline (OpenSSF, Linux Foundation)

Three levels of controls for any project. Level 1: any code project. Level 2: a project
with at least two maintainers and a small user base. Level 3: widely used or
security-critical. Each row: control, then how to meet it on GitHub.

### Level 1
| Control | How |
|---|---|
| AC-01.01 MFA for sensitive access | Owner enables 2FA on the account/org; for orgs, require 2FA in org settings |
| AC-02.01 least privilege for new collaborators | Default repo permission "Read"; add collaborators with the lowest role |
| AC-03.01 no direct commits to main | Ruleset: require pull request |
| AC-03.02 main cannot be deleted | Ruleset: restrict deletions, block force pushes |
| BR-01.01 sanitise untrusted CI metadata | Never interpolate `${{ github.event.* }}` into `run:`; pass through `env:`. zizmor `template-injection` |
| BR-01.03 untrusted code gets no secrets | No `pull_request_target` + checkout of PR head; fork PRs get read-only token |
| BR-03.01/.02 HTTPS everywhere, authenticated distribution | GitHub Releases/registries over HTTPS; checksums |
| BR-07.01 no secrets in VCS | gitleaks pre-push hook + CI full-history scan; push protection where available |
| DO-01.01 user guide | README usage section, `--help`, docs site |
| DO-02.01 how to report defects | Issue templates; README "Reporting bugs" |
| GV-02.01 public discussion | Issues (and Discussions if wanted) |
| GV-03.01 contribution process | CONTRIBUTING.md |
| LE-02.01/.02, LE-03.01/.02 OSI licence in LICENSE, shipped with releases | LICENSE at root, included in archives/packages |
| QA-01.01/.02 public repo, full history | Public GitHub repo; no history rewriting of main |
| QA-02.01 dependency list | Manifest + lockfile committed |
| QA-04.01 list of all repos | README "Related repositories" if multi-repo |
| QA-05.01/.02 no generated or opaque binaries in VCS | `.gitignore` build outputs; Scorecard Binary-Artifacts |
| VM-02.01 security contacts | SECURITY.md |

### Level 2
| Control | How |
|---|---|
| AC-04.01 default lowest CI permissions | Top-level `permissions: contents: read` in every workflow; repo setting "Read repository contents" for GITHUB_TOKEN |
| BR-02.01 unique version per release | SemVer tags `vX.Y.Z` |
| BR-04.01 change log per release | CHANGELOG.md + generated release notes grouped by commit type |
| BR-05.01 standard dependency tooling | Package manager with lockfile; no curl-pipe-sh in CI; `go install pkg@version` pinned |
| BR-06.01 signed releases or signed manifest | Sigstore: `actions/attest-build-provenance` (public, or Enterprise for private) or `cosign sign-blob` on checksums; SLSA provenance |
| DO-06.01 how dependencies are chosen and tracked | CONTRIBUTING "Dependencies" section + Dependabot/Renovate |
| DO-07.01 build instructions | README/CONTRIBUTING "Building from source" |
| GV-01.01/.02 who has access, roles | MAINTAINERS.md or GOVERNANCE.md (solo: one line) |
| GV-03.02 contribution requirements | CONTRIBUTING (tests, style, commits) |
| LE-01.01 contributors assert authorship per commit | DCO: `Signed-off-by` (`git commit -s`) enforced by a DCO check, or a CLA |
| QA-03.01 status checks must pass before merge | Ruleset required status checks |
| QA-06.01 automated tests in CI | Test job on every PR |
| SA-01.01 design documentation | `docs/architecture.md` + ADRs |
| SA-02.01 external interfaces documented | CLI reference/man pages, API reference (OpenAPI) |
| SA-03.01 security assessment per release | Short `docs/security-assessment.md`: assets, threats, mitigations; revisit each minor release |
| VM-01.01 CVD policy with timeframes | SECURITY.md with acknowledgement and fix targets |
| VM-03.01 private reporting | GitHub private vulnerability reporting (public repos) or a security email |
| VM-04.01 publish vulnerability data | GitHub Security Advisories (GHSA) and CVEs via GitHub as CNA |

### Level 3
| Control | How |
|---|---|
| AC-04.02 per-job least privilege | `permissions:` on each job, only what it needs |
| BR-01.04 validate input even from collaborators | Same injection hygiene for workflow_dispatch inputs |
| BR-02.02 assets tied to release id | Version in archive names; provenance subject |
| BR-07.02 secrets policy (store, access, rotate) | `docs/secrets-policy.md`; OIDC federation to clouds instead of long-lived keys |
| DO-03.01/.02 how to verify integrity and signer | README "Verifying releases" with `gh attestation verify` / `cosign verify-blob` / `slsa-verifier` |
| DO-04.01, DO-05.01 support scope and EOL | SECURITY.md "Supported versions" |
| GV-04.01 vet collaborators before escalated access | GOVERNANCE.md process |
| QA-02.02 SBOM with compiled releases | Syft (SPDX + CycloneDX) attached to each release |
| QA-04.02 subprojects as strict as main | Same rulesets across repos (org ruleset) |
| QA-06.02/.03 when tests run; major changes add tests | CONTRIBUTING; PR template checklist |
| QA-07.01 non-author approval before merge | Ruleset: 1 approval, code owners. Solo: not achievable honestly; document it |
| SA-03.02 threat model | `docs/threat-model.md` (STRIDE or OWASP Threat Dragon) |
| VM-04.02 VEX for non-affecting vulns | OpenVEX documents (`vexctl`) when a scanner flags something unreachable |
| VM-05.01-.03 SCA thresholds, fix before release, block on PR | dependency-review / osv-scanner with fail-on severity; release workflow runs the scan |
| VM-06.01/.02 SAST thresholds, block on PR | CodeQL/Opengrep/gosec etc. as required checks with a documented severity threshold |

Machine-readable evidence: add `SECURITY-INSIGHTS.yml` (OpenSSF Security Insights spec,
template in `assets/`) - the Privateer scanner and LFX Insights read it.

## 2. NIST SSDF (SP 800-218 v1.1; v1.2 draft Dec 2025)

Four groups. Map what you set up so a customer or auditor can see it:
- **PO Prepare the organization**: CONTRIBUTING rules, ADRs, CI as the enforced toolchain,
  security requirements in SECURITY.md. v1.2 adds PO.6 continuous improvement.
- **PS Protect the software**: branch rules, signed commits/tags optional, provenance,
  SBOM, archived releases (PS.1-PS.3).
- **PW Produce well-secured software**: threat model/security assessment (PW.1), reviews
  (PW.7), SAST/DAST/fuzz (PW.7-PW.8), secure defaults (PW.9). v1.2 adds PW.10 robust and
  reliable updates (signed, verifiable updates).
- **RV Respond to vulnerabilities**: SECURITY.md, advisories, root-cause regression tests
  (RV.1-RV.3).

## 3. NSA/CISA "Defending CI/CD Environments" (June 2023)

Their recommendations, as concrete settings:
- Strong auth: 2FA, least-privilege tokens, fine-grained PATs scoped to one repo, short expiry.
- No long-lived secrets in pipelines: OIDC federation to AWS/GCP/Azure; environment
  secrets behind required reviewers.
- Signed commits/artifacts, two-person review on protected branches where team size allows.
- Pin dependencies and actions by hash; minimal third-party actions; least-privilege
  `permissions:`.
- Audit: keep CI logs, enable audit log streaming in orgs; dependency and IaC scanning.
- Ephemeral, hardened runners (GitHub-hosted, or StepSecurity harden-runner egress audit).

## 4. CISA SBOM minimum elements (2025 draft, finalised 2026)

Generate SPDX or CycloneDX with Syft for each release. The 2026 elements add component
hash, licence, tool name and generation context, and expect the SBOM to be signed by its
author: attach `sbom.spdx.json` / `sbom.cdx.json` and sign them (attestation or cosign).

## 5. CISA Secure by Design and memory safety

Prefer memory-safe languages for new code (Go, Rust, Java/Kotlin, C#, Python, TS). For
C/C++ code, CISA/NSA ask manufacturers to publish a memory-safety roadmap. Secure by
Design pledge goals that a repo can show: MFA, no default passwords, reducing classes of
vulnerability (e.g. parameterised queries, memory safety), timely patching, a published
VDP, CVE transparency, and customer-visible security logs (for SaaS).

## 6. OpenSSF Scorecard and Best Practices badge

Scorecard (public repos) scores 18 checks; it also reports OSPS Baseline coverage. The
Best Practices badge (bestpractices.dev, LF) is self-certification: passing / silver /
gold, and newer baseline-1/2/3 series. The owner must log in with GitHub and submit; an
agent can fill the answers from repo evidence once they are logged in, but must not
create the account or approve OAuth for them. Expected solo-project gaps: Code-Review,
Contributors, Maintained (<90 days old).

## 7. EU Cyber Resilience Act

Applies to products with digital elements placed on the EU market (commercial). Open
source stewards have lighter duties. Reporting obligations start 2026-09-11; full
application 2027-12-11. Relevant artefacts: SBOM, vulnerability handling process,
security updates for the support period, CE documentation for commercial products. The
OSPS Baseline maps to CRA requirements; point SaaS/commercial owners to it and to legal
advice rather than claiming compliance.


## Preset: solo maintainer, private repo, saas-b2b (Level 3)
Do not hand-write the skip list; start from this and edit. Mark in `docs/security/controls.md`:
- Not applicable while private: public discussion/contribution channels, OSI-approved
  licence, public vulnerability disclosure page, public release verification by strangers,
  DCO/sign-off for outside contributors, private vulnerability reporting (publish a
  security email instead).
- Partly met, solo: a second human reviewer (QA-07.01). Compensate with required checks,
  PR-only merges, bypass limited to PR merges, and a dated ADR; revisit at the second hire.
  Never fake it with a second account.
- Met and worth showing: signed images + SBOM per release, SHA-pinned CI, least-privilege
  tokens (job-level `permissions`), OIDC cloud auth, secret scan on history, tested restore.
