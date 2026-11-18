"""Which files the policy treats as tests, and which half of it each reads.

The test-only back-offs switch rules off, so a file read as a test that is not
one loses `reportPrivateUsage` where it is a real naming fault, and a test read
as code fails on the idiom the back-off exists for.
"""

import unittest

from ci_baseline_pyright.policy import (
    EVERYWHERE,
    MODE,
    SETTINGS,
    TESTS_ONLY,
    is_test_file,
    strict_config,
)


class TestIsTestFile(unittest.TestCase):
    def test_test_names_and_test_directories_are_tests(self) -> None:
        for path in (
            "test_root.py",
            "a/test_one.py",
            "a/one_test.py",
            "a/one_test_support.py",
            "a/conftest.py",
            "pkg/test/helper.py",
            "pkg/tests/deep/fixture.py",
            "tests/__init__.py",
            "a/test_one.pyi",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_test_file(path))

    def test_a_name_merely_containing_test_is_not(self) -> None:
        """`attest`, `latest` and a `testing` directory name code, not tests."""
        for path in (
            "a/attest.py",
            "a/latest_release.py",
            "a/testing/main.py",
            "a/contest.py",
            "a/tests_helper.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(is_test_file(path))


class TestStrictConfig(unittest.TestCase):
    def test_only_the_test_configuration_carries_the_test_back_offs(self) -> None:
        base: dict[str, object] = {"pythonVersion": "3.12"}
        code = strict_config(base, tests=False)
        tests = strict_config(base, tests=True)
        for rule in TESTS_ONLY:
            with self.subTest(rule=rule):
                self.assertNotIn(rule, code)
                self.assertEqual(tests[rule], "none")
        self.assertEqual(code["pythonVersion"], "3.12")
        self.assertEqual(base, {"pythonVersion": "3.12"})

    def test_both_are_strict_and_ignore_mypy_suppressions(self) -> None:
        """A mypy `# type: ignore` silences every pyright finding on its line
        unless the setting is off, in the tests as much as anywhere."""
        for tests in (False, True):
            config = strict_config({}, tests=tests)
            with self.subTest(tests=tests):
                self.assertEqual(config["typeCheckingMode"], MODE)
                self.assertIs(config["enableTypeIgnoreComments"], False)
                for rule, level in {**SETTINGS, **EVERYWHERE}.items():
                    self.assertEqual(config[rule], level)

    def test_the_policy_overrides_a_base_that_names_its_settings(self) -> None:
        """The base is ci-baseline's own, but nothing in it can lower the
        policy: the policy's keys are applied last."""
        base: dict[str, object] = {
            "typeCheckingMode": "basic",
            "enableTypeIgnoreComments": True,
        }
        config = strict_config(base, tests=False)
        self.assertEqual(config["typeCheckingMode"], "strict")
        self.assertIs(config["enableTypeIgnoreComments"], False)


if __name__ == "__main__":
    unittest.main()
