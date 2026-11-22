# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-11-22

The project earned the OpenSSF Best Practices passing badge.

### Added

- `jq-repo-setup` asks who owns the code and which licence (never a default; "none yet" is
  allowed and becomes a follow-up), and reports a missing sibling skill as a follow-up with where
  to get it.
- `jq-repo-setup/references/tooling.md` lists what each tool sends out (dependency names to
  OSV, TruffleHog's verification, published Scorecard results, public transparency logs, SaaS
  tools) and the offline or local options.
- `docs/README.md` covers installing, using and securely using the skills.
- The OpenSSF Best Practices passing badge in the README, recorded in `.github/repo-setup.yaml`.

### Changed

- `TOOLS_CONFIG` moves the config root (default `~/.config/jq-tools`); `JQ_TOOLS_CONFIG` is still
  honoured as the older name.
- SECURITY.md no longer says there are no releases; CONTRIBUTING.md states that new functionality
  gets tests.

### Fixed

- `jq-openssf-common/scripts/fill-form.js` ended with a bare string that CodeQL flagged as a useless
  expression; it is now an assignment with the same result.

## [0.2.0] - 2026-11-21

### Changed

- **Breaking:** every skill folder, and so every skill name, now carries the `jq-` prefix:
  `jq-privacy-audit`, `jq-privacy-sandbox`, `jq-privacy-common`, `jq-openssf-passing`,
  `jq-openssf-common` (alongside the existing `jq-repo-setup`). To upgrade from 0.1.0:
  - from a clone, re-run `make link` after removing the old links from `~/.claude/skills` and
    `~/.copilot/skills` (`make link` never overwrites a link it didn't make);
  - for plugin or `npx skills` installs, reinstall to pick up the new names;
  - if your `~/.config/jq-tools/git-init-prompt/config.yaml` lists `openssf-passing`, change it to
    `jq-openssf-passing`.
  Config directories (`~/.config/jq-tools/privacy-audit/` and so on) and the marketplace plugin
  names are unchanged.

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

[Unreleased]: https://github.com/josh-quinn/jq-skills/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/josh-quinn/jq-skills/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/josh-quinn/jq-skills/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/josh-quinn/jq-skills/releases/tag/v0.1.0
