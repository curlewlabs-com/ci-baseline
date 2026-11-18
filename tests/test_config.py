"""What a repository states for pyright, read where ruff and mypy read it.

A floor read from the wrong file checks code against a Python it does not
support, so a finding ruff and the repository's own tests never see would be
reported, or a real one missed; an unstated floor must fail rather than fall
back to a guess.
"""

import tempfile
import unittest
from pathlib import Path

from ci_baseline_pyright.config import (
    ConfigError,
    own_configuration,
    python_floor,
    python_platform,
    repository_config,
    search_paths,
)


class _Root(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name).resolve()

    def tearDown(self) -> None:
        self._dir.cleanup()

    def write(self, path: str, text: str) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(text, encoding="utf-8")


class TestFloor(_Root):
    def test_each_ruff_configuration_is_read(self) -> None:
        for name, text in (
            (".ruff.toml", 'target-version = "py311"\n'),
            ("ruff.toml", 'target-version = "py311"\n'),
            ("pyproject.toml", '[tool.ruff]\ntarget-version = "py311"\n'),
        ):
            with self.subTest(name=name):
                self.write(name, text)
                self.assertEqual(python_floor(self.root), "3.11")
                (self.root / name).unlink()

    def test_the_first_configuration_wins_as_in_ruff(self) -> None:
        """ruff reads one file and does not merge, so a later one's value is
        not the floor even when the first sets none."""
        self.write(".ruff.toml", 'target-version = "py313"\n')
        self.write("ruff.toml", 'target-version = "py310"\n')
        self.write("pyproject.toml", '[tool.ruff]\ntarget-version = "py39"\n')
        self.assertEqual(python_floor(self.root), "3.13")
        self.write(".ruff.toml", "line-length = 100\n")
        with self.assertRaisesRegex(ConfigError, r"\.ruff\.toml sets no target"):
            python_floor(self.root)

    def test_a_pyproject_without_a_ruff_table_is_passed_over(self) -> None:
        self.write("pyproject.toml", '[project]\nrequires-python = ">=3.10"\n')
        with self.assertRaisesRegex(ConfigError, "no ruff configuration"):
            python_floor(self.root)

    def test_an_unstated_or_unreadable_floor_fails(self) -> None:
        for text, pattern in (
            ("[tool.ruff]\nline-length = 100\n", "sets no target-version"),
            ('[tool.ruff]\ntarget-version = "3.12"\n', "not one of ruff's"),
            ('[tool.ruff]\ntarget-version = "py312"\n[tool.ruff', "cannot read"),
        ):
            with self.subTest(text=text):
                self.write("pyproject.toml", text)
                with self.assertRaisesRegex(ConfigError, pattern):
                    python_floor(self.root)


class TestPlatform(_Root):
    def test_mypy_platform_is_read_and_linux_is_the_default(self) -> None:
        self.assertEqual(python_platform(self.root), "Linux")
        self.write("pyproject.toml", "[tool.mypy]\nstrict = true\n")
        self.assertEqual(python_platform(self.root), "Linux")
        self.write("pyproject.toml", '[tool.mypy]\nplatform = "darwin"\n')
        self.assertEqual(python_platform(self.root), "Darwin")

    def test_a_platform_pyright_has_no_name_for_fails(self) -> None:
        self.write("pyproject.toml", '[tool.mypy]\nplatform = "freebsd"\n')
        with self.assertRaisesRegex(ConfigError, "freebsd"):
            python_platform(self.root)


class TestOwnConfiguration(_Root):
    def test_a_configuration_or_a_table_anywhere_is_found(self) -> None:
        self.write("pyproject.toml", '[tool.pyright]\ntypeCheckingMode = "off"\n')
        self.write("sub/pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        self.write("deep/sub/pyproject.toml", "[tool.pyright.defineConstant]\n")
        self.assertEqual(
            own_configuration(
                self.root,
                [
                    "pyproject.toml",
                    "sub/pyproject.toml",
                    "deep/sub/pyproject.toml",
                    "pyrightconfig.json",
                    "a/pyrightconfig.json",
                    "README.md",
                ],
            ),
            [
                "pyproject.toml: a [tool.pyright] table",
                "deep/sub/pyproject.toml: a [tool.pyright] table",
                "pyrightconfig.json: a pyright configuration",
                "a/pyrightconfig.json: a pyright configuration",
            ],
        )

    def test_a_listed_file_missing_from_the_checkout_is_not_read(self) -> None:
        self.assertEqual(own_configuration(self.root, ["pyproject.toml"]), [])


class TestSearchPaths(_Root):
    def test_relative_and_absolute_directories_are_resolved(self) -> None:
        (self.root / "vendor").mkdir()
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        named = f"vendor\n\n  {outside.name}  \n"
        self.assertEqual(
            search_paths(self.root, named),
            [self.root / "vendor", Path(outside.name).resolve()],
        )

    def test_a_path_that_is_not_a_directory_fails(self) -> None:
        self.write("vendor", "a file\n")
        for named in ("missing", "vendor"):
            with (
                self.subTest(named=named),
                self.assertRaisesRegex(ConfigError, named),
            ):
                search_paths(self.root, named)


class TestRepositoryConfig(unittest.TestCase):
    def test_a_namespace_package_is_imported_from_above_it(self) -> None:
        """`src/pkg/mod.py` with no `__init__` is `pkg.mod` from `src`."""
        config = repository_config(
            Path("/t"),
            ["src/pkg/mod.py", "tests/test_mod.py"],
            floor="3.12",
            platform="Linux",
            search_paths=[],
            stubs=Path("/empty"),
        )
        self.assertEqual(
            config["executionEnvironments"],
            [
                {"root": "/t/src/pkg", "extraPaths": ["/t", "/t/src", "/t/tests"]},
                {"root": "/t/tests", "extraPaths": ["/t", "/t/src", "/t/src/pkg"]},
                {"root": "/t", "extraPaths": ["/t/src", "/t/src/pkg", "/t/tests"]},
            ],
        )

    def test_each_directory_searches_itself_first_then_the_rest(self) -> None:
        """A sibling resolves from the script's own directory before any other,
        so two directories each with a `helper` module never read each other's;
        a package is imported from the directory above its top level."""
        tree, stubs, fetched = Path("/t"), Path("/empty"), Path("/fetched")
        config = repository_config(
            tree,
            [
                "top.py",
                "a/helper.py",
                "b/helper.py",
                "src/pkg/__init__.py",
                "src/pkg/sub/__init__.pyi",
            ],
            floor="3.12",
            platform="Linux",
            search_paths=[fetched],
            stubs=stubs,
        )
        self.assertEqual(
            config,
            {
                "pythonVersion": "3.12",
                "pythonPlatform": "Linux",
                "stubPath": "/empty",
                "executionEnvironments": [
                    {
                        "root": "/t/src/pkg/sub",
                        "extraPaths": [
                            "/t",
                            "/t/a",
                            "/t/b",
                            "/t/src",
                            "/t/src/pkg",
                            "/fetched",
                        ],
                    },
                    {
                        "root": "/t/src/pkg",
                        "extraPaths": [
                            "/t",
                            "/t/a",
                            "/t/b",
                            "/t/src",
                            "/t/src/pkg/sub",
                            "/fetched",
                        ],
                    },
                    {
                        "root": "/t/a",
                        "extraPaths": [
                            "/t",
                            "/t/b",
                            "/t/src",
                            "/t/src/pkg",
                            "/t/src/pkg/sub",
                            "/fetched",
                        ],
                    },
                    {
                        "root": "/t/b",
                        "extraPaths": [
                            "/t",
                            "/t/a",
                            "/t/src",
                            "/t/src/pkg",
                            "/t/src/pkg/sub",
                            "/fetched",
                        ],
                    },
                    {
                        "root": "/t",
                        "extraPaths": [
                            "/t/a",
                            "/t/b",
                            "/t/src",
                            "/t/src/pkg",
                            "/t/src/pkg/sub",
                            "/fetched",
                        ],
                    },
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
