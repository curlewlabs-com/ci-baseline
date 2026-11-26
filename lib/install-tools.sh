#!/bin/sh
# Install the pinned tools the checks run into $RUNNER_TEMP/ci-baseline, and
# verify each download's digest. A runner image's own copies move whenever the
# image does; these move only by a bump a pull request makes.
#
#   install-tools.sh        every tool but the Ruby image
#   install-tools.sh ruby   pull the Ruby image RuboCop runs in, by its digest,
#                           and print its reference; lib/rubocop.sh asks for it
#                           only where Ruby is tracked
set -eu

# renovate: datasource=github-releases depName=rhysd/actionlint
ACTIONLINT_VERSION=v1.7.12
# renovate: datasource=github-releases depName=koalaman/shellcheck
SHELLCHECK_VERSION=v0.11.0
# renovate: datasource=github-releases depName=zizmorcore/zizmor
ZIZMOR_VERSION=v1.32.0
# renovate: datasource=github-releases depName=astral-sh/ruff
RUFF_VERSION=0.17.5
# renovate: datasource=github-releases depName=mvdan/sh
SHFMT_VERSION=v3.14.1
# renovate: datasource=github-releases depName=bazel-contrib/buildtools
BUILDIFIER_VERSION=v10.2.0
# renovate: datasource=npm depName=prettier
PRETTIER_VERSION=3.9.10
# renovate: datasource=npm depName=pyright
PYRIGHT_VERSION=1.1.414
# shell-trap-lint is fetched as a commit, which git verifies by its name, so
# it has no digest below; the tag beside it is the release that commit is.
# renovate: datasource=github-tags depName=curlewlabs-com/shell-trap-lint pin=digest
SHELL_TRAP_LINT_COMMIT=057267eb3555b881390a345c70053ad07105f063 # v0.1.4
# The official Ruby image RuboCop runs in, by tag and by the digest of its
# multi-architecture index, which is what is pulled; the tag is for a reader
# and for the update. Pulled from the Amazon ECR Public mirror of Docker's
# official images, the same bytes under the same digest as Docker Hub, which
# limits anonymous pulls per address and hosted runners share addresses; ECR
# Public limits them too, so Docker Hub is the fallback (pull_image below). The
# full image, not the slim one: Bundler builds json and prism, which RuboCop
# needs, from source even where the image's Ruby already carries the same
# versions, and only the full image has the compiler.
# renovate: datasource=docker depName=public.ecr.aws/docker/library/ruby pin=image
RUBY_VERSION=4.0.9-trixie@sha256:ac9b27edd4382328460376335b40bcc294c756be117ba93179cf0317f5e86bec
# A bump moves a version and leaves these stale, since a digest cannot be
# typed from a version; tools/refresh_tools.py downloads each asset and
# rewrites them.
ACTIONLINT_SHA256_X86_64=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8
ACTIONLINT_SHA256_AARCH64=325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6
SHELLCHECK_SHA256_X86_64=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198
SHELLCHECK_SHA256_AARCH64=12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588
ZIZMOR_SHA256_X86_64=bb110cc765eca9cd7efb2e284a956be5974c60027b0970f16397d86208a9957b
ZIZMOR_SHA256_AARCH64=cb152b207f815116d7fa1c1ee4614f61578803351395052908095e79adfd9fd0
RUFF_SHA256_X86_64=7d261fc981a784668e19e9fa6ad437bfd95b67f2dc263fc1eab87d54d72fcc90
RUFF_SHA256_AARCH64=4d959d4322a8cd3effe11e9fc6743da1dbb41cd0b2476e433b6e6bfd9a69b626
SHFMT_SHA256_X86_64=76e77641faa025814b77f153b29796b8e6fa2fca03e0c76a691608b86c7ea7bf
SHFMT_SHA256_AARCH64=5f2db09dae91fca848f7adbdd014632e921a383863a2ad7e0450ad3aba0c6489
BUILDIFIER_SHA256_X86_64=470844069d710d0b7740e55007071c63e4d00be89a833dce5d1a91790e84dc28
BUILDIFIER_SHA256_AARCH64=e33b41bdb36eca5dfa69647333f4f148272654b98cddcea12f38fac5ec0a00ff
# prettier and pyright are each JavaScript with no dependencies (pyright's
# one optional dependency is for macOS), so one tarball serves every
# architecture.
PRETTIER_SHA256=9dc72045591793dff972432fb78722f7ab91aaa90a7fa8c1261ede55969246b7
PYRIGHT_SHA256=bf5f473f6167c0d14175492c3263d783b4489a6956e1c06c18e15228e3a3fa42

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

# pull_image REFERENCE: pull REFERENCE, a tag and digest, and print it.
# Returns 0 when pulled, and 2 when this registry could not serve it, so the
# next registry may. Docker refuses content that does not hash to the digest
# named, and that refusal exits at once, never retried or passed to the other
# registry: the same digest served differently is what the pin exists to stop.
# A registry that answers that it has no such image is left for the next one
# without a retry. Every other failure - a rate limit, a 5xx, a network or TLS
# failure, an attempt cut off by the timeout - is retried: Docker words these
# many ways, and a list of them is the list that misses one, while asking again
# costs only the backoff. A registry gets PULL_ATTEMPTS attempts, each ended by
# a TERM after PULL_TIMEOUT seconds and a KILL 10 seconds later, 5 and then 15
# seconds apart, so whatever Docker prints or fails to print the two registries
# spend at most 2 * (3 * 190 + 20) = 1180 seconds before the step fails; with
# lib/rubocop.sh's 900-second run that is well inside a job's default 360
# minutes.
PULL_ATTEMPTS=3
PULL_TIMEOUT=180
pull_image() {
	log=$(mktemp)
	attempt=1
	delay=5
	while :; do
		status=0
		timeout -k 10 "$PULL_TIMEOUT" docker pull --quiet "$1" >"$log" 2>&1 || status=$?
		if [ "$status" -eq 0 ]; then
			rm -f "$log"
			echo "$1"
			return 0
		fi
		cat "$log" >&2
		if grep -Eqi 'verification failed|digest mismatch|unexpected commit digest|failed precondition' "$log"; then
			echo "ci-baseline: $1 does not have the pinned digest" >&2
			exit 1
		fi
		if grep -Eqi 'manifest unknown|not found|pull access denied' "$log"; then
			echo "ci-baseline: $1 is not served by this registry" >&2
			rm -f "$log"
			return 2
		fi
		if [ "$attempt" -ge "$PULL_ATTEMPTS" ]; then
			echo "ci-baseline: $1 failed on all $PULL_ATTEMPTS attempts" >&2
			rm -f "$log"
			return 2
		fi
		echo "ci-baseline: $1 failed (attempt $attempt of $PULL_ATTEMPTS); retrying in $delay seconds" >&2
		sleep "$delay"
		attempt=$((attempt + 1))
		delay=$((delay * 3))
	done
}

if [ "${1:-}" = ruby ]; then
	if ! command -v docker >/dev/null; then
		echo "ci-baseline: RuboCop runs in a container, and this runner has no docker; the README names the runners the action supports" >&2
		exit 1
	fi
	for repository in public.ecr.aws/docker/library/ruby docker.io/library/ruby; do
		status=0
		pull_image "$repository:$RUBY_VERSION" || status=$?
		if [ "$status" -eq 0 ]; then
			exit 0
		fi
		echo "ci-baseline: $repository could not serve the Ruby image; trying the next registry" >&2
	done
	echo "ci-baseline: could not pull the Ruby image from ECR Public or Docker Hub" >&2
	exit 1
fi

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

fetch "https://registry.npmjs.org/pyright/-/pyright-$PYRIGHT_VERSION.tgz" \
	"$PYRIGHT_SHA256" "$work/pyright.tgz"
tar -xzf "$work/pyright.tgz" -C "$work"
rm -rf "$bin/pyright"
mv "$work/package" "$bin/pyright"

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
node "$bin/pyright/index.js" --version
echo "shell-trap-lint $(git -C "$shell_trap_lint" rev-parse HEAD)"
