#!/bin/sh
# Run shellcheck on every tracked shell file: one named *.sh or *.bash, or one
# whose first line is a sh, bash or dash shebang, so a script under bin/ with
# no extension is not missed. A tracked path git has to quote (a newline, a
# quote or a backslash in its name) cannot be read back here and fails the
# run rather than being skipped.
set -eu
bin=$RUNNER_TEMP/ci-baseline/bin
all=$RUNNER_TEMP/ci-baseline/tracked
shell_files=$RUNNER_TEMP/ci-baseline/shell-files
cd "$(git rev-parse --show-toplevel)"
git -c core.quotePath=false ls-files >"$all"
: >"$shell_files"
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
	case $f in
	*.sh | *.bash)
		printf '%s\n' "$f" >>"$shell_files"
		;;
	*)
		if head -n 1 "$f" | grep -Eq '^#! *(/usr)?/bin/(env +)?(ba|da)?sh([[:space:]]|$)'; then
			printf '%s\n' "$f" >>"$shell_files"
		fi
		;;
	esac
done <"$all"
if [ ! -s "$shell_files" ]; then
	echo "ci-baseline: no shell files to check"
	exit 0
fi
echo "ci-baseline: shellcheck $(wc -l <"$shell_files" | tr -d ' ') files"
# -x follows a `source` into the file it names, resolved from the sourcing
# script's own directory, so a variable a sourced file sets is not reported
# unset and a sourced file's own mistakes are read in context.
tr '\n' '\0' <"$shell_files" | xargs -0 "$bin/shellcheck" -x --source-path=SCRIPTDIR
