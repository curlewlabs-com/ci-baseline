# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
privately via
[GitHub's security advisory feature](https://github.com/curlewlabs-com/ci-baseline/security/advisories/new).

Do not open a public issue for security vulnerabilities.

## Scope

The action downloads three tools and runs them, and three actions, over the
repository it runs in. It never runs what it reads. The security surface is:

- **The downloads.** actionlint, shellcheck and zizmor come from their GitHub
  releases over HTTPS, and each is refused unless its sha256 matches the digest
  pinned in `lib/install-tools.sh`.
- **The token.** The zizmor step is given the job's `github.token`, which its
  online audits use to read GitHub. Nothing writes with it.
- **A false clean.** A finding one of the checks makes that the action passes is
  a defect in what the action promises. Report it as a bug, or privately if you
  think it matters more than that.
