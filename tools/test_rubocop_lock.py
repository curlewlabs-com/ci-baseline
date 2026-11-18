"""Tests for rubocop_lock, against recorded rubygems.org records.

testdata/rubygems/rubocop-<version>.json are the records
https://rubygems.org/api/v2/rubygems/rubocop/versions/<version>.json served
on 2026-11-18, cut down to the fields rubocop_lock reads. A test that needs a
shape no real release has derives it from one of them, and says so.
"""

from __future__ import annotations

import json
import unittest
from collections.abc import Mapping
from pathlib import Path

import rubocop_lock

RECORDS = Path(__file__).resolve().parent / "testdata/rubygems"
# The lock Bundler wrote for rubocop 1.92.2 in the pinned image, as
# lib/rubocop/Gemfile.lock held it; fixed here so a later bump of the real lock
# leaves the tests' starting point where it was.
LOCK = (
    Path(__file__).resolve().parent / "testdata/rubocop-1.92.2.Gemfile.lock"
).read_text()
RUBY = "4.0.9"
OLD_SHA = "14fb31eed143a0dc6f78186c550c1715e81cd38f59d05d1165050e445c1f5382"
NEW_SHA = "fd77feac46e8e91c3a534f868a1702c59f5bf8173515fd00a3c6ce1198672ff6"


def gemfile(version: str) -> str:
    return (
        "# frozen_string_literal: true\n\n"
        'source "https://rubygems.org"\n\n'
        f'gem "rubocop", "{version}"\n'
    )


def recorded(version: str) -> bytes:
    return (RECORDS / f"rubocop-{version}.json").read_bytes()


def serve(*bodies: tuple[str, bytes]) -> tuple[list[str], rubocop_lock.Fetch]:
    """A fetch that serves each (version, body) at its record URL, and logs."""
    by_url = {rubocop_lock.RECORD.format(version=v): body for v, body in bodies}
    asked: list[str] = []

    def fetch(url: str) -> bytes:
        asked.append(url)
        return by_url[url]

    return asked, fetch


def lock_at(version: str, **locked: str) -> str:
    """The repository's lock as Bundler would have written it for an earlier
    rubocop `version`, with each gem in `locked` at the version given."""
    record = json.loads(recorded(version))
    text = rubocop_lock.rewrite(
        gemfile(version), LOCK, RUBY, serve((version, recorded(version)))[1]
    )
    for name, value in locked.items():
        lines = []
        for line in text.split("\n"):
            if line.startswith(f"    {name} ("):
                line = f"    {name} ({value})"
            lines.append(line)
        text = "\n".join(lines)
    assert record["number"] == version
    return text


class Rewrite(unittest.TestCase):
    def test_a_patch_bump_moves_only_rubocops_three_entries(self) -> None:
        # 1.92.2 -> 1.92.3, the bump the next Renovate run proposes: the
        # lines Bundler's `lock --conservative --update rubocop` changes, and
        # no others, so the frozen install sees the release's own checksum.
        asked, fetch = serve(("1.92.3", recorded("1.92.3")))
        new = rubocop_lock.rewrite(gemfile("1.92.3"), LOCK, RUBY, fetch)
        changed = [
            (a, b)
            for a, b in zip(LOCK.split("\n"), new.split("\n"), strict=True)
            if a != b
        ]
        self.assertEqual(
            changed,
            [
                ("    rubocop (1.92.2)", "    rubocop (1.92.3)"),
                ("  rubocop (= 1.92.2)", "  rubocop (= 1.92.3)"),
                (
                    f"  rubocop (1.92.2) sha256={OLD_SHA}",
                    f"  rubocop (1.92.3) sha256={NEW_SHA}",
                ),
            ],
        )
        self.assertEqual(asked, [rubocop_lock.RECORD.format(version="1.92.3")])

    def test_the_lock_it_writes_for_the_locked_release_is_the_committed_one(
        self,
    ) -> None:
        # The dependency lines are rebuilt from the record, so writing 1.92.2
        # from 1.91.0's lock must reproduce what Bundler wrote: Bundler's
        # order of a dependency's requirements is the case this pins.
        older = lock_at("1.91.0")
        _, fetch = serve(("1.92.2", recorded("1.92.2")))
        self.assertEqual(
            rubocop_lock.rewrite(gemfile("1.92.2"), older, RUBY, fetch), LOCK
        )

    def test_a_lock_already_at_the_pin_is_left_alone_without_a_request(self) -> None:
        asked, fetch = serve()
        self.assertEqual(
            rubocop_lock.rewrite(gemfile("1.92.2"), LOCK, RUBY, fetch), LOCK
        )
        self.assertEqual(asked, [])


class Refusals(unittest.TestCase):
    """Each shape the writer cannot answer for, refused with the relock."""

    def assertRefused(
        self, gem: str, lock: str, fetch: rubocop_lock.Fetch, why: str
    ) -> None:
        with self.assertRaises(rubocop_lock.LockError) as raised:
            rubocop_lock.rewrite(gem, lock, RUBY, fetch)
        self.assertIn(why, str(raised.exception))
        self.assertIn("Relocking RuboCop", str(raised.exception))

    def test_a_raised_floor_the_lock_does_not_meet_needs_the_relock(self) -> None:
        # The real case: 1.92.0 raised regexp_parser's floor to 2.11.3. A lock
        # written for 1.91.0 that holds regexp_parser 2.10.0 cannot take it
        # without moving regexp_parser, which only Bundler may decide.
        older = lock_at("1.91.0", regexp_parser="2.10.0")
        _, fetch = serve(("1.92.0", recorded("1.92.0")))
        self.assertRefused(
            gemfile("1.92.0"),
            older,
            fetch,
            "needs regexp_parser >= 2.11.3, < 3.0, and the lock has regexp_parser 2.10.0",
        )

    def derived(self, change: Mapping[str, object]) -> rubocop_lock.Fetch:
        # 1.92.3's record with one field changed: no real release has these.
        record = json.loads(recorded("1.92.3"))
        record.update(change)
        return serve(("1.92.3", json.dumps(record).encode()))[1]

    def test_a_new_dependency(self) -> None:
        record = json.loads(recorded("1.92.3"))
        runtime = record["dependencies"]["runtime"] + [
            {"name": "prism", "requirements": ">= 1.7"}
        ]
        fetch = self.derived({"dependencies": {"development": [], "runtime": runtime}})
        self.assertRefused(gemfile("1.92.3"), LOCK, fetch, "depends on")

    def test_a_prerelease_or_platform_gem(self) -> None:
        for change in ({"prerelease": True}, {"platform": "java"}, {"yanked": True}):
            with self.subTest(change):
                self.assertRefused(
                    gemfile("1.92.3"), LOCK, self.derived(change), "only a released"
                )

    def test_a_ruby_the_image_does_not_have(self) -> None:
        fetch = self.derived({"ruby_version": ">= 4.1.0"})
        self.assertRefused(gemfile("1.92.3"), LOCK, fetch, "requires Ruby")

    def test_a_rubygems_requirement(self) -> None:
        fetch = self.derived({"rubygems_version": ">= 3.6"})
        self.assertRefused(gemfile("1.92.3"), LOCK, fetch, "requires RubyGems")

    def test_a_record_for_another_release(self) -> None:
        fetch = self.derived({"number": "1.92.4"})
        self.assertRefused(gemfile("1.92.3"), LOCK, fetch, "not rubocop 1.92.3")

    def test_a_requirement_form_it_does_not_read(self) -> None:
        record = json.loads(recorded("1.92.3"))
        runtime = [dict(d) for d in record["dependencies"]["runtime"]]
        runtime[0]["requirements"] = ">= 2.3.a"
        fetch = self.derived({"dependencies": {"development": [], "runtime": runtime}})
        self.assertRefused(
            gemfile("1.92.3"), LOCK, fetch, "not a plain numeric version"
        )

    def test_a_gemfile_with_more_than_rubocop(self) -> None:
        gem = gemfile("1.92.3") + 'gem "rubocop-performance", "1.27.0"\n'
        self.assertRefused(gem, LOCK, serve()[1], "not rubocop alone")

    def test_a_gemfile_line_it_does_not_read(self) -> None:
        gem = gemfile("1.92.3").replace('"1.92.3"', '"~> 1.92"')
        self.assertRefused(gem, LOCK, serve()[1], "not a plain numeric version")

    def test_a_lock_section_it_does_not_read(self) -> None:
        lock = LOCK.replace(
            "BUNDLED WITH", "RUBY VERSION\n  ruby 4.0.9\n\nBUNDLED WITH"
        )
        self.assertRefused(gemfile("1.92.3"), lock, serve()[1], "RUBY VERSION")

    def test_a_platform_variant_in_the_lock(self) -> None:
        lock = LOCK.replace(
            "    prism (1.8.2)\n", "    prism (1.8.2)\n    prism (1.8.2-x86_64-linux)\n"
        )
        self.assertRefused(gemfile("1.92.3"), lock, serve()[1], "prism")


class Requirements(unittest.TestCase):
    def test_the_pessimistic_operator(self) -> None:
        cases = [
            ("3.17.0.6", "~> 3.17.0.2", True),
            ("3.17.1", "~> 3.17.0.2", False),
            ("1.9", "~> 1.7", True),
            ("2.0", "~> 1.7", False),
            ("1.1.9", "~> 1.1.0", True),
            ("1.2.0", "~> 1.1.0", False),
            ("2", "~> 2", True),
            ("3", "~> 2", False),
        ]
        for version, requirement, expected in cases:
            with self.subTest(version=version, requirement=requirement):
                self.assertIs(rubocop_lock.satisfies(version, requirement), expected)

    def test_trailing_zeros_compare_equal(self) -> None:
        self.assertTrue(rubocop_lock.satisfies("4.0", "= 4.0.0"))
        self.assertTrue(rubocop_lock.satisfies("4.0.9", "< 4.1"))
        self.assertFalse(rubocop_lock.satisfies("4.1", "< 4.1.0"))


if __name__ == "__main__":
    unittest.main()
