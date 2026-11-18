#!/bin/sh
# Install the eslint toolchain lint/package-lock.json pins, with the
# configuration in lint/ beside it, into a directory of its own outside the
# caller's checkout: $RUNNER_TEMP/ci-baseline/lint in the action, where a
# repository with no JavaScript or TypeScript installs nothing, or the
# directory given as $1. Every package comes from the npm registry and is
# checked against the sha512 the lockfile records; a lockfile entry that names
# another source, or records no digest, is refused before anything is fetched,
# and no package's install script runs. lib/lint-env.sh is what the caller's
# job can set that changes none of this.
#
# It runs on the node already on PATH, as the prettier check does, and refuses
# one older than eslint supports rather than failing inside it.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
if [ $# -eq 0 ]; then
	# lib/tracked-files.sh has listed the files by now.
	if [ ! -s "$RUNNER_TEMP/ci-baseline/files/js" ]; then
		echo "ci-baseline: no JavaScript or TypeScript, so no eslint to install"
		exit 0
	fi
	dest=$RUNNER_TEMP/ci-baseline/lint
else
	dest=$1
fi
# shellcheck source=lib/lint-env.sh
. "$here/lib/lint-env.sh"

if ! node -e '
const [major, minor] = process.versions.node.split(".").map(Number);
const ok = (major === 20 && minor >= 19) || (major === 22 && minor >= 13) || major >= 24;
process.exit(ok ? 0 : 1);
'; then
	echo "ci-baseline: eslint needs node ^20.19, ^22.13 or 24 and newer, not $(node --version)" >&2
	exit 1
fi

python3 -I "$here/lib/check_lint_lock.py" "$here/lint/package-lock.json"

# The install directory is ci-baseline's own: emptied and rebuilt from the
# lockfile, so nothing a previous run or another version left there is used.
# A directory that exists without the marker this script writes into every one
# it creates is someone else's, and is refused rather than emptied. A second
# marker says the install finished.
marker=.ci-baseline-lint
if [ -e "$dest" ] && [ ! -e "$dest/$marker" ]; then
	echo "ci-baseline: $dest exists and is not an eslint install of ours" >&2
	exit 1
fi
rm -rf "$dest"
mkdir -p "$dest"
: >"$dest/$marker"
cp "$here/lint/package.json" "$here/lint/package-lock.json" "$here/lint/eslint.config.mjs" \
	"$here/lint/print-rules.mjs" "$dest/"
cp -R "$here/lint/config" "$dest/config"
printf '{}\n' >"$dest/no-suppressions.json"
: >"$dest/.npmrc-user"
: >"$dest/.npmrc-global"
(cd "$dest" && npm ci --userconfig="$dest/.npmrc-user" --globalconfig="$dest/.npmrc-global" \
	--ignore-scripts --registry=https://registry.npmjs.org/ --replace-registry-host=never \
	--audit=false --fund=false --loglevel=error)
: >"$dest/$marker-installed"
echo "eslint $(node "$dest/node_modules/eslint/bin/eslint.js" --version)"
