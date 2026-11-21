# 0003. Make the repository public under the MIT licence

- **Status**: Accepted
- **Date**: 2026-11-21

## Context

ADR 0002 skipped the licence, the code of conduct and the public-only workflows because
visibility was undecided. The repository now holds all the owner's skills (privacy audit,
repo setup, OpenSSF badges), and installing them on other machines and sharing them is the
point. Private-repo installs need git credentials on every machine, and the skills.sh and plugin
directories only list public repositories.

## Decision

- We will make the repository public under the MIT licence.
- We will add `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1) and route security reports to
  GitHub private vulnerability reporting.
- We will turn on secret scanning, push protection and Dependabot alerts, and add the
  public-only workflows (CodeQL, Scorecard, dependency review).
- Commit history is kept as is, including the author email on earlier commits.

## Consequences

This supersedes the "skipped" list in ADR 0002 for LICENSE, CODE_OF_CONDUCT and the
public-only workflows. Skills must stay generic (see `AGENTS.md`): nothing personal or
company-specific goes in a skill, because everything is now world-readable.

## Alternatives considered

- **Apache-2.0**: adds a patent grant, which these skills don't need.
- **Stay private**: works for the owner's own machines, but blocks sharing and listing.
