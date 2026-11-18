#!/bin/sh
# Install the pinned actionlint, shellcheck, zizmor and prettier into
# $RUNNER_TEMP/ci-baseline/bin and verify each download's digest. A runner
# image's own copies move whenever the image does; these move only by a bump
# a pull request makes.
set -eu

# renovate: datasource=github-releases depName=rhysd/actionlint
ACTIONLINT_VERSION=v1.7.12
# renovate: datasource=github-releases depName=koalaman/shellcheck
SHELLCHECK_VERSION=v0.11.0
# renovate: datasource=github-releases depName=zizmorcore/zizmor
ZIZMOR_VERSION=v1.31.1
# renovate: datasource=npm depName=prettier
PRETTIER_VERSION=3.9.10
# A bump moves a version and leaves these stale, since a digest cannot be
# typed from a version; tools/refresh_tools.py downloads each asset and
# rewrites them.
ACTIONLINT_SHA256_X86_64=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8
ACTIONLINT_SHA256_AARCH64=325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6
SHELLCHECK_SHA256_X86_64=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198
SHELLCHECK_SHA256_AARCH64=12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588
ZIZMOR_SHA256_X86_64=d185f726bdaf92df78273217dfdd24ebcd6b0ef48cf3ce776ff5762b6e138c99
ZIZMOR_SHA256_AARCH64=37eebbd5762a44f262d94875431b14a6d2402991e90a685113ea97b8b41be833
# prettier is JavaScript with no dependencies, so one tarball serves every
# architecture.
PRETTIER_SHA256=9dc72045591793dff972432fb78722f7ab91aaa90a7fa8c1261ede55969246b7

case "$(uname -s)-$(uname -m)" in
Linux-x86_64)
	actionlint_arch=amd64 actionlint_sha256=$ACTIONLINT_SHA256_X86_64
	shellcheck_arch=x86_64 shellcheck_sha256=$SHELLCHECK_SHA256_X86_64
	zizmor_arch=x86_64 zizmor_sha256=$ZIZMOR_SHA256_X86_64
	;;
Linux-aarch64)
	actionlint_arch=arm64 actionlint_sha256=$ACTIONLINT_SHA256_AARCH64
	shellcheck_arch=aarch64 shellcheck_sha256=$SHELLCHECK_SHA256_AARCH64
	zizmor_arch=aarch64 zizmor_sha256=$ZIZMOR_SHA256_AARCH64
	;;
*)
	echo "ci-baseline: runs on Linux x86_64 or aarch64, not $(uname -s)-$(uname -m)" >&2
	exit 1
	;;
esac

bin=$RUNNER_TEMP/ci-baseline/bin
work=$RUNNER_TEMP/ci-baseline/download
rm -rf "$work"
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

fetch "https://registry.npmjs.org/prettier/-/prettier-$PRETTIER_VERSION.tgz" \
	"$PRETTIER_SHA256" "$work/prettier.tgz"
tar -xzf "$work/prettier.tgz" -C "$work"
rm -rf "$bin/prettier"
mv "$work/package" "$bin/prettier"

rm -rf "$work"
"$bin/actionlint" -version | head -n 1
"$bin/shellcheck" --version | sed -n 2p
"$bin/zizmor" --version
echo "prettier $(node "$bin/prettier/bin/prettier.cjs" --version)"
