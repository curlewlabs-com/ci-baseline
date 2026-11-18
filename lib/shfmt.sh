#!/bin/sh
# Check the formatting of every tracked shell file with shfmt, printing the
# difference for each one it would rewrite. No formatting flag is passed, so
# a repository's .editorconfig decides the style where it has one and shfmt's
# default applies where it does not; a flag here would switch .editorconfig
# off.
set -eu
bin=$RUNNER_TEMP/ci-baseline/bin
files=$RUNNER_TEMP/ci-baseline/files/shell
cd "$(git rev-parse --show-toplevel)"
if [ ! -s "$files" ]; then
	echo "ci-baseline: no shell files to check"
	exit 0
fi
# shfmt applies an .editorconfig `ignore = true` only to files it finds by
# walking a directory; --apply-ignore extends it to the files named here, so
# a repository can leave out a file it must keep byte for byte.
tr '\n' '\0' <"$files" | xargs -0 "$bin/shfmt" --apply-ignore -d --
