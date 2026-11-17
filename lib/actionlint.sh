#!/bin/sh
# actionlint over the repository's workflows, passing the inline shell of each
# `run:` through the pinned shellcheck rather than whichever one is on PATH.
set -eu
bin=$RUNNER_TEMP/ci-baseline/bin
exec "$bin/actionlint" -color -shellcheck="$bin/shellcheck"
