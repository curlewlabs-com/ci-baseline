#!/bin/sh
# Check the formatting of every tracked file prettier knows how to format,
# under the repository's own prettier configuration and .prettierignore. It
# runs on the runner image's node: prettier supports every node an image
# ships, and installing one would change the node later steps of the
# caller's job see.
#
# This is the one prettier every repository is checked with, so a
# repository does not pin its own: two versions disagree about formatting
# whenever their pins differ.
set -eu
bin=$RUNNER_TEMP/ci-baseline/bin
files=$RUNNER_TEMP/ci-baseline/files/all
cd "$(git rev-parse --show-toplevel)"
if [ ! -s "$files" ]; then
	echo "ci-baseline: no files to check"
	exit 0
fi
# --ignore-unknown skips a file prettier has no parser for, so the whole
# tracked tree can be handed over without a list of extensions. The -- keeps a
# tracked file named like an option (--help) from being read as one.
tr '\n' '\0' <"$files" |
	xargs -0 node "$bin/prettier/bin/prettier.cjs" --check --ignore-unknown --
