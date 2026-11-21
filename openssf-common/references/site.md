# bestpractices.dev: sources, data and the form

## Where the criteria come from

All from `https://raw.githubusercontent.com/ossf/best-practices-badge/<ref>/`. `badge.py init`
fetches them at one commit and records it in `source.json`.

| File | Holds |
|---|---|
| `criteria/criteria.yml` | Metal series (`'0'` passing, `'1'` silver, `'2'` gold): `category` (MUST/SHOULD/SUGGESTED), `na_allowed`, `met_url_required`, `met_justification_required`, `na_justification_required`, `future`, `obsolete`, plus `rationale` and `autofill` notes. Uses `!!omap`. |
| `config/locales/en.yml` | Wording: `en.criteria.<level>.<key>.description` and `details` |
| `criteria/baseline_criteria.yml` | OSPS Baseline (`baseline-1..3`); keys like `osps_ac_03_01`, with `original_id` `OSPS-AC-03.01` |
| `criteria/metal_to_baseline_map.yml` | Which metal criterion's evidence serves which baseline control |

Upstream docs worth reading when the site behaves unexpectedly: `docs/automation-proposals.md`,
`docs/api.md`, `docs/bestpractices-json.md`.

## A project's saved answers

`https://www.bestpractices.dev/projects/<id>.json` (`badge.py project`). It has `<key>_status`
and `<key>_justification` for every criterion, and `badge_percentage_0|1|2` and
`badge_percentage_baseline_1|2|3`. Baseline readbacks use the OSPS id (`OSPS-AC-01.01_status`);
`badge.py` handles both forms. Find a project by URL with
`/en/projects.json?url=<encoded repo URL>`. Read this JSON rather than scraping the form.

## Proposal URLs (the preferred way to fill the form)

The site supports tools proposing answers through the edit URL: the form opens with the
proposals filled in and highlighted, and nothing is stored until a person saves.

- `https://www.bestpractices.dev/en/projects/<id>/<level>/edit?<key>_status=Met&<key>_justification=...`,
  where level is `passing`, `silver`, `gold`, `baseline-1`, `baseline-2` or `baseline-3`.
  Without an id: `/en/projects?as=edit&url=<encoded repo URL>&section=<level>&...`.
- Proposals for fields not on that level's form are silently ignored.
- Unforced proposals only fill blank (`?`) fields. To replace an existing answer, the key must
  be in `overrides=<key>_status,...`; its justification follows its status. `badge.py urls`
  forces exactly the answers that differ from `project.json`, so refresh that file first.
- Highlights: yellow 🤖 = filled a blank; orange ⚠️ = replaced an answer (click to see the old
  one); blue ≠ = a different proposal that was not applied.
- In a URL, `?` resets a field, so `badge.py urls` never proposes `?`.
- Not logged in: the site keeps the URL, sends the user to log in, then brings them back with
  the proposals intact. Not authorised for that project: it shows the read-only page.
- URLs are split at about 6,000 characters (`max_url_length` in the config) to stay under
  common server limits. If the site still rejects one (an error page, or proposals missing),
  lower `--max-length` and rebuild.
- Proposals live only in the open page until it is saved, and are not re-applied on later
  saves. Save each URL before opening the next.

## The form, mechanically

- The edit page is `/en/projects/<id>/<level>/edit`. The page without `/edit` is read-only and
  has no form; a redirect after saving can leave you there.
- New project: `/en/projects/new`, which needs the user logged in (GitHub OAuth). If the repo is
  already registered it redirects to the existing project and says "This project already
  exists!"
- Fields: radios `project[<key>_status]` with values `Met`, `Unmet`, `N/A` and `?`; textareas
  `project[<key>_justification]`. Baseline keys are the `osps_` form.
- Buttons: `name="continue" value="Save"` saves and stays ("Save and continue": the site's
  automation re-runs and shows its highlights). `name="commit"` is "Submit (and exit)". Use Save.
- After saving, the flash says "Project was successfully updated." or "CONGRATULATIONS on
  earning a ... badge!"
- "not enough for a badge" next to a Met means the required URL or justification is missing.

## The site's own automation ("Chief" and the detectives)

- On the first edit of a level, and on each Save, the site analyses the repository and proposes
  or forces answers. It reads the **default branch**, and mostly only top-level files plus files
  directly in `docs/`. When it's confident (e.g. no CONTRIBUTING file means `contribution`
  can't be Met), it overrides the answer on every save.
- "Automation instead determined Unmet" means it disagrees with a saved answer. Fix the
  repository so the evidence is where the automation looks. Don't argue with it in the
  justification.
- `SECURITY-INSIGHTS.yml` at the repo root, and a `.bestpractices.json` if present, feed the
  automation. Their autofilled justifications often lack the URL a criterion requires. Check
  them and supply your own.

## Claude in Chrome

- Load the browser tools in one ToolSearch call; start with `tabs_context_mcp`; use a new tab.
- Tool output that contains URLs or query strings is blocked (`[BLOCKED: Cookie/query string
  data]`), and output is cut off at about 1,000 characters. Return statuses, counts and keys,
  never justification text or links. Use the project JSON to read answers back.
- Navigating to a proposal URL is fine: the block applies to what tools return, not to what
  you send.
- Fallback when proposal URLs fail: `scripts/fill-form.js` with `javascript_tool` on the edit
  page. Paste the file, then `osb.fill(<payload>)` with `badge.py payload answers.yaml --keys ...`
  in chunks of about 15 criteria, then `osb.save()` (only on the go-ahead), then paste the file
  again after the reload and run `osb.remaining()`. In fill results, `no N/A option: <key>`
  means that criterion has no N/A.
- Never type the user's credentials, and never get past a login or 2FA page for them. If a
  login page appears, hand over to the user.
