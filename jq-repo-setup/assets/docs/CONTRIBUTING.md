# Contributing

Security problems: report them privately as described in [SECURITY.md](SECURITY.md).

## Ground rules

- **Test first.** Add a failing test, then the code. Every bug fix gets a regression test.
- **Small, single-purpose commits** written as [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat(api): ...`, `fix(auth): ...`). A `commit-msg` hook and CI enforce this.
- **Decisions** that are hard to reverse get an ADR in [`docs/adr/`](docs/adr) in the same PR.
- **Dependencies**: justify new ones in the PR; prefer the standard library and
  well-maintained, widely used packages; lockfiles are committed; Dependabot keeps them current.
<!-- If using DCO: - **Sign off** every commit (`git commit -s`) to certify the Developer Certificate of Origin. -->

## Getting started

```sh
<install toolchain, e.g. brew install go gitleaks shellcheck>
make hooks    # once per clone: commit messages checked, pushes scanned for secrets
make check    # everything CI runs
```

## Pull requests

Open a PR against `main`. It needs every required check to pass and an approving review
from a code owner ([`.github/CODEOWNERS`](.github/CODEOWNERS)). First-time contributors'
CI runs start after a maintainer approves them.

If the pre-push scan blocks you, remove the secret from **history** (amend or rebase) and
rotate the credential. Record genuine false positives by fingerprint in `.gitleaksignore`.
