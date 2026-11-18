"""Read the verdict out of one pyright run's `--outputjson` report.

pyright exits 0 when it found nothing and 1 when it found something; any other
status (a fatal error, a configuration it could not read, a file that does not
exist) means it reached no verdict, and what it printed is not a report. A
report is also no verdict unless it says it analysed every file it was given:
a file it skipped would otherwise pass unread. Only an `error` counts; strict
leaves a few rules at `warning`, and those are pyright's to say, not this
check's.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeGuard

VERDICTS = (0, 1)


class NoVerdict(Exception):
    """pyright reached no verdict, so its output holds no findings to read."""


@dataclass(frozen=True, slots=True)
class Finding:
    """One pyright finding, its path repository-relative."""

    path: str
    line: int
    column: int
    severity: str
    message: str
    rule: str | None

    def __str__(self) -> str:
        rule = f" ({self.rule})" if self.rule else ""
        return (
            f"{self.path}:{self.line}:{self.column} - {self.severity}: "
            f"{self.message}{rule}"
        )


def _is_object(value: object) -> TypeGuard[dict[str, object]]:
    # JSON object keys are always strings, so the element check is json's.
    return isinstance(value, dict)


def _is_array(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _finding(entry: object, names: Mapping[str, str], tree: str) -> Finding:
    span = entry.get("range") if _is_object(entry) else None
    start = span.get("start") if _is_object(span) else None
    if not _is_object(entry) or not _is_object(start):
        raise NoVerdict(f"pyright reported a finding with no position: {entry}")
    path, severity = entry.get("file"), entry.get("severity")
    message, rule = entry.get("message"), entry.get("rule")
    line, column = start.get("line"), start.get("character")
    if not (
        isinstance(path, str)
        and isinstance(severity, str)
        and isinstance(message, str)
        and (rule is None or isinstance(rule, str))
        and isinstance(line, int)
        and isinstance(column, int)
    ):
        raise NoVerdict(f"pyright reported a finding this cannot read: {entry}")
    # pyright counts lines and columns from zero and prints them from one.
    return Finding(
        path=names.get(os.path.realpath(path), os.path.relpath(path, tree)),
        line=line + 1,
        column=column + 1,
        severity=severity,
        message=message,
        rule=rule,
    )


def errors(output: str, files: list[str], tree: str) -> list[Finding]:
    """The errors in the report pyright printed for `files`, each a path
    relative to `tree`, the directory it ran in."""
    try:
        report: object = json.loads(output)
    except ValueError as error:
        raise NoVerdict(f"pyright printed no JSON report: {error}") from error
    entries = report.get("generalDiagnostics") if _is_object(report) else None
    summary = report.get("summary") if _is_object(report) else None
    analysed = summary.get("filesAnalyzed") if _is_object(summary) else None
    if not _is_array(entries):
        raise NoVerdict("pyright's report has no generalDiagnostics list")
    if analysed != len(files):
        raise NoVerdict(
            f"pyright analysed {analysed} of the {len(files)} files it was given"
        )
    names = {os.path.realpath(os.path.join(tree, path)): path for path in files}
    found = [_finding(entry, names, tree) for entry in entries]
    return [finding for finding in found if finding.severity == "error"]
