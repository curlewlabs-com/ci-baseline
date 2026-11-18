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
GitHub's Ubuntu images ship.

## What it pins

actionlint, shellcheck, zizmor, ruff, shfmt and buildifier are downloaded from
their GitHub releases, and prettier from the npm registry, at the versions in
[`lib/install-tools.sh`](lib/install-tools.sh), and each download is refused
unless its sha256 matches the digest beside the version. shell-trap-lint is
fetched as the commit named there, which git verifies by its name, and runs on
the shfmt above. The three lints at the top of the table are actions pinned by
commit in [`action.yml`](action.yml). A runner image's own copies of these tools
are not used, because they move whenever the image does.

Each tool is the one every repository is checked with, so a repository does not
pin its own to run the same check, in `package.json`, a requirements file or a
pre-commit configuration: two versions disagree about the same file whenever
their pins differ.

## What a repository configures

Formatting and lint rules are the repository's, read from where each tool looks
for them; what is checked, and with which version, is not.

| Check           | Reads                                               | To leave a file out                                     |
| --------------- | --------------------------------------------------- | ------------------------------------------------------- |
| ruff            | `pyproject.toml`, `ruff.toml` or `.ruff.toml`       | `exclude` or `extend-exclude` there                     |
| shfmt           | `.editorconfig`; without one, shfmt's defaults      | `ignore = true` in an `.editorconfig` section           |
| prettier        | its configuration file, and `.editorconfig`         | `.prettierignore`                                       |
| buildifier      | nothing: every repository gets its default warnings | a `# buildifier: disable=<warning>` comment on the line |
| shell-trap-lint | nothing                                             | -                                                       |

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
