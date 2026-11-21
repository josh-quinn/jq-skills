# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-21

First release. The repository is public under the MIT licence.

### Added

- `privacy-audit`, `privacy-sandbox` and `privacy-common`: check a skill, plugin, MCP server,
  package, app or extension before trusting it with your data, by reading the code and, with your
  go-ahead, watching it in a Docker sandbox.
- `jq-repo-setup`: set up or harden a repository with engineering, security and supply-chain
  practices; includes the optional git-init prompt (`make install-shell`).
- `openssf-passing` and `openssf-common`: take a project to the OpenSSF Best Practices passing
  badge, honestly. `badge.py` gained `answers` (skeleton) and a `project_status` report.
- A Claude Code marketplace with three plugins (`privacy-audit`, `jq-repo-setup`,
  `openssf-badges`), also installable with `npx skills add`.
- MIT licence, code of conduct, security policy, decision records, CI (tests, ruff, gitleaks,
  actionlint, zizmor, CodeQL, Scorecard, dependency review).

### Fixed

- The MCP driver in the sandbox waited out its timeout when a server wrote more than one line at
  once.
- The git-init prompt printed `_gip_target: command not found` in shells that keep `git` but not
  its helper functions.

[Unreleased]: https://github.com/josh-quinn/jq-skills/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/josh-quinn/jq-skills/releases/tag/v0.1.0
