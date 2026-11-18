#!/bin/sh
# Type-check every tracked .py and .pyi file with pyright, strict, under the
# policy in src/ci_baseline_pyright/policy.py and nothing a repository
# carries. The step itself is that package's __main__, which says what reaches
# pyright.
#
# python3 -I keeps the checkout's directory, every PYTHON* variable and the
# user's site-packages off the import path, so a file in the checkout named
# like a standard module, or one a caller's PYTHONPATH names, cannot stand in
# for the one the step imports; the package goes first on the path by name.
set -eu
src=$(CDPATH='' cd -- "$(dirname -- "$0")/../src" && pwd)
root=$(git rev-parse --show-toplevel)
files=$RUNNER_TEMP/ci-baseline/files
if ! grep -Eq '\.pyi?$' "$files/python"; then
	echo "ci-baseline: no Python files to check"
	exit 0
fi
# The launcher is written for any python3, so that one older than the package
# needs is told so instead of failing on a syntax error.
exec python3 -I -c '
import sys
if sys.version_info < (3, 12):
    sys.exit("ci-baseline: pyright is run by python3 3.12 or newer, not " + sys.version.split()[0])
sys.path.insert(0, sys.argv[1])
from ci_baseline_pyright.__main__ import main
sys.exit(main(sys.argv[2:]))
' "$src" \
	--root "$root" \
	--files "$files" \
	--pyright "$RUNNER_TEMP/ci-baseline/bin/pyright/index.js" \
	--work "$RUNNER_TEMP/ci-baseline/pyright" \
	--search-paths="${CI_BASELINE_SEARCH_PATHS:-}"
