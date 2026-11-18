"""pyright strict for every repository ci-baseline checks: the policy, and the
step that applies it.

policy.py is the policy, and the one module meant to be imported from outside:
another project that runs pyright itself reads the same back-offs from there
rather than restating them.
"""
