# Privacy audit skills

Agent skills (Claude Code, GitHub Copilot) that check a tool **before you trust it with your
data**: whether a skill, plugin, MCP server, package, desktop app or extension stores or
sends your messages, meeting notes, files, prompts, tokens or company code anywhere other
than this machine and the service it exists for.

Calling the service a tool is for is expected (a YouTube skill calls YouTube; a Slack MCP
calls Slack). Everything else is reported so you can decide: telemetry, AI providers,
the author's servers, cloud storage, hidden endpoints, install scripts that phone home,
and skill instructions that make the agent send things.

| Skill | Does |
|---|---|
| [`privacy-audit`](privacy-audit/SKILL.md) | Reads the code without running it, traces where personal data goes, and writes a report with a verdict. Can also triage everything already installed. |
| [`privacy-sandbox`](privacy-sandbox/SKILL.md) | Optional, with your go-ahead: runs the target in Docker with planted fake data behind a proxy that records and blocks every connection, so you see what it actually tries to send. |
| [`privacy-common`](privacy-common/SKILL.md) | Shared: the `privacy.py` helper, the policy and verdicts, the report template, safe fetching. |

Install all three together; the other two read `privacy-common` from beside their folders.

## Verdicts

- **Local only**: your data stays on this machine or goes only to the tool's own service
  and hosts you trust.
- **Needs your decision**: something legitimate but yours to approve, such as transcripts
  to an AI provider, disclosed telemetry, or a remote MCP operator.
- **Do not use**: undisclosed sending, credential harvesting, hidden instructions, remote
  code, or text trying to talk the auditor out of it.
- **Can't tell**: significant code couldn't be read; the sandbox can help.

## Configuration

`~/.config/jq-tools/privacy-audit/config.yaml`, created on first use and never rewritten:

- `data_dir`: where reports go, as `<data_dir>/<target>/<date>/report.md`
  (default `~/development/privacy-audits`).
- `profiles.work` and `profiles.personal`: `trusted_domains`, `approved_ai_endpoints`, and
  `own_service` (`trusted` on personal; `confirm` on work, so a tool's own service still
  needs your OK on the company laptop).
- `profile: auto` with `work_computer_names: ["ACME-*"]` picks the work profile by computer
  name. `PRIVACY_AUDIT_PROFILE=work` overrides it for one run.

## Install

As a Claude Code plugin (installs all three skills together):

```sh
/plugin marketplace add josh-quinn/privacy-audit-skills
/plugin install privacy-audit --marketplace josh-quinn/privacy-audit-skills
```

From a clone, for development:

```sh
make link     # symlinks each skill into ~/.claude/skills and ~/.copilot/skills
make unlink   # removes those links
```

Requires `uv` (or Python 3.11+ with PyYAML). The sandbox needs Docker (Docker Desktop or
OrbStack); its images are `mitmproxy/mitmproxy:12.2.1`, `nicolaka/netshoot:v0.14`, and a local
build from `python:3.13-slim-bookworm` and `node:22-bookworm-slim`.

## Develop

```sh
make check          # unit tests and basic skill checks; no network, no Docker
make sandbox-smoke  # a real sandbox run against a planted leaky package (needs Docker)
```

Skill evals live in `privacy-audit/evals/` (the `claude plugin eval` layout). They audit
planted fixtures and never run them.
