"""pyright strict for every repository ci-baseline checks: the policy, and the
step that applies it.

Two modules are meant to be imported from outside, so that another project
that runs pyright itself, or holds a repository to the same policy, reads them
from here rather than restating them:

  - policy.py, the policy.
  - config.py's readers of what a repository states, which the README's "What
    a repository configures" lists: `python_floor`, `python_platform`,
    `own_configuration`, `RUFF_CONFIGURATIONS`, and the `ConfigError` the
    readers raise.

The rest of config.py, and the other modules, are the step's own.
"""
