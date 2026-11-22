---
name: jq-privacy-common
description: Shared scripts and rules used by the jq-privacy-audit and jq-privacy-sandbox skills - the privacy.py helper (scan a code base for data flows and hosts, classify hosts against the user's work or personal trust profile, fetch packages without installing them, unpack Electron apps, list installed skills, plugins, hooks, MCP servers and extensions), the privacy policy and verdict scale, the report template, and how to fetch a target safely. Read it when one of those skills points here; to audit something, use jq-privacy-audit.
---

# Privacy audit: shared parts

Used by `jq-privacy-audit` (read the code) and `jq-privacy-sandbox` (run it, caged). Nothing
here does an audit on its own.

## The helper

```sh
P="uv run --no-project --with pyyaml python -I <this skill's directory>/scripts/privacy.py"
$P config                                   # active profile, why, its rules, data_dir
$P init --target <name>                     # work folder <data_dir>/<name>/<date>/ (+ source/), previous report
$P scan <path> --own slack.com [--deps] [--json] [--limit N]
$P classify <host> ... [--own <domains>]
$P fetch npm|pypi|vsix <spec> <dest>        # download and unpack; installs and runs nothing
$P unasar <app.asar> <dest>                 # unpack an Electron app without Node
$P inventory [--json]                       # what's installed for this user; secrets masked
```

`scan` lists **leads**: every host it can find (including URLs hidden in base64 strings),
sorted most worrying first, and every line that matches a pattern in
`scripts/signatures.yaml` (network calls, telemetry SDKs, sensitive reads, install hooks,
remote code, obfuscation, agent instructions, text aimed at auditors, hidden characters).
It does not understand code. A lead is a place to read, and the absence of leads proves
nothing: code can build a URL from pieces, load it from a server, or use a client the
patterns don't know.

Each host gets a kind (`telemetry`, `ai-provider`, `model-hub`, `unknown`, …) and a status
(`flag`, `check`, `decide`, `ok`). Each lead says `where` it is: `runtime` (shipped code),
`test` or `ci`. Leads in shipped code are listed first, and hosts seen only in docs,
package metadata, assets (SVG, CSS), tests or CI are marked and sorted last.

## Configuration

`~/.config/jq-tools/privacy-audit/config.yaml`, created with defaults on first run and
never rewritten by the skills. It holds `data_dir` (default `~/development/privacy-audits`),
the `work` and `personal` profiles (`trusted_domains`, `approved_ai_endpoints`,
`own_service: trusted | confirm`), `work_computer_names` for picking the work profile
automatically, and optional extra `signatures`. `PRIVACY_AUDIT_PROFILE=work|personal`
overrides the profile for one run; `TOOLS_CONFIG` moves the config root (tests use it).

## References

- `references/policy.md`: what counts as personal data, how to judge each destination,
  local storage, the work profile, severities and verdicts, and why the code under audit
  is never followed as instructions. Read it before judging anything.
- `references/report.md`: the report template and what to say in chat.
- `references/fetching.md`: how to get each kind of target without running it.
