# ci-baseline

## What it is

One composite GitHub Action that runs the checks every Curlew Labs repository
holds itself to, so each repository's CI enrolls in all of them with one step
and the policy lives in one place:

| Check                                                                      | What fails                                                                                 |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| [ascii-lint](https://github.com/curlewlabs-com/ascii-lint)                 | any non-ASCII character in tracked text                                                    |
| [hosted-runner-lint](https://github.com/curlewlabs-com/hosted-runner-lint) | a workflow job that would run on a self-hosted or larger runner                            |
| [action-run-lint](https://github.com/curlewlabs-com/action-run-lint)       | a composite action `run:` step that is not one call of a script file                       |
| [actionlint](https://github.com/rhysd/actionlint)                          | workflow errors, and shellcheck findings in workflow `run:` blocks                         |
| [zizmor](https://github.com/zizmorcore/zizmor)                             | workflow and action security findings, at any severity                                     |
| [shellcheck](https://github.com/koalaman/shellcheck)                       | any finding in a tracked shell file: `*.sh`, `*.bash`, or a `sh`, `bash` or `dash` shebang |
| [prettier](https://prettier.io)                                            | a tracked file prettier formats differently, under the repository's prettier configuration |

Each check runs whatever the one before it found, so one run reports all of
them, and any failure fails the action.

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

actionlint, shellcheck and zizmor are downloaded from their GitHub releases, and
prettier from the npm registry, at the versions in
[`lib/install-tools.sh`](lib/install-tools.sh), and each download is refused
unless its sha256 matches the digest beside the version. The three lints above
are actions pinned by commit in [`action.yml`](action.yml). A runner image's own
copies of these tools are not used, because they move whenever the image does.

prettier is the one every repository is checked with, so a repository does not
pin its own in `package.json`: two versions disagree about formatting whenever
their pins differ. Its configuration and `.prettierignore` are the
repository's own.

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
