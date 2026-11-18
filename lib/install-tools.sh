#!/bin/sh
# Install the pinned tools the checks run into $RUNNER_TEMP/ci-baseline, and
# verify each download's digest. A runner image's own copies move whenever the
# image does; these move only by a bump a pull request makes.
set -eu

# renovate: datasource=github-releases depName=rhysd/actionlint
ACTIONLINT_VERSION=v1.7.12
# renovate: datasource=github-releases depName=koalaman/shellcheck
SHELLCHECK_VERSION=v0.11.0
# renovate: datasource=github-releases depName=zizmorcore/zizmor
ZIZMOR_VERSION=v1.31.1
# renovate: datasource=github-releases depName=astral-sh/ruff
RUFF_VERSION=0.17.3
# renovate: datasource=github-releases depName=mvdan/sh
SHFMT_VERSION=v3.14.1
# renovate: datasource=github-releases depName=bazel-contrib/buildtools
BUILDIFIER_VERSION=v10.1.0
# renovate: datasource=npm depName=prettier
PRETTIER_VERSION=3.9.10
# shell-trap-lint is fetched as a commit, which git verifies by its name, so
# it has no digest below; the tag beside it is the release that commit is.
# renovate: datasource=github-tags depName=curlewlabs-com/shell-trap-lint pin=digest
SHELL_TRAP_LINT_COMMIT=1910d5e1ddecbf83ca9e91bc44636722ee85980e # v0.1.2
# A bump moves a version and leaves these stale, since a digest cannot be
# typed from a version; tools/refresh_tools.py downloads each asset and
# rewrites them.
ACTIONLINT_SHA256_X86_64=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8
ACTIONLINT_SHA256_AARCH64=325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6
SHELLCHECK_SHA256_X86_64=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198
SHELLCHECK_SHA256_AARCH64=12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588
ZIZMOR_SHA256_X86_64=d185f726bdaf92df78273217dfdd24ebcd6b0ef48cf3ce776ff5762b6e138c99
ZIZMOR_SHA256_AARCH64=37eebbd5762a44f262d94875431b14a6d2402991e90a685113ea97b8b41be833
RUFF_SHA256_X86_64=2b0890f5a55900af741f133918c2656919bbf18c2ab7741b4ca8403a90e647a9
RUFF_SHA256_AARCH64=3f4639152c0e42bb5938e6c23d53d527a38f3133e000102934518f90529fa299
SHFMT_SHA256_X86_64=76e77641faa025814b77f153b29796b8e6fa2fca03e0c76a691608b86c7ea7bf
SHFMT_SHA256_AARCH64=5f2db09dae91fca848f7adbdd014632e921a383863a2ad7e0450ad3aba0c6489
BUILDIFIER_SHA256_X86_64=31b6a8aa1e5c746696788f428729701770ad91925873d8256cb885c60e12c77e
BUILDIFIER_SHA256_AARCH64=38d2ed845f560b4a16ddee41de906508a95f8dc85b04e0851b0a71e3a70d3890
# prettier is JavaScript with no dependencies, so one tarball serves every
# architecture.
PRETTIER_SHA256=9dc72045591793dff972432fb78722f7ab91aaa90a7fa8c1261ede55969246b7

case "$(uname -s)-$(uname -m)" in
Linux-x86_64)
	actionlint_arch=amd64 actionlint_sha256=$ACTIONLINT_SHA256_X86_64
	shellcheck_arch=x86_64 shellcheck_sha256=$SHELLCHECK_SHA256_X86_64
	zizmor_arch=x86_64 zizmor_sha256=$ZIZMOR_SHA256_X86_64
	ruff_arch=x86_64 ruff_sha256=$RUFF_SHA256_X86_64
	shfmt_arch=amd64 shfmt_sha256=$SHFMT_SHA256_X86_64
	buildifier_arch=amd64 buildifier_sha256=$BUILDIFIER_SHA256_X86_64
	;;
Linux-aarch64)
	actionlint_arch=arm64 actionlint_sha256=$ACTIONLINT_SHA256_AARCH64
	shellcheck_arch=aarch64 shellcheck_sha256=$SHELLCHECK_SHA256_AARCH64
	zizmor_arch=aarch64 zizmor_sha256=$ZIZMOR_SHA256_AARCH64
	ruff_arch=aarch64 ruff_sha256=$RUFF_SHA256_AARCH64
	shfmt_arch=arm64 shfmt_sha256=$SHFMT_SHA256_AARCH64
	buildifier_arch=arm64 buildifier_sha256=$BUILDIFIER_SHA256_AARCH64
	;;
*)
	echo "ci-baseline: runs on Linux x86_64 or aarch64, not $(uname -s)-$(uname -m)" >&2
	exit 1
	;;
esac

bin=$RUNNER_TEMP/ci-baseline/bin
work=$RUNNER_TEMP/ci-baseline/download
shell_trap_lint=$RUNNER_TEMP/ci-baseline/shell-trap-lint
rm -rf "$work" "$shell_trap_lint"
mkdir -p "$bin" "$work"

# fetch URL SHA256 FILE: download URL to FILE and refuse it unless its digest
# is SHA256. Retries cover a refused connection and a server error; a digest
# mismatch is never retried, since another download of the same URL that
# differs is the thing the digest exists to refuse.
fetch() {
	curl -fsSL --retry 3 --retry-connrefused --retry-all-errors -o "$3" "$1"
	if ! echo "$2  $3" | sha256sum -c - >/dev/null; then
		echo "ci-baseline: $1 does not have the pinned digest $2" >&2
		exit 1
	fi
}

v=${ACTIONLINT_VERSION#v}
fetch "https://github.com/rhysd/actionlint/releases/download/$ACTIONLINT_VERSION/actionlint_${v}_linux_${actionlint_arch}.tar.gz" \
	"$actionlint_sha256" "$work/actionlint.tar.gz"
tar -xzf "$work/actionlint.tar.gz" -C "$work" actionlint
mv "$work/actionlint" "$bin/actionlint"

fetch "https://github.com/koalaman/shellcheck/releases/download/$SHELLCHECK_VERSION/shellcheck-$SHELLCHECK_VERSION.linux.$shellcheck_arch.tar.xz" \
	"$shellcheck_sha256" "$work/shellcheck.tar.xz"
tar -xJf "$work/shellcheck.tar.xz" -C "$work"
mv "$work/shellcheck-$SHELLCHECK_VERSION/shellcheck" "$bin/shellcheck"

fetch "https://github.com/zizmorcore/zizmor/releases/download/$ZIZMOR_VERSION/zizmor-$zizmor_arch-unknown-linux-gnu.tar.gz" \
	"$zizmor_sha256" "$work/zizmor.tar.gz"
tar -xzf "$work/zizmor.tar.gz" -C "$work"
mv "$work/zizmor" "$bin/zizmor"

fetch "https://github.com/astral-sh/ruff/releases/download/$RUFF_VERSION/ruff-$ruff_arch-unknown-linux-gnu.tar.gz" \
	"$ruff_sha256" "$work/ruff.tar.gz"
tar -xzf "$work/ruff.tar.gz" -C "$work"
mv "$work/ruff-$ruff_arch-unknown-linux-gnu/ruff" "$bin/ruff"

# shfmt and buildifier are each published as the executable itself.
fetch "https://github.com/mvdan/sh/releases/download/$SHFMT_VERSION/shfmt_${SHFMT_VERSION}_linux_$shfmt_arch" \
	"$shfmt_sha256" "$work/shfmt"
fetch "https://github.com/bazel-contrib/buildtools/releases/download/$BUILDIFIER_VERSION/buildifier-linux-$buildifier_arch" \
	"$buildifier_sha256" "$work/buildifier"
chmod +x "$work/shfmt" "$work/buildifier"
mv "$work/shfmt" "$work/buildifier" "$bin/"

fetch "https://registry.npmjs.org/prettier/-/prettier-$PRETTIER_VERSION.tgz" \
	"$PRETTIER_SHA256" "$work/prettier.tgz"
tar -xzf "$work/prettier.tgz" -C "$work"
rm -rf "$bin/prettier"
mv "$work/package" "$bin/prettier"

# One commit, fetched by its full name: git refuses an object whose content
# does not hash to the name it was asked for, which is the check a digest
# makes for the downloads above. The lint runs from this tree, uninstalled.
git -c init.defaultBranch=main init -q "$shell_trap_lint"
attempt=1
until git -C "$shell_trap_lint" fetch -q --depth 1 \
	https://github.com/curlewlabs-com/shell-trap-lint "$SHELL_TRAP_LINT_COMMIT"; do
	if [ "$attempt" -ge 3 ]; then
		echo "ci-baseline: could not fetch shell-trap-lint $SHELL_TRAP_LINT_COMMIT" >&2
		exit 1
	fi
	attempt=$((attempt + 1))
	sleep 5
done
git -C "$shell_trap_lint" -c advice.detachedHead=false checkout -q FETCH_HEAD

rm -rf "$work"
"$bin/actionlint" -version | head -n 1
"$bin/shellcheck" --version | sed -n 2p
"$bin/zizmor" --version
"$bin/ruff" --version
echo "shfmt $("$bin/shfmt" --version)"
"$bin/buildifier" --version | head -n 1
echo "prettier $(node "$bin/prettier/bin/prettier.cjs" --version)"
echo "shell-trap-lint $(git -C "$shell_trap_lint" rev-parse HEAD)"
