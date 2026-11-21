# 0002. Set up repository standards

- **Status**: Accepted
- **Date**: 2026-11-21

## Context

The repository holds three agent skills, is maintained by one person, and its visibility
(public or private) and licence are not decided yet. It is a small tool-like project, so the
setup is proportionate: OpenSSF OSPS Baseline level 1 plus the level 2 controls that suit a
private, solo repository.

## Decision

- Conventional Commits (hook and CI), secret scanning on push (hook) and in CI (full history),
  workflow linting, `make check` in CI.
- All actions pinned by commit SHA; Dependabot for `github-actions` only (no Python manifest).
- Skipped on purpose: LICENSE and CODE_OF_CONDUCT (visibility and licence undecided), CodeQL,
  Scorecard and dependency review (public-only), second-reviewer rules (solo), release signing
  and SBOM (nothing is released; skills are installed by `make link`).

## Consequences

Going public needs a licence choice, a code of conduct and the public-only workflows; see
`.github/repo-setup.yaml`.
