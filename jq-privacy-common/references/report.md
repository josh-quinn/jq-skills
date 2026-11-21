# Report template

Write the report to `<work dir>/report.md` (from `privacy.py init`). Keep it readable by
someone who doesn't write code: say what happens to their data in plain words, and put
the file and line evidence right after each claim. Leave out a section that would be
empty, except Coverage.

```markdown
# Privacy audit: <target> <version or commit>

**Verdict: <Local only | Needs your decision | Do not use | Can't tell>.** <One or two
sentences: what happens to your data, and the main reason for the verdict.>

<date> · profile <work|personal> · <static | static and sandbox> · source <URL or path, version, commit>

## What it does with your data

<Two to five plain sentences: what the tool reads, what it keeps, and where it sends it.>

| Your data | How it gets it | Stays local? | Goes to |
|---|---|---|---|
| Slack messages | Slack API with your bot token | cached in ~/.slack-mcp/cache.db | slack.com only |

## Where it connects

| Host | Kind | What is sent | When | Disclosed? | Evidence |
|---|---|---|---|---|---|
| slack.com | own service | your token, channel IDs | every tool call | yes, README | src/slack.ts:40 |
| us.i.posthog.com | telemetry | your email, tool names | every start, on by default | no | src/telemetry.ts:12 |

## What it keeps on this machine

| Where | What | Protection | Synced or shared? |
|---|---|---|---|

## Findings

### 1. <Short title> (blocker | decide | note)

<What happens, in plain words.> Evidence: `path/file.ts:12`

    <the few lines of code that show it>

<Why it matters to the user, and what would fix it.>

## Your decisions

- [ ] <Something the user must choose, with what they get and what it costs.
      For example: allow meeting transcripts to go to api.openai.com for summaries;
      turn it off with SUMMARY_PROVIDER=none.>

## Making it safer

- <Concrete settings, environment variables, a pinned version, a firewall rule, or a
  different tool.>

## Coverage

- Read: <the files and folders you read in full, and how many of the scanner's leads you checked>
- Not read: <minified bundles, binaries, large vendored folders; why>
- Dependencies: <which were checked and how>
- Dynamic check: <sandbox run and what it exercised, or "none">
- Would change the verdict: <for example, a sandbox run, or the author confirming X>
```

## In chat

After writing the file, give the user the short version in the conversation: the verdict
line, the findings that are blocker or decide (one line each), the decisions you need
from them, and the path to the full report. Offer the sandbox when the verdict is Can't
tell or when a finding depends on code you couldn't follow.

## A later audit of the same target

`privacy.py init` returns `previous_report` when there is one. Read it, and add a
"Changes since <date>" section after the verdict: new hosts, findings that appeared or
went away, decisions the user made last time that still apply.
