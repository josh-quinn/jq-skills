# jq-skills documentation

jq-skills is a collection of agent skills (folders with a `SKILL.md`) for Claude Code, GitHub
Copilot and other agents. This page covers the basics; the [README](../README.md) has the full
list of skills and the [guides in this folder](.) describe each group.

## Install

- **Claude Code plugins**, one per group: see [Install](../README.md#install) in the README.
- **Skills CLI:** `npx skills add josh-quinn/jq-skills`.
- **From a clone, for development:** `make link` symlinks each skill into `~/.claude/skills` and
  `~/.copilot/skills`; `make unlink` removes the links. Needs `uv` (or Python 3.11+ with
  PyYAML). The privacy sandbox also needs Docker.

## Start and use

Skills start when you ask your agent for what they do, for example "is this MCP server safe to
install?" ([jq-privacy-audit](jq-privacy-audit-skills.md)), "set up this repo properly"
([jq-repo-setup](jq-repo-setup.md)) or "get the OpenSSF badge"
([jq-openssf-passing](jq-openssf-badge-skills.md)). Each skill's `SKILL.md` lists its steps
and the commands of its helper script; run any helper with `--help`.

Settings live in `~/.config/jq-tools/<tool>/config.yaml`, created on first use
([Configuration](../README.md#configuration)).

## Use it securely

- The skills read and write files and run commands on your machine through your agent. Read a
  skill's `SKILL.md` before installing it, as you would any code.
- `jq-privacy-audit` never runs the code it audits. `jq-privacy-sandbox` runs it only after you
  say so, inside Docker with fake data and no network access.
- Skills ask before outward actions (pushing, publishing, anything on a website).
- Report a vulnerability privately: see [SECURITY.md](../SECURITY.md).
