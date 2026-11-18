"""Which pyright comments a file may carry.

A file-level directive or an ignore naming no rule changes the verdict for more
than the line it is on, so a miss here is a finding the policy would report
going unreported; a false refusal fails a file that follows the policy.
"""

import tempfile
import unittest
from pathlib import Path

from ci_baseline_pyright.comments import refusals


class TestRefusals(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def refused(self, source: str) -> list[int]:
        (self.root / "case.py").write_text(source, encoding="utf-8")
        return [refusal.line for refusal in refusals(self.root, "case.py")]

    def test_an_ignore_naming_rules_is_allowed(self) -> None:
        for comment in (
            "# pyright: ignore[reportAssignmentType]",
            "# pyright: ignore[reportAssignmentType, reportUnknownMemberType]",
            "#pyright:ignore[reportAssignmentType]",
            "# pyright: ignore [reportAssignmentType]",
            "# noqa: E501  # pyright: ignore[reportAssignmentType]",
        ):
            with self.subTest(comment=comment):
                self.assertEqual(self.refused(f'x: int = "s"  {comment}\n'), [])

    def test_an_ignore_naming_no_rule_is_refused(self) -> None:
        for comment in (
            "# pyright: ignore",
            "#pyright:ignore",
            "# pyright: ignore[]",
            "# pyright: ignore[ , ]",
            "# pyright: ignore because the stub is wrong",
            "# noqa: E501  # pyright: ignore",
        ):
            with self.subTest(comment=comment):
                self.assertEqual(self.refused(f'x: int = "s"  {comment}\n'), [1])

    def test_a_file_level_directive_is_refused_wherever_it_is(self) -> None:
        """pyright applies one to the whole file even below the code, and even
        beside code, where it also reports it."""
        for directive in (
            "# pyright: basic",
            "# pyright: standard",
            "# pyright: strict",
            "#pyright: reportUnknownMemberType=false",
            "# pyright: strict, reportPrivateUsage=false",
        ):
            with self.subTest(directive=directive):
                self.assertEqual(self.refused(f"{directive}\nx = 1\n"), [1])
                self.assertEqual(self.refused(f"x = 1\n\n{directive}\n"), [3])
                self.assertEqual(self.refused(f"x = 1  {directive}\n"), [1])

    def test_text_that_is_not_a_comment_is_not_read(self) -> None:
        source = (
            's = "# pyright: basic"\n'
            'doc = """\n# pyright: ignore\n"""\n'
            "# a note that mentions pyright: basic\n"
            "# pyright:basic is how a file would lower itself\n"
        )
        # The last line is a directive as pyright reads it: it begins with
        # `pyright:` and is not an ignore.
        self.assertEqual(self.refused(source), [6])

    def test_a_directive_in_a_template_string_field_is_refused(self) -> None:
        """pyright reads a comment in a 3.14 template string's replacement
        field as a comment; a python3 older than 3.14 tokenizes the whole
        template as one string, so its text is read conservatively there."""
        source = 'x = 1\ns = t"""{\nx  # pyright: reportAssignmentType=false\n}"""\n'
        self.assertEqual(self.refused(source), [3])

    def test_a_file_that_does_not_tokenize_is_refused(self) -> None:
        self.assertEqual(self.refused('x = "unterminated\n'), [1])


if __name__ == "__main__":
    unittest.main()
