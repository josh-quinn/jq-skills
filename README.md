# jq-skills

My agent skills for Claude Code, GitHub Copilot and other agents that read `SKILL.md`. Each
skill is a top-level folder; skills that share material read a `*-common` folder from beside
their own, so install a group together.

| Skill | Group | Does |
|---|---|---|
| [`privacy-audit`](privacy-audit/SKILL.md) | privacy-audit | Reads a skill, plugin, MCP server, package, app or extension without running it, traces where your data goes, and writes a report with a verdict. |
| [`privacy-sandbox`](privacy-sandbox/SKILL.md) | privacy-audit | With your go-ahead, runs the target in Docker with planted fake data behind a proxy that records and blocks every connection. |
| [`privacy-common`](privacy-common/SKILL.md) | privacy-audit | Shared: the `privacy.py` helper, policy and verdicts, report template, safe fetching. |
| [`jq-repo-setup`](jq-repo-setup/SKILL.md) | jq-repo-setup | Sets up or hardens a repo with engineering, security and supply-chain practices using free and open-source tooling. Also holds the optional git-init prompt. |
| [`openssf-passing`](openssf-passing/SKILL.md) | openssf-badges | Takes a project to the OpenSSF Best Practices "passing" badge, honestly (draft). |
| [`openssf-common`](openssf-common/SKILL.md) | openssf-badges | Shared: live criteria, answers checker, proposal URLs, workflow and honesty rules. |

More on each: [privacy audit](docs/privacy-audit-skills.md), [jq-repo-setup](docs/jq-repo-setup.md),
[OpenSSF badges](docs/openssf-badge-skills.md).

## Install

As Claude Code plugins, one per group:

```sh
/plugin marketplace add josh-quinn/jq-skills
/plugin install privacy-audit --marketplace josh-quinn/jq-skills
/plugin install jq-repo-setup --marketplace josh-quinn/jq-skills
/plugin install openssf-badges --marketplace josh-quinn/jq-skills
```

With the [Skills CLI](https://skills.sh/), for Claude Code, Copilot and other agents (pick every
skill in a group):

```sh
npx skills add josh-quinn/jq-skills
```

From a clone, for development:

```sh
make link     # symlinks each skill into ~/.claude/skills and ~/.copilot/skills
make unlink   # removes those links
```

`make link` never overwrites a folder or a link it didn't make. Requires `uv` (or Python 3.11+
with PyYAML). The privacy sandbox needs Docker (Docker Desktop or OrbStack).

## Configuration

Config for each tool lives in `~/.config/jq-tools/<tool>/config.yaml`, created on first use and
never rewritten. Set `JQ_TOOLS_CONFIG` to use another root, as the tests do.

## Develop

```sh
make hooks          # once per clone: Conventional Commits on commit, gitleaks on push
make check          # unit tests and basic skill checks; no network, no Docker
make sandbox-smoke  # a real sandbox run against a planted leaky package (needs Docker)
```

See [AGENTS.md](AGENTS.md) for the rules and [CONTRIBUTING.md](CONTRIBUTING.md) for the
workflow. Skill evals live in each skill's `evals/` folder (the `claude plugin eval` layout)
and use planted fixtures.
