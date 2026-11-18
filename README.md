# ci-baseline

## What it is

One composite GitHub Action that runs the checks every Curlew Labs repository
holds itself to, so each repository's CI enrolls in all of them with one step
and the policy lives in one place:

| Check                                                                      | What fails                                                                                                                      |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| [ascii-lint](https://github.com/curlewlabs-com/ascii-lint)                 | any non-ASCII character in tracked text                                                                                         |
| [hosted-runner-lint](https://github.com/curlewlabs-com/hosted-runner-lint) | a workflow job that would run on a self-hosted or larger runner                                                                 |
| [action-run-lint](https://github.com/curlewlabs-com/action-run-lint)       | a composite action `run:` step that is not one call of a script file                                                            |
| [actionlint](https://github.com/rhysd/actionlint)                          | workflow errors, and shellcheck findings in workflow `run:` blocks                                                              |
| [zizmor](https://github.com/zizmorcore/zizmor)                             | workflow and action security findings, at any severity                                                                          |
| [shellcheck](https://github.com/koalaman/shellcheck)                       | any finding in a tracked shell file                                                                                             |
| [shfmt](https://github.com/mvdan/sh)                                       | a tracked shell file shfmt formats differently                                                                                  |
| [shell-trap-lint](https://github.com/curlewlabs-com/shell-trap-lint)       | an EXIT trap in a tracked shell file that lets a run that stopped short exit 0                                                  |
| [ruff](https://docs.astral.sh/ruff/)                                       | a lint finding in a tracked Python file, or one ruff formats differently                                                        |
| [RuboCop](https://rubocop.org)                                             | any finding in a tracked Ruby file, under the one configuration in [`lib/rubocop/config.yml`](lib/rubocop/config.yml)           |
| [buildifier](https://github.com/bazel-contrib/buildtools)                  | a tracked Starlark file buildifier formats differently, or a lint warning in one                                                |
| [prettier](https://prettier.io)                                            | a tracked file of a kind prettier formats (Markdown, YAML, JSON, JavaScript, TypeScript, CSS, HTML) that it formats differently |
| [eslint](https://eslint.org)                                               | a finding in a tracked JavaScript or TypeScript file, of the rules that need no type information                                |

Each check runs whatever the one before it found, so one run reports all of
them, and any failure fails the action. A check with no file of its language to
read says so and passes.

A file is a language's by its name or, under any other name, by its shebang, so
a script with no extension is still read:

- **shell**: `*.sh`, `*.bash`, or a `sh`, `bash` or `dash` shebang
- **Python**: `*.py`, `*.pyi`, or a `python` shebang
- **Starlark**: `*.bzl`, `*.bazel`, `*.bzlmod`, `*.BUILD`, `BUILD`, `WORKSPACE`
- **Ruby**: the names RuboCop counts as Ruby (`*.rb`, `*.gemspec`, `*.podspec`,
  `Gemfile`, `Podfile`, `Rakefile`, `Fastfile`, `Brewfile` and the rest, as
  [`lib/tracked-files.sh`](lib/tracked-files.sh) lists them), fastlane's
  `Appfile`, `Matchfile` and `Pluginfile`, a `Brewfile.<name>`, or a `ruby`,
  `jruby` or `rake` shebang; not `*.spec` or `*.schema`, which are as often
  something else, and not a `Brewfile*.json`, which is `brew bundle`'s lock
- **JavaScript and TypeScript**: `*.js`, `*.mjs`, `*.cjs`, `*.jsx`, `*.ts`,
  `*.mts`, `*.cts`, `*.tsx`, or a `node`, `bun` or `deno` shebang

Only what a check can run with none of a repository's own dependencies installed
is here. A type check, and tests, need them, and stay in the repository's own
CI.

## Why it exists

A rule a repository's contributing guide states, and no check enforces, is held
only by whoever remembers it. These repositories are small and separate, so a
check added to one of them by hand reaches none of the others, and a check
copied into each drifts. One action, pinned by commit in every repository and
moved by its dependency updater, keeps them all on the same checks at the same
versions.

## How to use it

A job in the repository's CI, on a GitHub-hosted Linux runner (x86_64 or arm64),
after a checkout. Pin it by commit:

```yaml
baseline:
  runs-on: ubuntu-24.04
  steps:
    - uses: actions/checkout@<sha> # vX.Y.Z
      with:
        persist-credentials: false
    - uses: curlewlabs-com/ci-baseline@<sha> # vX.Y.Z
```

It needs `python3` 3.12 or newer, `node` ^20.19, ^22.13 or 24 and newer with
`npm`, `git` and mikefarah's `yq`, which GitHub's Ubuntu images ship, and,
where Ruby is tracked, `docker`, which they ship too.

### Running eslint locally

From the repository's checkout:

```sh
<a ci-baseline checkout>/lib/lint-local.sh
```

It reads the ci-baseline commit the repository's workflows pin, fetches that
commit by its full name into `${XDG_CACHE_HOME:-~/.cache}/ci-baseline`, and runs
that commit's check, so the result is the one CI gives. It writes nothing in the
checkout. Any ci-baseline checkout starts it:
`git clone https://github.com/curlewlabs-com/ci-baseline ~/src/ci-baseline`
once, and `~/src/ci-baseline/lib/lint-local.sh` from then on.

## What it pins

actionlint, shellcheck, zizmor, ruff, shfmt and buildifier are downloaded from
their GitHub releases, and prettier from the npm registry, at the versions in
[`lib/install-tools.sh`](lib/install-tools.sh), and each download is refused
unless its sha256 matches the digest beside the version. shell-trap-lint is
fetched as the commit named there, which git verifies by its name, and runs on
the shfmt above. The three lints at the top of the table are actions pinned by
commit in [`action.yml`](action.yml). A runner image's own copies of these tools
are not used, because they move whenever the image does.

RuboCop runs in a container, and only where a repository tracks Ruby: the
official Ruby image, pulled from Amazon ECR Public's copy of Docker's official
images by the digest in `lib/install-tools.sh`, which Docker refuses a pull not
to match. RuboCop and every gem it needs are installed inside it from
[`lib/rubocop/Gemfile.lock`](lib/rubocop/Gemfile.lock) with the lock frozen, so
Bundler refuses a gem whose sha256 is not the one the lock's `CHECKSUMS` record,
and the image's compiler builds the ones with a C extension. What crosses into the container is
the image, the repository and [`lib/rubocop/`](lib/rubocop) mounted read-only,
the list of files to check, and the three Bundler settings
[`lib/rubocop.sh`](lib/rubocop.sh) names, so nothing else of the runner's or of
the caller's job (its Ruby, its gems, its environment, a `RUBOCOP_OPTS`)
reaches RuboCop.

The eslint toolchain - eslint, its plugins, and the TypeScript its parser reads
with - is installed by `npm ci --ignore-scripts` from
[`lint/package-lock.json`](lint/package-lock.json), which npm checks package by
package against the sha512 recorded there; a lockfile entry that names any
source but the npm registry, or records no digest, is refused before anything
is fetched. It installs into a directory of its own, never the caller's
checkout. That TypeScript is the release the parser supports, and can differ
from the one a repository type-checks with.

What a job sets does not change the toolchain or what it checks: npm reads no
configuration but its command line, the `npm_config_*`, `ESLINT_*`,
`TSESTREE_*` and `TYPESCRIPT_ESLINT_*` variables and `NODE_OPTIONS` and
`NODE_PATH` are cleared before it runs, and a `node` or `npm` found inside the
checkout is refused ([`lib/lint-env.sh`](lib/lint-env.sh)).

Each tool is the one every repository is checked with, so a repository does not
pin its own to run the same check, in `package.json`, a requirements file or a
pre-commit configuration: two versions disagree about the same file whenever
their pins differ.

## What a repository configures

Formatting and lint rules are the repository's, read from where each tool looks
for them; what is checked, and with which version, is not.

| Check           | Reads                                                                                                | To leave a file out                           |
| --------------- | ---------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| actionlint      | `.github/actionlint.yaml`                                                                            | -                                             |
| zizmor          | nothing: [`zizmor.yml`](zizmor.yml) here is every repository's policy                                | -                                             |
| shellcheck      | `.shellcheckrc`, and a `# shellcheck` directive in a file                                            | -                                             |
| shfmt           | `.editorconfig`; without one, shfmt's defaults                                                       | `ignore = true` in an `.editorconfig` section |
| shell-trap-lint | nothing                                                                                              | -                                             |
| ruff            | `pyproject.toml`, `ruff.toml` or `.ruff.toml`                                                        | `exclude` or `extend-exclude` there           |
| RuboCop         | nothing: [`lib/rubocop/config.yml`](lib/rubocop/config.yml) here is every repository's configuration | -                                             |
| buildifier      | nothing: every repository gets its default warnings                                                  | -                                             |
| prettier        | its configuration file, and `.editorconfig`                                                          | `.prettierignore`                             |
| eslint          | `.ci-baseline/eslint.json`: ignored paths only                                                       | `ignore` there, with a reason                 |

buildifier switches one warning off for one line at a
`# buildifier: disable=<warning>` comment there, which says so beside the code.

RuboCop runs under [`lib/rubocop/config.yml`](lib/rubocop/config.yml), whose
every departure from RuboCop's defaults carries its reason there, and under
nothing a repository carries. Almost all a Ruby linter enforces is a choice of
style, and a choice each repository makes for itself is the copy that drifts.
A tracked `.rubocop.yml`, which RuboCop would not read here, or a `.rubocop`
options file, which would change what it checks, fails the run, so neither can
leave a contributor believing it applies; a `.rubocop` at the root fails it
tracked or not, since RuboCop reads it from its working directory. Every Ruby
file the list above finds is checked, whatever its name. A line that must
differ says so where it is, with `# rubocop:disable <Department/Cop>` and the
reason beside it, and RuboCop reports a directive that no longer disables
anything.

shell-trap-lint judges every shell file by its script form. Which files are
tests is a caller's to say, so its test form's further check, that a failed
teardown cannot fail a test, is for a repository that names its tests to run
itself; the script form accepts a test's completion check.

eslint runs with the one configuration in
[`lint/config/rules.mjs`](lint/config/rules.mjs), which names each rule beyond
its presets and why. JavaScript is parsed as JavaScript and TypeScript as
TypeScript. CommonJS's globals (`require`, `module`, `__dirname`) are defined in
a `.cjs`, and in a `.js` or a script found by its shebang, which is CommonJS or a
module by its `package.json`, and not in an `.mjs`. It reads no `eslint.config.*` and no
`eslint-suppressions.json` of the repository's, and a configuration written in a
comment fails the run: the only comments it accepts are line disables
(`// eslint-disable-next-line <rule> -- <why>`) and
`/* global <name> -- <why> */`, each with its reason, and a disable that
suppresses nothing fails it too. A repository states only what eslint cannot
know about it, in `.ci-baseline/eslint.json`:

```json
{
  "ignore": [
    { "path": "src/generated/**", "reason": "written by the generator" }
  ]
}
```

`ignore` takes tracked files out, each pattern (a git glob) with its reason; the
run names every file it skips, and a pattern that matches no tracked file fails
it. Any other key fails the run. [`lint/rules.txt`](lint/rules.txt) is every
rule the configuration turns on, for each kind of file, and CI fails when it
differs from what the configuration resolves to, so a change to what is checked
is a reviewed diff.

### What the eslint configuration assumes

It is written for the JavaScript and TypeScript the repositories that run it
have: `.ts` and `.d.ts` files, `.mjs`, a few `.cjs` and ES-module `.js` files,
scripts with a `node` shebang and an extension, and tests named by the globs in
`lint/config/rules.mjs`. Each of those has a case in
[`tests/eslint_cases.py`](tests/eslint_cases.py). For the shapes none of them
has yet:

- **`.jsx` and `.tsx`** parse with JSX; no React or JSX rule is on.
- **`.mts` and `.cts`** are TypeScript like `.ts`; which module system each is
  makes no difference, since the TypeScript compiler, not eslint, checks names
  there.
- **A `.js` file, and a script found by its shebang alone,** are parsed as
  modules whatever `package.json`'s `type` says, so a CommonJS one that
  `return`s at the top level fails to parse; CommonJS's globals are defined in
  them, since eslint is not told which they are.
- **A runtime's own globals** (`Bun`, `Deno`, a page's `document`) are not
  defined: a file that uses one says so with
  `/* global <name> -- <why> */`.
- **A test named any other way** (`*.spec.*`, `__tests__/`) is linted as
  source.
- **JSON, JSONC and Markdown** are not linted by eslint; prettier formats them.

zizmor runs with [`zizmor.yml`](zizmor.yml) and nothing the repository carries:
not its own configuration, and not an inline ignore comment. Each exception in
`zizmor.yml` carries its reason, and holds for every repository at once. Every
workflow and action is audited whether `.gitignore` names it or not, and one
zizmor cannot parse fails the run.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))
- MIT license ([LICENSE-MIT](LICENSE-MIT))

at your option. Releases published under the MIT license alone may also be used
under either license.

### Contribution

By submitting a contribution for inclusion in this project, you agree that it
is dual licensed as above, without any additional terms or conditions.
