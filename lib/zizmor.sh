#!/bin/sh
# zizmor over the repository's workflows and actions, with this action's
# policy and nothing the repository carries: not its config, and not an
# inline ignore comment (--no-ignores), so one policy holds every repository
# that runs this. Every workflow and action is collected, .gitignore or not
# (--collect=all), and one zizmor cannot parse fails the run rather than being
# skipped (--strict-collection). GH_TOKEN, from the step, lets the audits that
# read GitHub run.
set -eu
exec "$RUNNER_TEMP/ci-baseline/bin/zizmor" --no-progress --format=github \
	--config "$GITHUB_ACTION_PATH/zizmor.yml" --no-ignores --collect=all \
	--strict-collection .
