# GitHub plans, settings and gh commands

Plans and prices change; when a feature matters, confirm on GitHub's pricing/docs pages
instead of trusting this table.

## Feature availability

| Feature | Public (any plan) | Private, Free | Private, Pro / Team | Private, needs |
|---|---|---|---|---|
| Rulesets / branch protection, required checks, required reviews, CODEOWNERS enforcement | yes | no | yes | - |
| Actions minutes | unlimited (standard runners) | 2,000/mo | Pro 3,000/mo, Team 3,000/mo | macOS uses 10x, Windows 2x |
| Dependabot alerts, security updates, version updates | yes | yes | yes | - |
| Secret scanning + push protection | yes | no | no | Secret Protection (Team/Enterprise orgs) |
| CodeQL code scanning, dependency review action | yes | no | no | Code Security (Team/Enterprise orgs) |
| Private vulnerability reporting | yes | n/a | n/a | - |
| Artifact attestations (`attest-build-provenance`) | yes | no | no | Enterprise Cloud |
| Environments with required reviewers / wait timers | yes | no | Pro: limited, Team: yes | - |
| Scorecard, Best Practices badge | yes | meaningless | meaningless | - |

GitHub Student Developer Pack includes GitHub Pro.

Environment protection on private repos varies by plan and changes over time. Probe rather
than assume: create the environment, then `gh api -X PUT repos/$R/environments/production
--input env.json` with `reviewers`; a 422/403 means the rule is unavailable. Fallback: a
tag ruleset (only `main` may create `v*` tags) plus a deploy workflow that runs only on
those tags, and record the gap in `controls.md`.

Consequences for private repos without paid security add-ons: replace CodeQL with
Opengrep + language linters, dependency-review with OSV-Scanner `--fail-on-vuln` on PRs,
push protection with the gitleaks pre-push hook + CI scan, attestations with cosign
(knowing it writes to the public Rekor log) or simply checksums + a private release.
Save minutes: run the full OS matrix only on pushes to main, Linux-only on PRs.

## Repository settings (show the owner, then apply)

```sh
R=OWNER/REPO
# merge strategy: pick one and say why (merge commits keep small commits; squash keeps main linear)
gh repo edit $R --enable-merge-commit --enable-squash-merge=false --enable-rebase-merge=false \
  --delete-branch-on-merge --enable-auto-merge
# security features (public repos; some are no-ops or errors on private Free/Pro)
gh api -X PUT repos/$R/vulnerability-alerts
gh api -X PUT repos/$R/automated-security-fixes
gh api -X PUT repos/$R/private-vulnerability-reporting          # public only
gh api -X PATCH repos/$R -F 'security_and_analysis[secret_scanning][status]=enabled' \
  -F 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
# GITHUB_TOKEN read-only by default; Actions may not approve PRs
gh api -X PUT repos/$R/actions/permissions/workflow -f default_workflow_permissions=read \
  -F can_approve_pull_request_reviews=false
```

## Ruleset for the default branch

Apply only after CI has run green once, so the check names exist. `required_status_checks`
contexts are the job `name:` values exactly as shown on a PR, matched literally
(commas, parentheses and spaces included). Read the real names from a finished run
instead of retyping them: `gh api repos/$R/commits/$SHA/check-runs --jq '.check_runs[].name'`.
Simple names (`test`, `lint`, `secrets`) avoid mismatches; a required check that never
reports blocks every merge.

```json
{
  "name": "protect main",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}],
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 1,
      "require_code_owner_review": true,
      "dismiss_stale_reviews_on_push": true,
      "require_last_push_approval": false,
      "required_review_thread_resolution": true,
      "allowed_merge_methods": ["merge"]}},
    {"type": "required_status_checks", "parameters": {
      "strict_required_status_checks_policy": false,
      "required_status_checks": [{"context": "test"}, {"context": "lint"}]}}
  ]
}
```

```sh
gh api -X POST repos/$R/rulesets --input ruleset.json        # create
gh api repos/$R/rulesets --jq '.[] | {id,name}'               # find id
gh api -X PUT repos/$R/rulesets/ID --input ruleset.json       # update
```

### Solo maintainer pattern
A solo owner cannot approve their own PRs. Options, in order of preference:
1. Require 1 code-owner approval with an admin bypass in `pull_request` mode (bypass only
   when merging a PR, never direct pushes). Owner merges with `gh pr merge --admin --merge`
   only after checks pass. Outside contributions still need the owner's review. Scorecard
   discounts the bypass (Branch-Protection ~4) but this is honest.
2. Require PRs and checks, 0 approvals (simplest; lower Branch-Protection score).
Never create a second account to self-approve: it fakes Code-Review evidence.
Bot PRs (Dependabot) need the same `--admin` merge, or auto-merge rules via a workflow
only for patch updates with passing checks.

`bypass_actors` actor_id 5 = Repository admin role. For teams, drop the bypass and add a
second maintainer to CODEOWNERS.

## Fork PRs
- Default "Require approval for first-time contributors" for workflow runs: keep it.
- Fork PRs get no secrets and a read-only token; keep it that way (no `pull_request_target`
  that checks out PR code).

## Tokens the owner may need to create (agent must not create or enter them)
- Fine-grained PAT, single repository, minimal permission (e.g. Contents: read/write on a
  Homebrew tap), short expiry; stored with `gh secret set NAME` by the owner.
- Prefer OIDC (`id-token: write`) to cloud providers and registries (PyPI trusted
  publishing, npm provenance, AWS/GCP/Azure federation) over stored secrets.
