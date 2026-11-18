"""The verdict read from a pyright report.

A report this misreads as clean passes a tree with findings, so each way a
report can say less than it seems to - no JSON, no list, a file left
unanalysed, a finding without a position - must fail rather than pass.
"""

import json
import unittest

from ci_baseline_pyright.report import Finding, NoVerdict, errors

TREE = "/work/tree"


def _entry(path: str, severity: str, rule: str | None = None) -> dict[str, object]:
    entry: dict[str, object] = {
        "file": f"{TREE}/{path}",
        "severity": severity,
        "message": 'Type of parameter "value" is unknown',
        "range": {"start": {"line": 3, "character": 10}, "end": {}},
    }
    if rule is not None:
        entry["rule"] = rule
    return entry


def _report(entries: list[dict[str, object]], analysed: int) -> str:
    return json.dumps(
        {"generalDiagnostics": entries, "summary": {"filesAnalyzed": analysed}}
    )


class TestErrors(unittest.TestCase):
    def test_errors_count_and_warnings_do_not(self) -> None:
        output = _report(
            [
                _entry("case/a.py", "error", "reportUnknownParameterType"),
                _entry("case/a.py", "warning", "reportMissingModuleSource"),
                _entry("case/b.py", "error"),
            ],
            analysed=2,
        )
        found = errors(output, ["case/a.py", "case/b.py"], TREE)
        self.assertEqual(
            [str(finding) for finding in found],
            [
                (
                    'case/a.py:4:11 - error: Type of parameter "value" is unknown '
                    "(reportUnknownParameterType)"
                ),
                'case/b.py:4:11 - error: Type of parameter "value" is unknown',
            ],
        )
        self.assertIsInstance(found[0], Finding)

    def test_a_clean_report_has_no_errors(self) -> None:
        self.assertEqual(errors(_report([], analysed=1), ["a.py"], TREE), [])

    def test_a_report_that_says_less_is_no_verdict(self) -> None:
        for output, pattern in (
            ("Error: no such file", "no JSON report"),
            (json.dumps({"summary": {"filesAnalyzed": 1}}), "no generalDiagnostics"),
            (_report([], analysed=0), "analysed 0 of the 1"),
            (json.dumps({"generalDiagnostics": []}), "analysed None of the 1"),
            (_report([{"file": f"{TREE}/a.py"}], analysed=1), "no position"),
        ):
            with (
                self.subTest(output=output),
                self.assertRaisesRegex(NoVerdict, pattern),
            ):
                errors(output, ["a.py"], TREE)


if __name__ == "__main__":
    unittest.main()
