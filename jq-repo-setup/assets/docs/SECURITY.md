# Security policy

## Supported versions

| Version | Supported |
|---|---|
| latest release (<MAJOR.MINOR>.x) | yes |
| older releases | no - please upgrade |

<!-- saas-b2b: state the deployed service is always the latest version. -->

## Reporting a vulnerability

Please **do not open a public issue**. Report privately:

- GitHub: **Security** tab, **Report a vulnerability** (<https://github.com/<OWNER>/<REPO>/security/advisories/new>), or
- email <SECURITY_EMAIL> <!-- private repos / SaaS: use an email or form -->

Include what you did, what happened, the version, and your environment.

We will acknowledge within <7> days and give an assessment within <14> days. Confirmed
issues are fixed as soon as practical (target: critical <7> days, high <30> days), with
credit to you unless you prefer otherwise, and published as a GitHub security advisory
(with a CVE where appropriate).

## Scope

In scope: <what attackers could reach - inputs, files written, network endpoints, auth,
tenant isolation, the release pipeline>.
Out of scope: <deliberate behaviour, social engineering, volumetric DoS>.

## Verifying releases

<How to verify checksums, signatures or attestations - see RELEASING.md.>
