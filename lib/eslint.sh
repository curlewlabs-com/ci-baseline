#!/bin/sh
# Run eslint over every tracked JavaScript and TypeScript file with the one
# configuration in lint/, from the toolchain lib/install-lint.sh installed.
# LAYER is `baseline`, the rules that need no type information, or `typed`,
# both layers with types read through the repository's own installed
# dependencies. eslint reads no configuration of the repository's: a rule, a
# severity or a plugin there changes nothing, and .ci-baseline/eslint.json
# states only ignored paths, with reasons, and tsconfig projects.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
lint=${CI_BASELINE_LINT_DIR:-$RUNNER_TEMP/ci-baseline/lint}
files=${CI_BASELINE_FILES_DIR:-$RUNNER_TEMP/ci-baseline/files}
layer=${LAYER:?LAYER is baseline or typed}
# shellcheck source=lib/lint-env.sh
. "$here/lib/lint-env.sh"
cd "$(git rev-parse --show-toplevel)"
if [ ! -s "$files/js" ]; then
	# The statement is still read, so an ignore entry left behind when the last
	# file it matched went fails here, rather than surviving to excuse whatever
	# file is added next. Nothing was installed, so the plan goes nowhere.
	python3 -I "$here/lib/eslint_plan.py" "$layer" "$files" /dev/null /dev/null
	echo "ci-baseline: no JavaScript or TypeScript to lint"
	exit 0
fi
python3 -I "$here/lib/eslint_plan.py" "$layer" "$files" "$lint/plan.json" "$lint/files"
if [ ! -s "$lint/files" ]; then
	echo "ci-baseline: every JavaScript and TypeScript file is ignored by .ci-baseline/eslint.json"
	exit 0
fi
# --max-warnings 0 makes a file eslint would skip with a warning (one under its
# default ignores, or one no configuration matches) fail the run instead.
# --suppressions-location names the install's empty suppressions file, so a
# bulk-suppressions file in the checkout (eslint reads eslint-suppressions.json
# from the working directory by default) suppresses nothing. The -- keeps a
# tracked file named like an option from being read as one. The report is kept
# in eslint.out beside the install as well as printed, so a later step can read
# which rule a run reported.
if CI_BASELINE_ESLINT_PLAN=$lint/plan.json xargs -0 \
	node "$lint/node_modules/eslint/bin/eslint.js" \
	--config "$lint/eslint.config.mjs" --suppressions-location "$lint/no-suppressions.json" \
	--max-warnings 0 -- <"$lint/files" >"$lint/eslint.out" 2>&1; then
	status=0
else
	status=$?
fi
cat "$lint/eslint.out"
exit "$status"
