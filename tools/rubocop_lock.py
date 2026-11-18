"""Move lib/rubocop/Gemfile.lock to the RuboCop release the Gemfile pins.

A RuboCop bump moves the `gem "rubocop", "<version>"` line of
lib/rubocop/Gemfile and leaves the lock naming the old release. Bundler would
relock it, but the hosts that finish a bump have no Ruby, and a relock outside
the pinned image would also rewrite `BUNDLED WITH` and move every other gem to
its newest release. So this rewrites the lock's three RuboCop entries - its
spec and dependency lines under GEM, its DEPENDENCIES line and its CHECKSUMS
line - from the release's rubygems.org record, and keeps every other gem at
the version already locked.

That is only Bundler's answer when the locked gems still satisfy the new
release, so it refuses instead, changing nothing, whenever a dependency's
locked version falls outside the new requirement, the release adds or drops a
dependency, or anything in the Gemfile, the lock or the record is a shape this
does not model. The refusal names the documented relock in the pinned image
(CONTRIBUTING.md, "Relocking RuboCop"). Nothing here has to be right for the
lock to be trusted: the RuboCop check installs it frozen, so Bundler refuses a
lock whose checksums or dependencies are not the release's.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

RELOCK = (
    'relock in the pinned image instead, as CONTRIBUTING.md\'s "Relocking RuboCop" says'
)

RECORD = "https://rubygems.org/api/v2/rubygems/rubocop/versions/{version}.json"

# The lock's sections, in the order Bundler writes them, as this repository's
# lock has them. Any other section (PATH, GIT, RUBY VERSION, ...) is refused.
SECTIONS = ("GEM", "PLATFORMS", "DEPENDENCIES", "CHECKSUMS", "BUNDLED WITH")

VERSION = re.compile(r"\d+(?:\.\d+)*")
OPERATORS = ("=", "!=", ">=", "<=", ">", "<", "~>")


# Returns the body at a URL; refresh_tools.py passes its retrying download.
Fetch = Callable[[str], bytes]


class LockError(Exception):
    """The lock cannot be moved without Bundler; the message says why."""


def _refuse(reason: str) -> LockError:
    return LockError(f"{reason}; {RELOCK}")


def _version(text: str) -> tuple[int, ...]:
    # Only all-numeric versions are modeled: a prerelease or a platform
    # suffix orders by rules this does not implement.
    if not VERSION.fullmatch(text):
        raise _refuse(f"version {text!r} is not a plain numeric version")
    return tuple(int(part) for part in text.split("."))


def _compare(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    width = max(len(a), len(b))
    a = a + (0,) * (width - len(a))
    b = b + (0,) * (width - len(b))
    return (a > b) - (a < b)


def satisfies(version: str, requirement: str) -> bool:
    """Whether `version` meets one RubyGems requirement such as `~> 1.7`."""
    match = re.fullmatch(r"(~>|>=|<=|!=|=|>|<) (\S+)", requirement)
    if not match:
        raise _refuse(f"requirement {requirement!r} is not a form this reads")
    operator, bound_text = match.groups()
    have, bound = _version(version), _version(bound_text)
    order = _compare(have, bound)
    if operator == "~>":
        # RubyGems' pessimistic bound: at least the version, and below the
        # next release of its second-to-last segment (~> 3.17.0.2 is
        # >= 3.17.0.2, < 3.17.1).
        prefix = bound[:-1] if len(bound) > 1 else bound
        ceiling = prefix[:-1] + (prefix[-1] + 1,)
        return order >= 0 and _compare(have, ceiling) < 0
    return {
        "=": order == 0,
        "!=": order != 0,
        ">=": order >= 0,
        "<=": order <= 0,
        ">": order > 0,
        "<": order < 0,
    }[operator]


def _requirements(text: str) -> list[str]:
    parts = [part.strip() for part in text.split(",")]
    if not all(parts):
        raise _refuse(f"requirements {text!r} are not a list this reads")
    return parts


def _to_lock(requirements: list[str]) -> str:
    # Bundler's own order for a dependency's requirements in a lock
    # (Gem::Dependency#to_lock): sorted, then reversed.
    return ", ".join(sorted(requirements, reverse=True))


@dataclass(frozen=True)
class Release:
    """What the lock needs from one RuboCop release's rubygems.org record."""

    version: str
    sha256: str
    ruby: list[str]
    dependencies: dict[str, list[str]]


def release(record: bytes, version: str) -> Release:
    """The parts of a rubygems.org version record the lock is written from."""
    try:
        data = json.loads(record)
        name, number = data["name"], data["number"]
        platform, prerelease, yanked = (
            data["platform"],
            data["prerelease"],
            data["yanked"],
        )
        sha256, ruby, rubygems = (
            data["sha"],
            data["ruby_version"],
            data["rubygems_version"],
        )
        runtime = data["dependencies"]["runtime"]
        dependencies = {
            entry["name"]: _requirements(entry["requirements"]) for entry in runtime
        }
    except (ValueError, KeyError, TypeError) as e:
        raise _refuse(
            f"the rubygems.org record for {version} is unreadable: {e!r}"
        ) from e
    if (name, number) != ("rubocop", version):
        raise _refuse(f"the record is for {name} {number}, not rubocop {version}")
    if platform != "ruby" or prerelease or yanked:
        raise _refuse(
            f"rubocop {version} is platform {platform!r}, prerelease {prerelease},"
            f" yanked {yanked}; only a released pure-Ruby gem is modeled"
        )
    if not re.fullmatch(r"[0-9a-f]{64}", str(sha256)):
        raise _refuse(f"rubocop {version}'s sha {sha256!r} is not a sha256")
    if rubygems != ">= 0":
        raise _refuse(f"rubocop {version} requires RubyGems {rubygems}")
    if len(dependencies) != len(runtime):
        raise _refuse(f"rubocop {version} names a dependency twice")
    return Release(version, sha256, _requirements(ruby), dependencies)


def pinned(gemfile: str) -> str:
    """The RuboCop version the Gemfile pins, read strictly."""
    gems = []
    for line in gemfile.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == 'source "https://rubygems.org"':
            continue
        gem = re.fullmatch(r'gem "([^"]+)", "([^"]+)"', stripped)
        if not gem:
            raise _refuse(f"the Gemfile line {stripped!r} is not a form this reads")
        gems.append(gem.groups())
    if len(gems) != 1 or gems[0][0] != "rubocop":
        raise _refuse(f"the Gemfile pins {gems}, not rubocop alone")
    version = gems[0][1]
    _version(version)
    return version


def _sections(lock: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in lock.split("\n"):
        if line and not line.startswith(" "):
            if line in sections or line not in SECTIONS:
                raise _refuse(f"the lock's section {line!r} is not one this reads")
            current = sections[line] = []
        elif current is None:
            if line:
                raise _refuse("the lock does not start with a section")
        else:
            current.append(line)
    if tuple(sections) != SECTIONS:
        raise _refuse(f"the lock's sections are {list(sections)}, not {SECTIONS}")
    return sections


def _specs(body: list[str]) -> tuple[list[str], dict[str, str], dict[str, list[str]]]:
    """GEM's header lines, each gem's locked version, and rubocop's dependencies."""
    header: list[str] = []
    versions: dict[str, str] = {}
    rubocop: dict[str, list[str]] = {}
    current = None
    for line in body:
        spec = re.fullmatch(r" {4}(\S+) \(([^)]+)\)", line)
        dependency = re.fullmatch(r" {6}(\S+)(?: \(([^)]+)\))?", line)
        if spec:
            current, version = spec.groups()
            if current in versions:
                raise _refuse(f"the lock names {current} more than once")
            _version(version)
            versions[current] = version
        elif dependency and current is not None:
            if current == "rubocop":
                name, requirements = dependency.groups()
                rubocop[name] = _requirements(requirements) if requirements else []
        elif current is None and line.startswith("  ") and not line.startswith("    "):
            header.append(line)
        elif line:
            raise _refuse(f"the lock's GEM line {line!r} is not a form this reads")
    if header != ["  remote: https://rubygems.org/", "  specs:"]:
        raise _refuse(f"the lock's GEM header is {header}")
    if "rubocop" not in versions:
        raise _refuse("the lock has no rubocop spec")
    return header, versions, rubocop


def rewrite(gemfile: str, lock: str, ruby: str, fetch: Fetch) -> str:
    """`lock` moved to the RuboCop the Gemfile pins, for Ruby `ruby`.

    `fetch` returns the body at a URL; it is called only when the lock names
    another release than the Gemfile.
    """
    version = pinned(gemfile)
    sections = _sections(lock)
    _, versions, old_dependencies = _specs(sections["GEM"])
    old = versions["rubocop"]
    if old == version:
        return lock
    new = release(fetch(RECORD.format(version=version)), version)
    if not all(satisfies(ruby, requirement) for requirement in new.ruby):
        raise _refuse(f"rubocop {version} requires Ruby {new.ruby}, not {ruby}")
    if set(new.dependencies) != set(old_dependencies):
        raise _refuse(
            f"rubocop {version} depends on {sorted(new.dependencies)},"
            f" where {old} depended on {sorted(old_dependencies)}"
        )
    for name, requirements in new.dependencies.items():
        locked = versions.get(name)
        if locked is None:
            raise _refuse(f"rubocop {version} needs {name}, which the lock lacks")
        unmet = [r for r in requirements if not satisfies(locked, r)]
        if unmet:
            raise _refuse(
                f"rubocop {version} needs {name} {', '.join(requirements)},"
                f" and the lock has {name} {locked}"
            )

    spec_lines = [f"    rubocop ({version})"] + sorted(
        f"      {name} ({_to_lock(requirements)})"
        for name, requirements in new.dependencies.items()
    )
    gem: list[str] = []
    skipping = False
    for line in sections["GEM"]:
        if re.fullmatch(r" {4}\S+ \([^)]+\)", line):
            skipping = line == f"    rubocop ({old})"
            if skipping:
                gem.extend(spec_lines)
                continue
        elif skipping and line.startswith("      "):
            continue
        gem.append(line)

    def replace_one(
        body: list[str], old_line: str, new_line: str, section: str
    ) -> list[str]:
        if body.count(old_line) != 1:
            raise _refuse(
                f"the lock's {section} does not name {old_line.strip()!r} once"
            )
        return [new_line if line == old_line else line for line in body]

    dependencies = replace_one(
        sections["DEPENDENCIES"],
        f"  rubocop (= {old})",
        f"  rubocop (= {version})",
        "DEPENDENCIES",
    )
    checksum_old = [
        line for line in sections["CHECKSUMS"] if line.startswith(f"  rubocop ({old}) ")
    ]
    if len(checksum_old) != 1:
        raise _refuse("the lock's CHECKSUMS does not name rubocop once")
    checksums = replace_one(
        sections["CHECKSUMS"],
        checksum_old[0],
        f"  rubocop ({version}) sha256={new.sha256}",
        "CHECKSUMS",
    )

    rewritten = {
        **sections,
        "GEM": gem,
        "DEPENDENCIES": dependencies,
        "CHECKSUMS": checksums,
    }
    return "\n".join(line for name in SECTIONS for line in [name, *rewritten[name]])
