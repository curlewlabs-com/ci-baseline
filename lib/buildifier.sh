#!/bin/sh
# Check every tracked Starlark file with buildifier: its formatting, and its
# default lint warnings. A repository's own .buildifier.json is not read, so
# every repository is held to the same warnings; one that does not apply to a
# line is switched off there, with a `# buildifier: disable=<warning>` comment
# that says so beside the code.
set -eu
bin=$RUNNER_TEMP/ci-baseline/bin
files=$RUNNER_TEMP/ci-baseline/files/starlark
cd "$(git rev-parse --show-toplevel)"
if [ ! -s "$files" ]; then
	echo "ci-baseline: no Starlark files to check"
	exit 0
fi
tr '\n' '\0' <"$files" |
	xargs -0 "$bin/buildifier" --config=off --mode=check --lint=warn --
