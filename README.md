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

It needs `python3` 3.12 or newer, `node`, `git` and mikefarah's `yq`, which
GitHub's Ubuntu images ship, and, where Ruby is tracked, `docker`, which they
ship too.

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
