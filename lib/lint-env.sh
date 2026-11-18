# Sourced by lib/install-lint.sh and lib/eslint.sh: what the caller's job can
# set does not change the eslint toolchain or what it checks.
#   - Every npm_config_* variable, in either case, is cleared; npm reads no
#     configuration but the command line install-lint.sh gives it.
#   - NODE_OPTIONS, NODE_PATH and node's symlink-preserving switches are cleared,
#     so no module is preloaded or found outside the install.
#   - Every ESLINT_*, TSESTREE_* and TYPESCRIPT_ESLINT_* variable is cleared, so
#     neither eslint nor typescript-eslint takes a setting from the job
#     (ESLINT_USE_FLAT_CONFIG and ESLINT_FLAGS among them).
#   - A node or npm that resolves inside the checkout (a node_modules/.bin on
#     PATH, say) is refused, since the checkout is what is being checked.
# shellcheck shell=sh
unset NODE_OPTIONS NODE_PATH NODE_PRESERVE_SYMLINKS NODE_PRESERVE_SYMLINKS_MAIN
for name in $(env | grep -oE '^([Nn][Pp][Mm]_[Cc][Oo][Nn][Ff][Ii][Gg]|ESLINT|TSESTREE|TYPESCRIPT_ESLINT)_[A-Za-z0-9_]*=' | tr -d =); do
	unset "$name"
done
lint_checkout=$(git rev-parse --show-toplevel 2>/dev/null || true)
for lint_tool in node npm; do
	lint_found=$(command -v "$lint_tool" || true)
	if [ -z "$lint_found" ]; then
		echo "ci-baseline: no $lint_tool on PATH" >&2
		exit 1
	fi
	lint_dir=$(cd "$(dirname "$lint_found")" && pwd -P)
	if [ -n "$lint_checkout" ]; then
		case $lint_dir/ in
		"$lint_checkout"/*)
			echo "ci-baseline: $lint_tool resolves to $lint_found, inside the checkout being checked" >&2
			exit 1
			;;
		esac
	fi
done
