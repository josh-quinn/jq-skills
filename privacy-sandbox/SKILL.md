---
name: privacy-sandbox
description: Run a tool, package, MCP server or skill script inside a Docker sandbox with planted fake personal data (fake Slack and OpenAI tokens, SSH key, meeting notes, shell history, agent history) behind a proxy that records and blocks every connection, to see what it actually tries to send and where - including at install time. Use it when the user wants to test, run, watch or "detonate" something to see if it phones home, when a privacy-audit came out "Can't tell" or found obfuscated or minified network code, or when the user accepts the sandbox offer at the end of an audit. Only run it with the user's go-ahead, since it runs the target's code. Not for macOS GUI apps, and not a substitute for reading the code (use privacy-audit first).
---

# Privacy sandbox

A static audit reads what code says; this shows what it does. The target runs in a
container whose only way out is a logging proxy. The proxy forwards only allowed hosts
(package registries by default), blocks the rest, and blocks any request carrying one of
the planted fakes, so the fake data never leaves even when the code tries. A watcher logs
DNS lookups and direct connections that try to go around the proxy.

It runs the target's code. Containers are strong isolation, not perfect isolation, and on
the company laptop running untrusted code may itself be against policy. So:

- Ask the user before every `run`, saying what will be installed and run.
- Never put real credentials, real files or real data into the sandbox. The canaries are
  the data.
- If Docker isn't running, say so and stop; don't start or install anything on the
  user's behalf without asking.

## Before you start

The shared parts are at `<this skill's directory>/../privacy-common` (missing: tell the
user to run the skills repo's `make link`, and stop). Usually there's already an audit
work folder from `privacy-audit`; if not, make one with
`privacy.py init --target <name>`.

```sh
SB="uv run --no-project --with pyyaml python -I <this skill's directory>/scripts/sandbox.py"
```

## A run

1. **Choose what to exercise.** The sandbox only sees code that runs. Pick commands that
   touch personal data the way the user would: import the meeting notes, summarise a
   channel, call the MCP tools. Install is always exercised; for many packages that's
   where the worst behaviour is.

2. **Prepare** (writes files, runs nothing):

   ```sh
   $SB prepare --work <work_dir> --target <source dir>    # or --package npm:<name>@<ver> / pypi:<name>==<ver>
               [--run "<command>"]                        # after install, e.g. "node dist/cli.js import ~/Documents/meeting-notes"
               [--mcp "<server command>" --calls list|auto|calls.json]
               [--mode registries|block|trusted] [--own slack.com] [--allow host,...]
               [--timeout 120] [--linger 8]
   ```

   - `--mode registries` (default) lets the install reach npm and PyPI only. `block`
     forwards nothing (use it when the code is already installed or copied in).
     `trusted` also forwards the profile's trusted domains and `--own`; useful to see
     what a tool does after its own service answers, but the fake tokens will be
     rejected, so later code paths may not run.
   - For an MCP server, `--calls list` only starts it and records its tools (names,
     descriptions, schemas in `logs/tools.json`: read them for hidden instructions).
     `--calls auto` calls every tool with canary text as arguments, which exercises the
     data paths but also any destructive tool, harmlessly, inside the sandbox; say so
     when asking. A JSON file of `[{"name": …, "arguments": {…}}]` calls just those.
   - Planted data: fake tokens in env (`SLACK_BOT_TOKEN`, `OPENAI_API_KEY`,
     `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `NOTION_TOKEN`, `AWS_SECRET_ACCESS_KEY`), and in
     the home folder `~/.ssh/id_ed25519`, `~/.aws/credentials`, `~/.zsh_history`,
     `~/Documents/meeting-notes/…`, `~/.claude/history.jsonl`, `~/.gitconfig` and a Chrome
     cookie file. Standard input and `--calls auto` arguments carry a canary sentence.

3. **Ask, then run**: show the user the target, the install and run commands, the mode,
   and that it runs their code in Docker. On a yes:

   ```sh
   $SB run <sandbox dir>      # builds the image the first time; writes sandbox-report.md
   ```

4. **Read the result.** `sandbox-report.md` says which canaries appeared in which
   request (a fake token sent to its own service is expected use; anything else is
   data that would have left the machine), every host contacted and whether it was
   forwarded or blocked, TLS refusals (pinned certificates: host known, content not),
   bypass attempts, and the tails of the install and run logs. `logs/flows.jsonl` has
   every request with a body preview; `logs/calls.jsonl` has MCP call results.

5. **Fold it into the audit report** as a "Sandbox run" section: what was exercised, what
   was seen, and how it changes the verdict. A canary leaving for an unexpected host is
   a blocker. Nothing seen is evidence for the paths you exercised, not proof for the
   rest: say which paths those were.

6. **Clean up** when done: `$SB clean <sandbox dir>` removes the containers and the
   built image. The folder (logs, report) stays in the work folder.

## Limits to tell the user

- Only exercised code paths are covered. Time bombs, rare flags, server-side switches and
  "phone home after 7 days" aren't.
- Code can detect containers or missing real accounts and behave differently.
- Linux containers only: no macOS GUI apps, no macOS-only binaries. For those, a network
  monitor the user runs (LuLu, Little Snitch) during real use is the dynamic check.
- HTTPS is inspected through the proxy's certificate. A client that pins certificates
  or ignores the proxy settings shows up as a TLS refusal or a bypass attempt, without
  content.
