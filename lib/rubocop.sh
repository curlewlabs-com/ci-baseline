#!/bin/sh
# Lint every tracked Ruby file with RuboCop, under ci-baseline's configuration,
# lib/rubocop/config.yml, and nothing a repository carries: unlike a formatter,
# almost all a Ruby linter enforces is a choice of style, and a choice made once
# per repository is the copy that drifts.
#
# RuboCop runs in the pinned Ruby image, so no Ruby, gem, PATH entry, home
# directory or setting of the runner's reaches it. What crosses into the
# container is exactly: the image, pulled by digest; the repository, mounted
# read-only at /repo and the working directory; this directory's rubocop/,
# mounted read-only at /ci; the list of files to check, on standard input; the
# three Bundler settings named below; and the gems the lock names, fetched
# from rubygems.org and refused unless each matches its CHECKSUMS entry.
set -eu
listed=$RUNNER_TEMP/ci-baseline/files/listed
files=$RUNNER_TEMP/ci-baseline/files/ruby
lib=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
root=$(git rev-parse --show-toplevel)
cd "$root"
if [ ! -s "$files" ]; then
	echo "ci-baseline: no Ruby files to check"
	exit 0
fi
# RuboCop reads a .rubocop file in its working directory, here the
# repository's root, as more command-line options, which can narrow a run to
# nothing; and under --config it reads no .rubocop.yml at all. Either would
# leave a contributor believing the file applies, so one tracked anywhere, or a
# .rubocop at the root tracked or not, fails the run instead.
refused=$RUNNER_TEMP/ci-baseline/files/rubocop-configuration
grep -E '(^|/)\.rubocop(\.yml)?$' "$listed" >"$refused" || [ $? -eq 1 ]
if [ -e .rubocop ] && ! grep -qx '\.rubocop' "$refused"; then
	echo ".rubocop" >>"$refused"
fi
if [ -s "$refused" ]; then
	echo "ci-baseline: RuboCop runs under ci-baseline's configuration, and a repository carries none of its own; remove:" >&2
	sed 's/^/  /' "$refused" >&2
	exit 1
fi
image=$("$lib/install-tools.sh" ruby)
# The working directory is the repository's because RuboCop resolves the
# configuration's file patterns against it. BUNDLE_GEMFILE puts Bundler's root
# in /ci, so no Gemfile or .bundle/config of the repository's is read;
# BUNDLE_FROZEN makes it install exactly the lock; BUNDLE_VERSION=system keeps
# the image's own Bundler, verified with the image, rather than fetching the
# one the lock names. Nothing passes --autocorrect, and RUBOCOP_OPTS is not
# passed in. --force-exclusion is not passed: it would drop each named file
# whose name RuboCop's own patterns do not pick, an Appfile among them. The
# timeout ends a hung pull of gems or run well inside a job's own limit.
# shellcheck disable=SC2016  # the script is the container's, expanded there
tr '\n' '\0' <"$files" |
	timeout 900 docker run --rm --interactive --pull=never \
		--mount "type=bind,source=$root,target=/repo,readonly" \
		--mount "type=bind,source=$lib/rubocop,target=/ci,readonly" \
		--workdir /repo \
		--env BUNDLE_GEMFILE=/ci/Gemfile --env BUNDLE_FROZEN=true --env BUNDLE_VERSION=system \
		"$image" sh -euc '
			bundle install --retry 3 </dev/null >&2
			echo "rubocop $(bundle exec rubocop --version </dev/null)" >&2
			xargs -0 bundle exec rubocop --config /ci/config.yml --cache false --
		'
