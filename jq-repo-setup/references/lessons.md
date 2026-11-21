# Lessons learned (pitfalls and fixes)

Each of these cost a failed release or a lost hour on a real project.

## GoReleaser
- `goreleaser check` and `--snapshot` builds do not evaluate templates that only run when
  publishing (e.g. Homebrew `token`, `skip_upload`). Two releases shipped without their
  cask because of this.
- Only GoReleaser's own template functions exist: there is no `envOrDefault`. Use
  `index .Env "NAME"` for optional variables.
- `token` fields must be exactly `'{{ .Env.NAME }}'` and nothing else.
- Optional publishing: `skip_upload: '{{ if index .Env "TAP_TOKEN" }}false{{ else }}true{{ end }}'`
  (checked before the token is read).
- Add a unit test that reads `.goreleaser.yaml` and asserts these rules, and test any other
  publish-time template by echoing it in a temporary `before.hooks` entry in a snapshot.
- `actionlint` installed with `go run` needs Go >= 1.25 even if the project supports older Go.

## Homebrew casks
- Ruby blocks (`postflight do ... end`) are deprecated; `postflight_steps` uses a
  declarative DSL. Inside it, `#{staged_path}`, `system_command` and `OS.mac?` fail with
  "cask is unreadable: undefined local variable or method 'staged_path' for an instance of
  Homebrew::InstallSteps::DSL". Correct form:
  ```ruby
  postflight_steps do
    on_macos do
      run "/usr/bin/xattr",
          args:           ["-dr", "com.apple.quarantine", "{{staged_path}}/mytool"],
          writable_paths: ["{{staged_path}}"]
    end
  end
  ```
  In `.goreleaser.yaml` (`homebrew_casks[].hooks.post.install_steps`) escape the Homebrew
  token from Go templates: `{{ "{{staged_path}}" }}`.
- Test it: render with a snapshot, then load the cask with
  `brew ruby -e 'Cask::CaskLoader::FromContentLoader.new(File.read(ARGV[0])).load(config: nil)' cask.rb`
  (Homebrew refuses to load casks from arbitrary paths; content loading works). Skip the
  test if the installed Homebrew predates install steps.

## Releases and tags
- Never move or reuse a published tag (Go's checksum database and users' caches have it).
  Fix forward with the next patch; delete the broken GitHub Release but keep the tag, so
  Scorecard's Signed-Releases only sees complete releases.
- Guard the release workflow: tag must be an ancestor of `origin/main`.
- `go install module@vX` builds have no ldflags; read the version from
  `debug.ReadBuildInfo()` when the stamped version is empty.

## GitHub Actions
- `slsa-github-generator` must be referenced by tag (`@v2.1.0`); slsa-verifier checks the
  builder's tag. Accept Scorecard's one-point Pinned-Dependencies deduction and record it.
- Do not claim a tool exempts something without checking (Scorecard does not exempt the
  SLSA generator).
- Required status check names are job `name:` values; a renamed job silently blocks merges.
- Jobs skipped with `if:` count as passing for required checks; use that for PR-only jobs.
- Scorecard's workflow must not have extra steps that use secrets and needs
  `id-token: write` + `security-events: write` on its job only.
- `concurrency` with `cancel-in-progress` per ref keeps PR runs cheap.

## Tests
- End-to-end tests that drive a real shell/terminal must wait for on-screen markers, not
  sleep; keystrokes sent before the program is ready are lost in CI only.
- Hooks are tested in throwaway repos; fake secrets are generated at runtime from a fixed
  seed so the scanner never sees a real-looking token in the repo.

## Working with the owner
- Agents may be blocked from pushing tags, creating repos, changing account settings or
  installing into the real shell. Prepare exact commands for the owner.
- Creating accounts and approving OAuth (e.g. bestpractices.dev login) is the owner's step;
  filling in a form after they log in is fine with their go-ahead.
- Ask before destructive actions (deleting releases, rewriting history); history rewrites
  of a public repo (e.g. to change a commit email) need explicit approval and a reason.
