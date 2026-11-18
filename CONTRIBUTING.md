# Contributing

Thanks for your interest in improving `ci-baseline`. The bar for a change is
whether every repository that runs it is still held to the same checks, and
whether a check that could not run still fails.

## Running the checks

CI runs the action on this repository's own tree on every push and pull request,
which is what lints, formats and type-checks it with pyright. Besides that it
runs mypy, the unit tests of `tools/` and the pyright step's unit tests;
locally, with Python 3.12 or newer:

```sh
python3 -m pip install -r requirements-dev.txt
mypy
python3 -m unittest discover -s tools
python3 -m unittest discover -s tests -t .
```

To see what the action would report before pushing, run the same tools at the
versions [`lib/install-tools.sh`](lib/install-tools.sh) names:
`ruff check . && ruff format --check .`, `shfmt -d lib`, `prettier --check .`,
and, with the gems in [`lib/rubocop/Gemfile.lock`](lib/rubocop/Gemfile.lock),
`BUNDLE_GEMFILE=lib/rubocop/Gemfile bundle exec rubocop --config lib/rubocop/config.yml`
on the Ruby files.

For eslint, `lib/lint-local.sh` lints `lint/` here as it stands. The eslint
check's own cases run against an install of this tree:
`lib/install-lint.sh <dir>`, and `npm ci --ignore-scripts` of a copy of
`tests/node-types` (the real `@types/node` the typed cases read node:test from)
into `<types dir>`, then `python3 -I tests/eslint_cases.py <dir> <types dir>`. A
new exemption in the configuration comes with a pair of cases there: what it
allows, and the nearest thing it must still report.
`python3 -I tests/config_tarball.py` packs the configuration as a release does
and checks that the tarball holds the licences.

A change to the eslint configuration, or a toolchain bump that changes what it
resolves to, rewrites [`lint/rules.txt`](lint/rules.txt) in the same change:
`node <install dir>/print-rules.mjs > lint/rules.txt` from an install of the
changed tree. A rule turned off names, beside it, what it reported that made it
not worth having.

`lint/package.json`'s `overrides` holds `minimatch` at 11.0.9, a release past
[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249),
because the pinned `eslint` and `typescript-eslint` still ask for the 10.x line.
Remove the override in the change that moves that pair to releases that ask
for 11.0.1 or later themselves, so it cannot hold `minimatch` below what they
need.

## Conventions

- **Tests ship with the change.** A change to what the action finds includes a
  CI case that shows it finding it. A check implemented in its own repository is
  tested there.
- **One policy.** What is checked, and at which version, is the same in every
  repository. A zizmor exception goes in `zizmor.yml` with the reason, for every
  repository at once, and zizmor, buildifier, RuboCop and pyright never read a
  repository's own configuration. A RuboCop rule changes in
  `lib/rubocop/config.yml`, and a pyright back-off in
  `src/ci_baseline_pyright/policy.py`, with its reason beside it. A formatter, ruff, shellcheck or actionlint reads the
  repository's, since how its files are laid out and which lint rules it adopts
  are its own to say; the README lists what each check reads.
- **The action's steps call scripts.** Each `run:` in `action.yml` is one call
  of an executable file in `lib/`, so shellcheck reads all of the shell the
  action runs. action-run-lint holds this repository to it.
- **Pin dependencies exactly.** An action reference is its release's commit SHA
  with the version beside it, since a tag can be moved. A downloaded tool is an
  exact version with the sha256 of each asset beside it, or a commit, which git
  verifies by its name. The Ruby image is its tag and digest, which an update
  moves together. RuboCop and the gems it needs are pinned by
  `lib/rubocop/Gemfile.lock`, whose `CHECKSUMS` Bundler checks. Renovate
  proposes the updates; after a tool bump, `python3 tools/refresh_tools.py`
  rewrites the digests, and after a RuboCop bump it moves the lock's RuboCop
  entries, or refuses (see Relocking RuboCop). A pin written inline
  needs a `# renovate:` comment above it saying what the literal is.
- **Comments explain why, not what.**
- **Keep tracked text ASCII.**

## Relocking RuboCop

`tools/refresh_tools.py` moves `lib/rubocop/Gemfile.lock` to the RuboCop that
`lib/rubocop/Gemfile` pins without running Ruby, and only when every other
locked gem still satisfies the new release. When it refuses - a release that
raises a dependency's floor past the locked version, adds a dependency, or
anything else `tools/rubocop_lock.py` does not model - relock with Bundler in
the pinned image, from the repository's root, on a machine with Docker:

```sh
docker run --rm --mount "type=bind,source=$PWD/lib/rubocop,target=/ci" \
  --workdir /ci --env BUNDLE_VERSION=system \
  "public.ecr.aws/docker/library/ruby:$(sed -n 's/^RUBY_VERSION=//p' lib/install-tools.sh)" \
  bundle lock --update rubocop
```

`--update rubocop` also moves the gems RuboCop depends on, as far as their
newest releases; read the lock's diff before committing it. The image's own
Bundler keeps the lock's `BUNDLED WITH`, and CI's frozen install refuses any
gem whose checksum is not the lock's.

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

1. On `main`, `lint/config/package.json`'s `version` and `pyproject.toml`'s
   `version` are the release's, without the `v`, so the eslint configuration
   and the pyright policy package another project installs from the tag each
   name the release they are; a pull request moves them before the tag when
   they are not.
2. Tag a `main` commit whose required checks passed `vMAJOR.MINOR.PATCH` and
   push the tag.
3. Pack the configuration for a repository that runs eslint from its own
   install: `python3 tools/pack_config.py .`, which writes
   `curlewlabs-com-eslint-config-MAJOR.MINOR.PATCH.tgz` with the licence files
   in it. `npm pack ./lint/config` alone would leave them out, since they live
   only at the root.
4. Publish the release with that tarball attached:
   `gh release create vMAJOR.MINOR.PATCH --verify-tag curlewlabs-com-eslint-config-MAJOR.MINOR.PATCH.tgz`.

## License

By submitting a contribution for inclusion in this project, you agree that it
is licensed under the MIT and Apache-2.0 licenses, as the README's License
section describes, without any additional terms or conditions.
