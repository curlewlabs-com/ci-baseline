# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
privately via
[GitHub's security advisory feature](https://github.com/curlewlabs-com/ci-baseline/security/advisories/new).

Do not open a public issue for security vulnerabilities.

## Scope

The action downloads tools and runs them, with the lint actions `action.yml`
pins, over the repository it runs in. It reads that repository's files and, with
one exception, never runs them:

- **prettier loads the repository's prettier configuration.** A configuration
  written in JavaScript, and a plugin a configuration names, is code from the
  checkout, and prettier runs it with the job's privileges, as the repository's
  own tests would. Run the action where you would run those tests, and not on a
  checkout you do not trust in a job that holds a secret or a token that can
  write.

The rest of the security surface is:

- **The downloads.** Each tool is fetched over HTTPS at the version pinned in
  `lib/install-tools.sh`: from its GitHub release, or for prettier from the npm
  registry, and refused unless its sha256 matches the digest pinned beside the
  version. shell-trap-lint is fetched as the commit pinned there, which git
  verifies by its name.
- **The token.** The zizmor step, and no other, is given the job's
  `github.token`, which its online audits use to read GitHub. Nothing the action
  does writes with it.
- **A false clean.** A finding one of the checks makes that the action passes is
  a defect in what the action promises. Report it as a bug, or privately if you
  think it matters more than that.
