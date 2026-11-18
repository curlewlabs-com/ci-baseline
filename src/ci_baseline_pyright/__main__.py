"""The pyright step: type-check every tracked Python file, strict, under policy.py.

lib/pyright.sh starts this after lib/tracked-files.sh has listed the tracked
files. It refuses what would change the verdict from inside the repository
(config.py's configuration files and comments.py's comments), then runs
pyright twice, once over the files that are not tests and once over the tests, each
under its half of the policy, and fails on any error either run reports.

WHAT REACHES PYRIGHT, and nothing else:

  - the tracked `.py` and `.pyi` files, copied as the checkout has them into a
    directory of their own, which is where pyright runs. An untracked file in
    the checkout - a module or stub an earlier step wrote, a `typings/`, a
    `.venv`, a `node_modules`, a `pyrightconfig.json` - is not in that copy, so
    nothing pyright resolves an import to can come from it;
  - the configuration built here, in a directory of its own named by
    `--project`, so pyright reads no other, with `extraPaths` into that copy
    and onto each directory the caller's `python-search-paths` names, and
    `stubPath` an empty directory;
  - pyright's own bundled typeshed, for the standard library.

pyright is started on the job's `node` with an environment of one variable,
PATH, naming that empty directory. So no variable of the caller's job
(NODE_OPTIONS, NODE_PATH, PYTHONPATH, HOME, anything) reaches it, and it finds
no Python interpreter to ask for installed packages: a repository's code
imports the standard library, its own files, and what the input names.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from ci_baseline_pyright import comments, config, report
from ci_baseline_pyright.policy import is_test_file, strict_config

# pyright is handed a file by name only when its name says it is Python; a
# script known only by its shebang cannot be given to it as one.
SUFFIXES = (".py", ".pyi")

# Ends a hung run well inside a job's own limit.
TIMEOUT_SECONDS = 900


def _lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line]


def _problems(root: Path, listed: list[str], tracked: list[str]) -> list[str]:
    """What the repository carries that would change the verdict from inside it."""
    try:
        problems = [
            f"{found}; ci-baseline's policy is the only one, so remove it"
            for found in config.own_configuration(root, listed)
        ]
    except config.ConfigError as error:
        problems = [str(error)]
    for path in tracked:
        problems += [str(refused) for refused in comments.refusals(root, path)]
    return problems


def _run(
    node: str, pyright: str, project: Path, tree: Path, empty: Path, files: list[str]
) -> list[report.Finding]:
    try:
        completed = subprocess.run(
            [
                node,
                pyright,
                "--outputjson",
                "--project",
                str(project),
                # Absolute, so no tracked name can be read as an option.
                *(str(tree / path) for path in files),
            ],
            cwd=tree,
            env={"PATH": str(empty)},
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise report.NoVerdict(f"pyright did not finish: {error}") from error
    if completed.returncode not in report.VERDICTS:
        raise report.NoVerdict(
            f"pyright exited {completed.returncode} with no verdict:\n"
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    return report.errors(completed.stdout, files, str(tree))


def check(root: Path, files: Path, pyright: str, work: Path, named: str) -> int:
    """The step's exit status, for the checkout at `root` whose tracked files
    tracked-files.sh listed into `files`."""
    tracked = [path for path in _lines(files / "python") if path.endswith(SUFFIXES)]
    if not tracked:
        print("ci-baseline: no Python files to check")
        return 0
    problems = _problems(root, _lines(files / "listed"), tracked)
    try:
        stated = (
            config.python_floor(root),
            config.python_platform(root),
            config.search_paths(root, named),
        )
    except config.ConfigError as error:
        problems.append(str(error))
        stated = None
    node = shutil.which("node")
    if node is None:
        problems.append("pyright runs on node, and there is none on PATH")
    if problems or stated is None or node is None:
        for problem in problems:
            print(f"ci-baseline: {problem}", file=sys.stderr)
        return 1
    floor, platform, extra = stated

    shutil.rmtree(work, ignore_errors=True)
    tree, projects, empty = work / "tree", work / "config", work / "empty"
    for directory in (tree, projects, empty):
        directory.mkdir(parents=True)
    for path in tracked:
        (tree / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / path, tree / path)
    base = config.repository_config(
        tree,
        tracked,
        floor=floor,
        platform=platform,
        search_paths=extra,
        stubs=empty,
    )
    passes = {
        "code": [path for path in tracked if not is_test_file(path)],
        "tests": [path for path in tracked if is_test_file(path)],
    }
    version = subprocess.run(
        [node, "--version"],
        env={"PATH": str(empty)},
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    print(
        f"pyright strict, Python {floor} on {platform}, node {version}: "
        f"{len(passes['code'])} files, "
        f"{len(passes['tests'])} test files",
        flush=True,
    )
    found: list[report.Finding] = []
    try:
        for name, checked in passes.items():
            if not checked:
                continue
            # Outside the copy: pyright drops a named file under a directory
            # beginning with `.`, or one named node_modules, below its
            # configuration's directory, whatever `exclude` says, so a tracked
            # `.github/check.py` would go unread were the configuration there.
            project = projects / f"{name}.json"
            settings = strict_config(base, tests=name == "tests")
            project.write_text(json.dumps(settings, indent=2), encoding="utf-8")
            found += _run(node, pyright, project, tree, empty, checked)
    except report.NoVerdict as error:
        print(f"ci-baseline: {error}", file=sys.stderr)
        return 1
    for finding in found:
        print(finding)
    if found:
        print(f"pyright: {len(found)} error(s)")
        return 1
    print("pyright: no errors")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ci_baseline_pyright", allow_abbrev=False)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--files", required=True, type=Path)
    parser.add_argument("--pyright", required=True)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--search-paths", default="")
    args = parser.parse_args(argv)
    return check(
        args.root.resolve(), args.files, args.pyright, args.work, args.search_paths
    )


if __name__ == "__main__":
    sys.exit(main())
