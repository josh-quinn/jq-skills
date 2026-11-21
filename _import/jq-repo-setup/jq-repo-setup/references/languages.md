# Per-language toolchain

For each language: format, lint (incl. security), test, vulnerabilities, fuzz, release.
Add the commands to the Makefile/justfile/package scripts and to CI. Test on the minimum
supported version and the latest.

## Go
- format: `gofmt -l .` must be empty; `go vet ./...`
- lint: golangci-lint v2 with `gosec`, `errcheck`, `staticcheck`, `revive`, `errorlint`
- test: `go test -race -count=1 -coverprofile=coverage.out ./...` (`-count=1` stops cached
  results hiding real runs of integration tests)
- vulns: `govulncheck ./...` (pin `golang.org/x/vuln/cmd/govulncheck@vX`)
- fuzz: native `func FuzzX(f *testing.F)`; CI runs each target briefly
  (`go test -run=^$ -fuzz=^FuzzX$ -fuzztime=20s ./pkg`), one target per invocation
- release: GoReleaser (archives, checksums, SBOM via syft, Homebrew cask, signing);
  stamp version with ldflags and fall back to `debug.ReadBuildInfo()` for `go install`
- Dependabot ecosystems: `gomod`, `github-actions`

## Python
- format/lint: Ruff (`ruff format --check`, `ruff check` with `S` (bandit) rules) or Black + Bandit
- types: mypy or pyright
- test: pytest + coverage; hypothesis for property tests
- vulns: `pip-audit` (or OSV-Scanner on the lockfile)
- fuzz: Atheris
- packaging: `pyproject.toml`, uv or pip-tools lockfile; publish with PyPI trusted
  publishing (OIDC) from a tag workflow, `pypa/gh-action-pypi-publish` with attestations
- Dependabot: `pip` / `uv`, `github-actions`

## JavaScript / TypeScript
- format/lint: Prettier (or Biome), ESLint with `eslint-plugin-security`, `tsc --noEmit`
- test: Vitest or Jest; Playwright for end-to-end web tests
- vulns: `npm audit --audit-level=high` or OSV-Scanner on `package-lock.json`/`pnpm-lock.yaml`
- install in CI with `npm ci` / `pnpm install --frozen-lockfile`; consider
  `--ignore-scripts` and an allow-list for packages that need install scripts
- release: `npm publish --provenance` via OIDC, or release-please
- Dependabot: `npm`, `github-actions`, plus `docker` if there is a Dockerfile; group
  minor/patch updates to cut noise
- Before pinning versions, check peer ranges (`npm view typescript-eslint peerDependencies`):
  the newest TypeScript is often outside what typescript-eslint supports, and "latest of
  each" gives a broken install. Generate the lockfile with network access and commit it
  (`npm ci` fails without one).
- CI tools written in Go (actionlint, gitleaks, osv-scanner) need `setup-go` on a Node
  repo; or run them as digest-pinned container images and skip the extra action.

## Rust
- `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo test`
- vulns + licences + bans: `cargo deny check` (advisories from RustSec)
- fuzz: cargo-fuzz; releases: cargo-dist (Homebrew, installers) or `cargo publish`
- Dependabot: `cargo`

## Java / Kotlin
- Gradle/Maven wrapper committed and verified (`gradle/actions/wrapper-validation`)
- lint: Spotless, Error Prone, SpotBugs + FindSecBugs
- test: JUnit 5; vulns: OSV-Scanner or OWASP Dependency-Check
- fuzz: Jazzer; Dependabot: `gradle` / `maven`

## Shell and hooks
- shellcheck every script and hook; POSIX `sh` for hooks so they run everywhere

## Containers / IaC (any language)
- Dockerfile: Hadolint; multi-stage build, non-root user, pinned base image by digest,
  distroless/minimal base; scan the image with Trivy or Grype in CI
- Terraform/K8s/Helm: Trivy config or Checkov; `terraform fmt -check`, `tflint`
- Dependabot: `docker`, `terraform`
