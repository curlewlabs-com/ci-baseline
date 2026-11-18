"""Decide what one eslint run reads, from the tracked files and what the
repository states, and write it as the plan lint/eslint.config.mjs reads.

    python3 -I lib/eslint_plan.py <tracked-files dir> <plan.json> <file-list>

A repository states what eslint should know about it in .ci-baseline/eslint.json,
and nothing else: no rule, severity, parser or plugin.

    {"ignore": [{"path": "<git glob>", "reason": "<why>"}]}

`ignore` takes tracked files out of the run, each pattern with a reason. A
pattern that matches no tracked JavaScript or TypeScript file is refused, since
whatever it excused is gone. Every file it takes out is named in the log, so
nothing is skipped silently.

The file list is every tracked JavaScript and TypeScript file but those an
`ignore` pattern takes out, written NUL-separated for xargs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

STATEMENT = ".ci-baseline/eslint.json"
KEYS = {"ignore"}


class StatementError(Exception):
    pass


def read_statement(root: Path) -> dict[str, Any]:
    path = root / STATEMENT
    if not path.exists():
        return {"ignore": []}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as err:
        raise StatementError(f"{STATEMENT} is not JSON: {err}") from err
    if not isinstance(data, dict):
        raise StatementError(f"{STATEMENT} is not an object")
    unknown = set(data) - KEYS
    if unknown:
        raise StatementError(
            f"{STATEMENT} states {', '.join(sorted(unknown))}; it may state only ignore"
        )
    ignore = data.get("ignore", [])
    if not isinstance(ignore, list):
        raise StatementError(f"{STATEMENT}: ignore is a list")
    for entry in ignore:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"path", "reason"}
            or not isinstance(entry["path"], str)
            or not isinstance(entry["reason"], str)
            or not entry["path"].strip()
            or not entry["reason"].strip()
        ):
            raise StatementError(
                f"{STATEMENT}: each ignore entry is a path and a reason, both"
                f" non-empty: {entry!r}"
            )
    return {"ignore": ignore}


def matched(root: Path, pattern: str) -> set[str]:
    # git's own glob pathspec, so a pattern means here what it means to git.
    out = subprocess.run(
        [
            "git",
            "-c",
            "core.quotePath=false",
            "ls-files",
            "-z",
            "--",
            f":(glob){pattern}",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {name for name in out.split("\0") if name}


def lines(path: Path) -> list[str]:
    return [line for line in path.read_text().split("\n") if line]


def plan(root: Path, files_dir: Path) -> tuple[dict[str, Any], list[str]]:
    statement = read_statement(root)
    tracked = lines(files_dir / "js")
    shebang = lines(files_dir / "js-shebang")
    tracked_set = set(tracked)
    excluded: set[str] = set()
    for entry in statement["ignore"]:
        hits = matched(root, entry["path"]) & tracked_set
        if not hits:
            raise StatementError(
                f"{STATEMENT}: ignore {entry['path']!r} matches no tracked JavaScript"
                " or TypeScript file"
            )
        for name in sorted(hits):
            print(
                f"ci-baseline: eslint skips {name}: {entry['reason']}", file=sys.stderr
            )
        excluded |= hits
    files = [name for name in tracked if name not in excluded]
    return {"extraFiles": [name for name in shebang if name not in excluded]}, files


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "usage: eslint_plan.py <tracked-files dir> <plan.json> <file-list>",
            file=sys.stderr,
        )
        return 2
    try:
        config, files = plan(Path.cwd(), Path(argv[1]))
    except StatementError as err:
        print(f"ci-baseline: {err}", file=sys.stderr)
        return 1
    Path(argv[2]).write_text(json.dumps(config))
    Path(argv[3]).write_text("".join(f"{name}\0" for name in files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
