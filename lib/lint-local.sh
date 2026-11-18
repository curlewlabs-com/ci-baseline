#!/bin/sh
# Run the eslint check CI runs, from a contributor's checkout of a repository
# that uses ci-baseline: run it from that checkout as
#
#   <any ci-baseline checkout>/lib/lint-local.sh
#
# It reads the ci-baseline commit the repository's workflows pin, fetches that
# commit by its full name into a cache of its own (git refuses an object whose
# content does not hash to that name), and runs that commit's check, so the
# result is the one CI gives for the same tree. With TypeScript tracked it runs
# both layers with types, which needs the repository's dependencies installed
# first; otherwise the baseline layer. Nothing is written in the checkout.
#
# Needs git, mikefarah's yq, python3 3.12 or newer, and node ^20.19, ^22.13 or
# 24 and newer with npm.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
root=$(git rev-parse --show-toplevel)
cache=${XDG_CACHE_HOME:-$HOME/.cache}/ci-baseline

# ci-baseline's own checkout is linted as it stands, since its workflows call
# the action from the checkout rather than at a commit.
if [ "$root" = "$here" ]; then
	pins=$(git -C "$here" rev-parse HEAD)
else
	# The pins are the steps' own `uses:` values, read by yq, so a comment or a
	# string in a run block naming another commit is not taken for one.
	if ! command -v yq >/dev/null; then
		echo "ci-baseline: reading the workflows' pins needs mikefarah's yq" >&2
		exit 1
	fi
	pins=$(for workflow in "$root"/.github/workflows/*.yml "$root"/.github/workflows/*.yaml; do
		if [ -f "$workflow" ]; then
			yq -r '.jobs[].steps[]?.uses // ""' "$workflow"
		fi
	done | grep -E '^curlewlabs-com/ci-baseline(/typed)?@[0-9a-f]{40}$' | sed 's/.*@//' | sort -u || true)
fi
case $pins in
"")
	echo "ci-baseline: no workflow in $root pins curlewlabs-com/ci-baseline by commit" >&2
	exit 1
	;;
*[!0-9a-f]*)
	echo "ci-baseline: the workflows in $root pin more than one ci-baseline commit: $(printf '%s' "$pins" | tr '\n' ' ')" >&2
	exit 1
	;;
esac

# A repository's check always runs from a clean snapshot of the pinned commit
# in the cache, never from the checkout this was started from, which may hold
# edits; a snapshot that is missing, at another commit, or changed since it was
# fetched is fetched again.
if [ "$root" != "$here" ]; then
	pinned=$cache/commits/$pins
	if [ "$(cd "$here" && pwd -P)" != "$( (cd "$pinned" 2>/dev/null && pwd -P) || true)" ]; then
		if [ "$(git -C "$pinned" rev-parse HEAD 2>/dev/null || true)" != "$pins" ] ||
			[ -n "$(git -C "$pinned" status --porcelain 2>/dev/null || echo unreadable)" ]; then
			mkdir -p "$cache/commits"
			rm -rf "$pinned" "$pinned.partial"
			git -c init.defaultBranch=main init -q "$pinned.partial"
			git -C "$pinned.partial" fetch -q --depth 1 https://github.com/curlewlabs-com/ci-baseline "$pins"
			git -C "$pinned.partial" -c advice.detachedHead=false checkout -q FETCH_HEAD
			mv "$pinned.partial" "$pinned"
		fi
		exec "$pinned/lib/lint-local.sh"
	fi
fi

# An install is named by the lint/ tree it came from, lockfile and
# configuration alike, so a commit that changes either installs afresh. A run
# from ci-baseline's own checkout, whose lint/ may be uncommitted, reinstalls
# every time.
if [ "$root" = "$here" ]; then
	export CI_BASELINE_LINT_DIR="$cache/lint/self"
	"$here/lib/install-lint.sh" "$CI_BASELINE_LINT_DIR"
else
	tree=$(git -C "$here" rev-parse HEAD:lint)
	export CI_BASELINE_LINT_DIR="$cache/lint/$tree"
	if [ ! -e "$CI_BASELINE_LINT_DIR/.ci-baseline-lint-installed" ]; then
		"$here/lib/install-lint.sh" "$CI_BASELINE_LINT_DIR"
	fi
fi
export CI_BASELINE_FILES_DIR="$cache/files"
RUNNER_TEMP=$cache/run
export RUNNER_TEMP
mkdir -p "$RUNNER_TEMP"
(cd "$root" && "$here/lib/tracked-files.sh")
rm -rf "$CI_BASELINE_FILES_DIR"
mv "$RUNNER_TEMP/ci-baseline/files" "$CI_BASELINE_FILES_DIR"
if grep -qE '\.(ts|mts|cts|tsx)$' "$CI_BASELINE_FILES_DIR/js"; then
	LAYER=typed
else
	LAYER=baseline
fi
export LAYER
cd "$root"
exec "$here/lib/eslint.sh"
