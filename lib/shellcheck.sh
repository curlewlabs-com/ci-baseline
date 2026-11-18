#!/bin/sh
# Run shellcheck on every tracked shell file: the ones lib/tracked-files.sh
# listed.
set -eu
bin=$RUNNER_TEMP/ci-baseline/bin
files=$RUNNER_TEMP/ci-baseline/files/shell
cd "$(git rev-parse --show-toplevel)"
if [ ! -s "$files" ]; then
	echo "ci-baseline: no shell files to check"
	exit 0
fi
echo "ci-baseline: shellcheck $(wc -l <"$files" | tr -d ' ') files"
# -x follows a `source` into the file it names, resolved from the sourcing
# script's own directory, so a variable a sourced file sets is not reported
# unset and a sourced file's own mistakes are read in context.
tr '\n' '\0' <"$files" | xargs -0 "$bin/shellcheck" -x --source-path=SCRIPTDIR
