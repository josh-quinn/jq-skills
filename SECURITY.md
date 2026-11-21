# Security policy

## Supported versions

Only the latest commit on `main` is supported. There are no releases yet.

## Reporting a vulnerability

Please **do not open a public issue**. Report privately to the repository owner
(Josh Quinn) directly, or through GitHub private vulnerability reporting (the repository's
**Security** tab, **Report a vulnerability**) once the repository is hosted there.

Include what you did, what happened, the commit, and your environment. Expect an
acknowledgement within 7 days and an assessment within 14 days.

## Scope

In scope: `privacy.py` and `sandbox.py` (parsing of untrusted packages, file writes, how the
sandbox is launched), the proxy and network-blocking setup in the sandbox, and anything that
could make a skill run, or leak, the data of the target it audits.
Out of scope: findings about the tools being audited, and social engineering.
