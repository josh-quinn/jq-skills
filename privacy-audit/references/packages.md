# CLI tools and libraries

## When code runs

- **Install time**: npm `preinstall`, `install`, `postinstall` and `prepare` scripts;
  Python `setup.py`, a custom `cmdclass`, or an unusual build backend; Rust `build.rs`;
  Homebrew `post_install`. The scan's `install-hook` category finds most of these. Read
  every one in full: a network call at install time is almost never needed and is a
  blocker unless it only downloads a documented binary from the project's own releases.
- **Import time**: top-level code in a library's entry module runs when anything imports
  it. Telemetry initialised at import is common.
- **Run time**: the commands themselves.

## Where data leaves through a package

- **Telemetry and analytics**: PostHog, Segment, Mixpanel, Amplitude and others; often on
  by default with an opt-out. Find the event payload: does it include file paths, command
  arguments, repo names, the git email, a machine ID? Find the off switch (`DO_NOT_TRACK`,
  a `*_TELEMETRY_DISABLED` env var, a config key, a first-run prompt) and put it in the
  report.
- **Error reporting**: Sentry, Bugsnag, Rollbar. Stack traces contain file paths (with
  usernames and project names); Sentry with `sendDefaultPii: true` or local-variable
  capture can include message contents. Check `beforeSend` scrubbing.
- **Update checks**: a request at start with the version, OS and often an install ID.
  Usually a note; worse if it carries more, or downloads and runs code (auto-update),
  which can change the tool after the audit.
- **AI and cloud SDKs**: an OpenAI or Anthropic client means prompts go to that provider;
  an S3 or Firebase client means data is stored somewhere: whose account?
- **Credential handling**: does it read tokens beyond the ones it needs, or the whole
  environment? Does it send the environment in error reports or "debug info"?

## Ecosystem notes

- **npm**: published code is often built (`dist/`) and sometimes minified. A source map
  (`*.map`) or the repository at the same tag helps; check that the built code matches.
- **PyPI**: wheels can contain compiled extensions (`.so`) you can't read; say so.
- **Go and Rust**: you usually install a prebuilt binary. Auditing the source tells you
  what the source does; the binary is a separate trust question (reproducible builds,
  signed releases). Say which you audited.
- **Homebrew**: `brew cat <formula>` shows where it downloads from. A bottle is a
  prebuilt binary; note that the same caveat applies. Homebrew's own analytics are
  separate from the tool's (`brew analytics off`).

## Own service

What the tool is for: a GitHub CLI's own service is `github.com`; a downloader's is the
site the user points it at. Package registries are fine for installing but are not a
place your data should go.
