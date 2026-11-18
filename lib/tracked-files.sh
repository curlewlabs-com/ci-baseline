#!/bin/sh
# List the tracked files each check reads, once, into
# $RUNNER_TEMP/ci-baseline/files: `all`, and `shell`, `python` and `starlark`
# by language. A file is a language's by its name, or, under any other name,
# by its shebang, so a script under bin/ with no extension is not missed. A
# symlink, and a tracked file deleted from the checkout, has nothing of its
# own to read and is left out. A tracked path git has to quote (a newline, a
# quote or a backslash in its name) cannot be read back here and fails the run
# rather than being skipped.
set -eu
out=$RUNNER_TEMP/ci-baseline/files
rm -rf "$out"
mkdir -p "$out"
cd "$(git rev-parse --show-toplevel)"
git -c core.quotePath=false ls-files >"$out/listed"
: >"$out/all"
: >"$out/shell"
: >"$out/python"
: >"$out/starlark"
while IFS= read -r f; do
	case $f in
	\"*)
		echo "ci-baseline: cannot read the tracked path $f" >&2
		exit 1
		;;
	esac
	if [ -L "$f" ] || [ ! -f "$f" ]; then
		continue
	fi
	printf '%s\n' "$f" >>"$out/all"
	case ${f##*/} in
	*.sh | *.bash)
		printf '%s\n' "$f" >>"$out/shell"
		;;
	*.py | *.pyi)
		printf '%s\n' "$f" >>"$out/python"
		;;
	*.bzl | *.bazel | *.bzlmod | BUILD | WORKSPACE)
		printf '%s\n' "$f" >>"$out/starlark"
		;;
	*)
		if head -n 1 "$f" | grep -Eq '^#! *(/usr)?/bin/(env +)?(ba|da)?sh([[:space:]]|$)'; then
			printf '%s\n' "$f" >>"$out/shell"
		elif head -n 1 "$f" | grep -Eq '^#! *(/usr)?(/local)?/bin/(env +)?python[0-9.]*([[:space:]]|$)'; then
			printf '%s\n' "$f" >>"$out/python"
		fi
		;;
	esac
done <"$out/listed"
