"""What a repository states that pyright's configuration is built from, and the
configuration a repository may not carry.

A repository states two things, each where another tool already reads it, and
nothing here restates them:

  - the oldest Python it supports: ruff's `target-version`, read from the
    configuration ruff itself reads at the repository root (`.ruff.toml`, then
    `ruff.toml`, then a `pyproject.toml` with a `[tool.ruff]` table, the first
    that exists winning, as in ruff). `py312` is `3.12`.
  - the platform it is checked for: `[tool.mypy] platform` in the root
    `pyproject.toml`, `linux` where it is absent, the runner's.

Everything else is ci-baseline's: the policy (policy.py) and the search path
(repository_config), to which the caller adds only the directories it names in
the action's `python-search-paths` input. A
repository therefore carries no pyright configuration of its own: a tracked
`pyrightconfig.json`, anywhere, or a `[tool.pyright]` table in a tracked
`pyproject.toml` is refused. pyright never reads either here, so one left in
place would have a contributor believe it applies; and an editor that does
read it would judge the files differently from this check.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath
from typing import TypeGuard

# ruff's own order: in one directory, the first of these that exists is its
# configuration, and a pyproject.toml counts only where it has [tool.ruff].
RUFF_CONFIGURATIONS = (".ruff.toml", "ruff.toml", "pyproject.toml")

# mypy's `platform` values, which are `sys.platform`'s, and pyright's names for
# the same platforms.
PLATFORMS = {"linux": "Linux", "darwin": "Darwin", "win32": "Windows"}
DEFAULT_PLATFORM = "Linux"

_TARGET_VERSION = re.compile(r"py3([0-9]+)")


class ConfigError(Exception):
    """A repository states its floor or platform in a form this cannot read."""


def _is_table(value: object) -> TypeGuard[dict[str, object]]:
    # A TOML table's keys are always strings, so the element check is the
    # parser's, not this one's.
    return isinstance(value, dict)


def _load_toml(path: Path, shown: str) -> dict[str, object]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"cannot read {shown}: {error}") from error


def _table(document: dict[str, object], *keys: str) -> dict[str, object] | None:
    current: object = document
    for key in keys:
        current = current.get(key) if _is_table(current) else None
    return current if _is_table(current) else None


def python_floor(root: Path) -> str:
    """The `pythonVersion` pyright checks against: ruff's `target-version`."""
    for name in RUFF_CONFIGURATIONS:
        path = root / name
        if not path.is_file():
            continue
        document = _load_toml(path, name)
        if name == "pyproject.toml":
            table = _table(document, "tool", "ruff")
            if table is None:
                continue
            where = "[tool.ruff] in pyproject.toml"
        else:
            table = document
            where = name
        target = table.get("target-version")
        if target is None:
            raise ConfigError(
                f"{where} sets no target-version; pyright checks against the "
                "Python ruff does, so set it there"
            )
        matched = _TARGET_VERSION.fullmatch(target) if isinstance(target, str) else None
        if matched is None:
            raise ConfigError(
                f"{where} sets target-version to {target!r}, not one of ruff's "
                "`py3<minor>` values"
            )
        return f"3.{matched[1]}"
    raise ConfigError(
        "no ruff configuration at the repository root sets target-version; "
        "pyright checks against the Python ruff does, so set it in "
        f"{', '.join(RUFF_CONFIGURATIONS[:2])} or [tool.ruff] in pyproject.toml"
    )


def python_platform(root: Path) -> str:
    """The `pythonPlatform` pyright checks for: mypy's `platform`."""
    path = root / "pyproject.toml"
    if not path.is_file():
        return DEFAULT_PLATFORM
    table = _table(_load_toml(path, "pyproject.toml"), "tool", "mypy")
    platform = None if table is None else table.get("platform")
    if platform is None:
        return DEFAULT_PLATFORM
    if not isinstance(platform, str) or platform not in PLATFORMS:
        raise ConfigError(
            f"[tool.mypy] in pyproject.toml sets platform to {platform!r}, not "
            f"one of {', '.join(PLATFORMS)}"
        )
    return PLATFORMS[platform]


def own_configuration(root: Path, listed: Iterable[str]) -> list[str]:
    """Each tracked file that is, or holds, a pyright configuration, with what
    it is. `listed` is every tracked path; only those that exist are read."""
    found: list[str] = []
    for path in listed:
        name = PurePosixPath(path).name
        if name == "pyrightconfig.json":
            found.append(f"{path}: a pyright configuration")
        elif (
            name == "pyproject.toml"
            and (root / path).is_file()
            and _table(_load_toml(root / path, path), "tool", "pyright") is not None
        ):
            found.append(f"{path}: a [tool.pyright] table")
    return found


def search_paths(root: Path, named: str) -> list[Path]:
    """The directories `named`, one per line, resolved against `root`. Each
    must exist: a path an earlier step was to fill and did not would otherwise
    leave its imports unresolved with nothing saying why."""
    paths: list[Path] = []
    for line in named.splitlines():
        entry = line.strip()
        if not entry:
            continue
        path = (root / entry).resolve()
        if not path.is_dir():
            raise ConfigError(f"python-search-paths names {entry}, not a directory")
        paths.append(path)
    return paths


def repository_config(
    tree: Path,
    tracked: Sequence[str],
    *,
    floor: str,
    platform: str,
    search_paths: Sequence[Path],
    stubs: Path,
) -> dict[str, object]:
    """The settings the policy is applied on top of, for the tracked files laid
    out under `tree`.

    Each directory holding a tracked file is an execution environment of its
    own, searched first for the files in it, as a script's own directory is
    first on `sys.path`. After it come the root, for a test that imports its
    fixtures as `tests.support`; then every other directory of the tree,
    holding a tracked file or above one, for the import a script makes after
    putting one of them on its path, which no static check can see, and for
    the directory a package is imported from (`src`, for `src/pkg/`, with an
    `__init__` or a namespace package); then the caller's search paths. Where
    one module name is offered by more than one of these, pyright's own
    resolution order picks the file, which the README's "What this check
    assumes" states. A directory nested in another is listed first, since pyright gives a file the first
    environment whose root holds it. All paths are absolute. `stubs` is
    pyright's `stubPath`, named so that its default, a `typings` directory, is
    not looked for.
    """
    files = [PurePosixPath(path) for path in tracked]
    dirs = {path.parent for path in files} - {PurePosixPath(".")}
    searched = sorted(
        {parent for path in files for parent in path.parents} - {PurePosixPath(".")}
    )
    after = [str(path) for path in search_paths]
    environments: list[dict[str, object]] = [
        {
            "root": str(tree / directory),
            "extraPaths": [
                str(tree),
                *(str(tree / other) for other in searched if other != directory),
                *after,
            ],
        }
        for directory in sorted(dirs, key=lambda d: (-len(d.parts), str(d)))
    ]
    environments.append(
        {
            "root": str(tree),
            "extraPaths": [*(str(tree / other) for other in searched), *after],
        }
    )
    return {
        "pythonVersion": floor,
        "pythonPlatform": platform,
        "stubPath": str(stubs),
        "executionEnvironments": environments,
    }
