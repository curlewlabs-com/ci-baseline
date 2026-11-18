# Contributing

Thanks for your interest in improving `ci-baseline`. The bar for a change is
whether every repository that runs it is still held to the same checks, and
whether a check that could not run still fails.

## Running the checks

CI runs the action on this repository's own tree on every push and pull request,
which is what lints and formats it. The type check is the one thing it runs
besides; locally, with Python 3.12 or newer:

```sh
python3 -m pip install -r requirements-dev.txt
mypy
```

To see what the action would report before pushing, run the same tools at the
versions [`lib/install-tools.sh`](lib/install-tools.sh) names:
`ruff check . && ruff format --check .`, `shfmt -d lib`, `prettier --check .`.

## Conventions

- **Tests ship with the change.** A change to what the action finds includes a
  CI case that shows it finding it. A check implemented in its own repository is
  tested there.
- **One policy.** A zizmor exception goes in `zizmor.yml` with the reason, for
  every repository at once; the action never reads a repository's own config.
- **The action's steps call scripts.** Each `run:` in `action.yml` is one call
  of an executable file in `lib/`, so shellcheck reads all of the shell the
  action runs. action-run-lint holds this repository to it.
- **Pin dependencies exactly.** An action reference is its release's commit SHA
  with the version beside it, since a tag can be moved. A downloaded tool is an
  exact version with the sha256 of each asset beside it, or a commit, which git
  verifies by its name. Renovate proposes the updates; after a tool bump,
  `python3 tools/refresh_tools.py` rewrites the digests. A pin written inline needs a `# renovate:` comment above it saying
  what the literal is.
- **Comments explain why, not what.**
- **Keep tracked text ASCII.**

## Submitting

Keep each pull request focused on one change, make sure the checks pass, and
describe the why in the pull request body. CI must be green before merge.

## Releasing

A patch or minor release needs no approval: whoever cuts it follows the steps
below in order, on a `main` commit whose required checks have passed. A major
version, a 1.0, or a minor before 1.0 that changes an interface consumers use
needs the maintainer's explicit approval before its tag is pushed.

Every release gets a fixed `vMAJOR.MINOR.PATCH` tag. The repository blocks
updates and deletions of those tags, and publishing the GitHub Release makes the
tag immutable. Consumers pin a release by its commit, so there is no floating
tag to move.

1. Tag a `main` commit whose required checks passed `vMAJOR.MINOR.PATCH` and
   push the tag.
2. Publish it: `gh release create vMAJOR.MINOR.PATCH --verify-tag`.

## License

By submitting a contribution for inclusion in this project, you agree that it
is licensed under the MIT and Apache-2.0 licenses, as the README's License
section describes, without any additional terms or conditions.
