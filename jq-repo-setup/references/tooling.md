# Tool catalogue

All free and open source unless marked. "Steward" shows who backs it: OpenSSF/LF (Linux
Foundation), CNCF (also LF), OWASP, government, or vendor-maintained OSS. Prefer
foundation-stewarded tools when two tools do the same job. "Private" = works on private
repos at no cost.

Pin versions everywhere (`tool@vX.Y.Z`), and look up the current release when adding a
tool rather than trusting a version from memory.

## Secrets
| Tool | Steward | Use | Private |
|---|---|---|---|
| gitleaks | vendor OSS (MIT) | pre-push hook on the pushed range; CI scan of full history (`gitleaks git --log-opts=--all`) | yes |
| TruffleHog | vendor OSS (AGPL) | optional second opinion; verifies live credentials | yes |
| GitHub secret scanning + push protection | GitHub | free on public repos; private needs Secret Protection (paid) | no |

## Static analysis (SAST)
| Tool | Steward | Use | Private |
|---|---|---|---|
| CodeQL | GitHub | multi-language, as code scanning | public only (private: Code Security, paid) |
| Opengrep (template: `assets/github/workflows/sast-opengrep.yml`) | community fork of Semgrep CE (LGPL-2.1), moving to foundation governance | multi-language rules, taint analysis; runs anywhere | yes |
| gosec / golangci-lint | OSS | Go | yes |
| Bandit, Ruff | PyCQA / OSS | Python | yes |
| ESLint + eslint-plugin-security | OpenJS (LF) | JS/TS | yes |
| clippy, cargo-deny | Rust project / OSS | Rust | yes |
| SpotBugs + FindSecBugs | OSS | Java | yes |

On private repos without Code Security, use Opengrep + the language linter, and upload
SARIF only if code scanning is available; otherwise fail the job on findings.

## Dependencies (SCA) and licences
| Tool | Steward | Use | Private |
|---|---|---|---|
| OSV-Scanner | Google OSS, uses OSV.dev (OSV schema is an OpenSSF project) | all ecosystems, lockfiles, containers; `--fail-on-vuln` | yes |
| govulncheck | Go team | reachability-aware for Go | yes |
| pip-audit | PyPA | Python | yes |
| npm audit / cargo audit | ecosystem | JS / Rust | yes |
| Dependabot (alerts + version updates) | GitHub | all ecosystems incl. github-actions | yes |
| Renovate | Mend OSS (AGPL) | alternative to Dependabot; grouping, automerge rules | yes |
| dependency-review-action | GitHub | blocks PRs adding vulnerable / disallowed-licence deps | public only (private needs Code Security) |
| ScanCode Toolkit | AboutCode (OSS) | licence and copyright detection | yes |
| REUSE | FSFE | SPDX licence headers per file (`reuse lint`) | yes |
| OWASP Dependency-Track | OWASP | SBOM inventory + continuous vuln monitoring (self-hosted; saas-b2b) | yes |

## CI / workflow security
| Tool | Steward | Use |
|---|---|---|
| actionlint | OSS | workflow syntax + shellcheck of `run:` (needs Go >= 1.25 to `go run`) |
| zizmor | OSS (MIT) | workflow security: template injection, credential persistence, excessive permissions, unpinned actions, dangerous triggers. `zizmor --format sarif` |
| scripts/pin-actions.sh | this skill | pin all `uses:` to SHAs |
| StepSecurity harden-runner | vendor OSS action | egress audit/block on runners; free for public repos |
| Allstar | OpenSSF | GitHub App enforcing repo policies across an org |
| Minder | OpenSSF (sandbox) | policy-as-code for repo settings across many repos |
| shellcheck | OSS | shell scripts and hooks |

## Supply chain, signing, provenance
| Tool | Steward | Use | Private |
|---|---|---|---|
| Sigstore cosign | OpenSSF (graduated) | keyless signing of blobs and container images via OIDC | yes, but writes to the public Rekor log (reveals artifact hashes and repo identity) |
| actions/attest-build-provenance | GitHub + Sigstore | SLSA build provenance attestations; `gh attestation verify` | public; private needs Enterprise Cloud |
| slsa-github-generator | OpenSSF SLSA | SLSA L3 provenance (`*.intoto.jsonl`); reference by tag | public (private: `private-repository: true`, still public log) |
| slsa-verifier | OpenSSF | verify SLSA provenance | - |
| Syft | Anchore OSS | SBOM (SPDX, CycloneDX) for source, binaries, images | yes |
| vexctl / OpenVEX | OpenSSF | VEX statements | yes |
| GUAC | OpenSSF | aggregate SBOM/provenance graphs (larger orgs) | yes |

## Containers and infrastructure (app / saas-b2b)
| Tool | Steward | Use |
|---|---|---|
| Trivy | Aqua OSS (Apache-2.0) | image, filesystem, IaC (Terraform, K8s, Dockerfile) misconfig and vuln scanning |
| Grype | Anchore OSS | image vulns from Syft SBOM |
| Hadolint | OSS | Dockerfile lint |
| Checkov | Prisma OSS | IaC policy scanning |
| Conftest / OPA | CNCF (graduated) | custom policy-as-code for configs |
| kube-linter / kube-bench | OSS | Kubernetes manifests / CIS benchmark |
| Falco | CNCF (graduated) | runtime threat detection |
| Distroless / Chainguard / Wolfi images | OSS images | minimal base images |

## Dynamic testing
| Tool | Steward | Use |
|---|---|---|
| ZAP (Zed Attack Proxy) | Checkmarx-sponsored OSS (formerly OWASP) | DAST baseline scan against a preview/staging URL in CI |
| Native fuzzing (go test -fuzz, cargo-fuzz, Atheris, Jazzer) | language projects | parsers and input handling; short runs in CI |
| OSS-Fuzz / ClusterFuzzLite | Google OSS | continuous fuzzing; ClusterFuzzLite runs in GitHub Actions |
| Schemathesis | OSS | property-based API testing from OpenAPI |
| k6 | Grafana OSS | load tests (saas-b2b) |

## Scoring and attestation
| Tool | Steward | Use |
|---|---|---|
| OpenSSF Scorecard (+ action, weekly + on push to main) | OpenSSF | 18 checks + OSPS Baseline coverage; public repos |
| Privateer + GitHub repo scanner (pvtr) | OpenSSF / FINOS | OSPS Baseline control checks; reads SECURITY-INSIGHTS.yml |
| Best Practices badge | OpenSSF (bestpractices.dev) | self-certification; owner must log in |
| Security Insights spec | OpenSSF | `SECURITY-INSIGHTS.yml` machine-readable security metadata |

## Commit hygiene and releases
| Tool | Use |
|---|---|
| `assets/githooks/commit-msg` | Conventional Commits check (shell, no deps); also run in CI per PR commit |
| commitlint | alternative for JS projects already on Node |
| DCO GitHub App / `git commit -s` | contributor sign-off (OSPS-LE-01.01) |
| release-please (Google OSS) | release PRs + CHANGELOG from Conventional Commits; good for libraries and long-lived apps |
| GoReleaser (OSS edition) | Go binaries, archives, Homebrew casks, SBOMs, signing |
| cargo-dist, PyPI trusted publishing, npm provenance (`npm publish --provenance`) | per-ecosystem releases with provenance |
