#!/bin/sh
# Run shell-trap-lint on every tracked shell file, in its script form: an
# EXIT trap must not let a run that stopped short exit 0. Which files are
# tests is a caller's to say and nothing here can, so the test form's extra
# check, that a failed teardown cannot fail a test, is left to a repository
# that names its tests; the script form accepts a test's completion check.
set -eu
tools=$RUNNER_TEMP/ci-baseline
files=$tools/files/shell
cd "$(git rev-parse --show-toplevel)"
if [ ! -s "$files" ]; then
	echo "ci-baseline: no shell files to check"
	exit 0
fi
# The lint parses shell with the shfmt on PATH, so it is given the pinned one
# the formatting check runs: one shfmt, whatever the runner image ships. -P
# keeps the checkout off python's module path, where `-m` would otherwise put
# it first: a file there named for the lint, or for a standard module the lint
# imports, would run in its place.
tr '\n' '\0' <"$files" |
	PATH="$tools/bin:$PATH" PYTHONPATH="$tools/shell-trap-lint/src" \
		xargs -0 python3 -P -m shell_trap_lint --
