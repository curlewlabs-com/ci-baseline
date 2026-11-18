"""The pyright strict policy: the mode, the back-offs, and which files are tests.

Owns the one configuration every Python file a repository tracks is held to,
and nothing about which files a run checks or how a verdict is read. The
policy is strict, at one pyright version, with the back-offs below and no
others, each a rule that fights a legitimate idiom rather than one that is
expensive to satisfy.

A back-off is changed here or nowhere: a repository carries no pyright
configuration of its own, and a `# pyright: ignore[<rule>]` on one line, with
its reason beside it, is how a single line that genuinely needs one says so
(comments.py says which pyright comments a file may carry).
"""

from __future__ import annotations

import re

# strict turns every rule pyright has to `error`; the rules it ships off stay
# off. The back-offs below are applied on top of it.
MODE = "strict"

# Applied to every file. Its findings were false or idiom fights: pyright
# reads `set == frozenset` as a comparison that can never hold (it holds), and
# reports `case x: assert_never(x)`, the exhaustiveness idiom, as a pattern
# that never matches. mypy's --strict-equality, which --strict enables, holds
# the comparisons that really cannot be equal.
EVERYWHERE: dict[str, str] = {"reportUnnecessaryComparison": "none"}

# Applied to test files only, in addition to EVERYWHERE.
#   reportPrivateUsage       a test calling a module's private helper is how
#                            that helper is tested. Outside tests the rule
#                            holds: a name used outside its module is not
#                            private.
#   reportUnknownLambdaType  a lambda handed to `mock.patch` has no declared
#                            type to infer its parameters from, and a lambda's
#                            parameters cannot be annotated, so the only fix is
#                            rewriting each as a `def`.
TESTS_ONLY: dict[str, str] = {
    "reportPrivateUsage": "none",
    "reportUnknownLambdaType": "none",
}

# pyright honours a mypy `# type: ignore[<code>]` as a suppression of every
# pyright finding on its line, whatever the code names, unless this is off. A
# mypy suppression silencing a pyright finding nobody looked at is a leak, not a
# back-off, so a line that needs each checker quiet carries a comment for each.
SETTINGS: dict[str, bool] = {"enableTypeIgnoreComments": False}

# A test is a file named for a test (`test_*`, `*_test`, `conftest`) or for a
# test's support module (`*_test_support`), or any file under a directory named
# `test` or `tests`.
_TEST_FILE = re.compile(
    r"(?:^|/)(?:test_[^/]*|[^/]*_test|[^/]*_test_support|conftest)\.pyi?$"
    r"|(?:^|/)tests?/"
)


def is_test_file(path: str) -> bool:
    """Whether `path`, repository-relative with `/` separators, is a test."""
    return _TEST_FILE.search(path) is not None


def strict_config(base: dict[str, object], *, tests: bool) -> dict[str, object]:
    """`base`, pyright's search and version settings, under the policy.

    `tests` says which half of the policy applies: the configuration a run over
    test files reads carries TESTS_ONLY too. A configuration of its own for the
    tests rather than an execution environment per test file in one, because
    pyright resolves imports separately for each environment, so the cost of a
    run grows with the number of test files rather than staying one run's.
    """
    config: dict[str, object] = {
        **base,
        "typeCheckingMode": MODE,
        **SETTINGS,
        **EVERYWHERE,
    }
    if tests:
        config.update(TESTS_ONLY)
    return config
