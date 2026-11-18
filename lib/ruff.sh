#!/bin/sh
# Lint and check the formatting of every tracked Python file with ruff, under
# the repository's own ruff configuration. Both run whatever the first found,
# so one run reports the lint findings and the files ruff would reformat.
set -eu
bin=$RUNNER_TEMP/ci-baseline/bin
files=$RUNNER_TEMP/ci-baseline/files/python
cd "$(git rev-parse --show-toplevel)"
if [ ! -s "$files" ]; then
	echo "ci-baseline: no Python files to check"
	exit 0
fi
# ruff reads a file named on its command line even where the repository's
# configuration excludes it; --force-exclude keeps the exclusion. --no-cache
# leaves no .ruff_cache in the caller's checkout for its later steps to find.
# A configuration can set `fix` or `fix-only`, which is right at a desk and
# here would rewrite the checkout and pass what it rewrote; either flag alone
# leaves the other setting in force, so both are switched off.
rc=0
tr '\n' '\0' <"$files" |
	xargs -0 "$bin/ruff" check --no-cache --force-exclude --no-fix --no-fix-only -- || rc=1
tr '\n' '\0' <"$files" |
	xargs -0 "$bin/ruff" format --check --no-cache --force-exclude -- || rc=1
exit "$rc"
