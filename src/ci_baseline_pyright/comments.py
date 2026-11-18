"""Which pyright comments a tracked Python file may carry.

One: `# pyright: ignore[<rule>, ...]`, which silences the rules it names on
its own line and nothing else. pyright reads two other kinds, and each would
change the verdict for more than the line it is on, so a file carrying one is
refused before pyright runs:

  - a file-level directive, a comment that begins `pyright:` and is not an
    ignore: `# pyright: basic`, `# pyright: standard`, or
    `# pyright: reportUnknownMemberType=false`. pyright applies it to the whole
    file on top of the configuration, so it lowers strict, or switches a rule
    off, for every line of it;
  - an ignore that names no rule, `# pyright: ignore` or `# pyright: ignore[]`,
    which pyright reads as silencing every finding on its line.

Both are matched as pyright matches them, in a comment token (and, on a
python3 older than 3.14, in the text of a template string, which such a
python3 cannot tokenize; there any `#` is read as if it began a comment): a directive by
the comment's text, an ignore wherever `pyright:` follows the comment's start
or another `#` in it (`# noqa: E501 # pyright: ignore`). Only real comments are
read, through the tokenizer, so text in a string is never mistaken for one.
"""

from __future__ import annotations

import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

_DIRECTIVE = "pyright:"
# pyright's ignore: `pyright:` after a `#`, the comment's own or a later one,
# and blanks, then `ignore`, ending the comment or followed by a blank or `[`.
_IGNORE = re.compile(r"#[ \t]*pyright:[ \t]*ignore(?=$|[ \t\[])")
_RULES = re.compile(r"[ \t]*\[([^\]]*)\]")
_TEMPLATE_PREFIXES = ("t", "rt", "tr")


@dataclass(frozen=True, slots=True)
class Refusal:
    """A comment the policy refuses, or a file that could not be read for one."""

    path: str
    line: int
    detail: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.detail}"


def _comment_refusals(path: str, line: int, comment: str) -> list[Refusal]:
    found: list[Refusal] = []
    text = comment[1:].strip()
    if text.startswith(_DIRECTIVE) and not (
        text[len(_DIRECTIVE) :].strip().startswith("ignore")
    ):
        found.append(
            Refusal(
                path,
                line,
                f"`# {text}` changes pyright's rules for the whole file; the "
                "policy is ci-baseline's, so remove it, and silence one line "
                "with `# pyright: ignore[<rule>]` where a line needs it",
            )
        )
    for ignore in _IGNORE.finditer(comment):
        rules = _RULES.match(comment, ignore.end())
        named = [] if rules is None else [r for r in rules[1].split(",") if r.strip()]
        if not named:
            found.append(
                Refusal(
                    path,
                    line,
                    "a `# pyright: ignore` that names no rule silences every "
                    "finding on its line; name each rule, "
                    "`# pyright: ignore[<rule>]`, with the reason beside it",
                )
            )
    return found


def refusals(root: Path, path: str) -> list[Refusal]:
    """Each comment in the file at `path` under `root` that the policy refuses."""
    try:
        source = (root / path).read_bytes()
        tokens = list(tokenize.tokenize(io.BytesIO(source).readline))
    except (OSError, SyntaxError, UnicodeDecodeError, tokenize.TokenError) as error:
        return [Refusal(path, 1, f"cannot be read for its pyright comments: {error}")]
    found: list[Refusal] = []
    previous: tokenize.TokenInfo | None = None
    for token in tokens:
        if token.type == tokenize.COMMENT:
            found += _comment_refusals(path, token.start[0], token.string)
        elif _template_string(previous, token):
            found += _template_refusals(path, token)
        previous = token
    return found


def _template_string(
    previous: tokenize.TokenInfo | None, token: tokenize.TokenInfo
) -> bool:
    """Whether `token` is the body of a template string (`t"..."`, 3.14) that
    this python3 is too old to tokenize as one: it reads the prefix as a name
    and the rest as a plain string, so a comment in a replacement field, which
    pyright reads as a comment, would be hidden in that string."""
    return (
        sys.version_info < (3, 14)
        and token.type == tokenize.STRING
        and previous is not None
        and previous.type == tokenize.NAME
        and previous.string.lower() in _TEMPLATE_PREFIXES
        and previous.end == token.start
    )


def _template_refusals(path: str, token: tokenize.TokenInfo) -> list[Refusal]:
    """The refusals any `#` in the string's text would earn as a comment:
    read conservatively, since text and comment cannot be told apart here."""
    found: list[Refusal] = []
    for offset, line in enumerate(token.string.splitlines()):
        start = line.find("#")
        if start >= 0:
            found += _comment_refusals(path, token.start[0] + offset, line[start:])
    return found
