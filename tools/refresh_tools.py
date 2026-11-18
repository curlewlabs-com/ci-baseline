"""Finish a tool bump in CI: rewrite what follows from the versions.

A bump moves a `*_VERSION` line in lib/install-tools.sh. The sha256 of each
asset the installer fetches follows from the version and cannot be typed from
it, so this downloads each asset for the versions the file now names and
writes its digest beside it. A RuboCop bump moves lib/rubocop/Gemfile, and
rubocop_lock.py moves lib/rubocop/Gemfile.lock to match.

    python3 tools/refresh_tools.py

It fails, changing nothing, when the script does not name exactly one of each
line it reads or rewrites, when an asset cannot be downloaded, or when the
lock cannot be moved without Bundler (rubocop_lock.py says when).
"""

from __future__ import annotations

import hashlib
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import rubocop_lock

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "lib/install-tools.sh"
GEMFILE = ROOT / "lib/rubocop/Gemfile"
LOCK = ROOT / "lib/rubocop/Gemfile.lock"

RELEASES = "https://github.com/{repo}/releases/download/{{version}}/"

# Each digest line the installer checks: the version line it follows, and the
# asset's URL for that version, with {version} the line's value and {bare} the
# value without a leading "v".
ASSETS = {
    "ACTIONLINT_SHA256_X86_64": (
        "ACTIONLINT_VERSION",
        RELEASES.format(repo="rhysd/actionlint")
        + "actionlint_{bare}_linux_amd64.tar.gz",
    ),
    "ACTIONLINT_SHA256_AARCH64": (
        "ACTIONLINT_VERSION",
        RELEASES.format(repo="rhysd/actionlint")
        + "actionlint_{bare}_linux_arm64.tar.gz",
    ),
    "SHELLCHECK_SHA256_X86_64": (
        "SHELLCHECK_VERSION",
        RELEASES.format(repo="koalaman/shellcheck")
        + "shellcheck-{version}.linux.x86_64.tar.xz",
    ),
    "SHELLCHECK_SHA256_AARCH64": (
        "SHELLCHECK_VERSION",
        RELEASES.format(repo="koalaman/shellcheck")
        + "shellcheck-{version}.linux.aarch64.tar.xz",
    ),
    "ZIZMOR_SHA256_X86_64": (
        "ZIZMOR_VERSION",
        RELEASES.format(repo="zizmorcore/zizmor")
        + "zizmor-x86_64-unknown-linux-gnu.tar.gz",
    ),
    "ZIZMOR_SHA256_AARCH64": (
        "ZIZMOR_VERSION",
        RELEASES.format(repo="zizmorcore/zizmor")
        + "zizmor-aarch64-unknown-linux-gnu.tar.gz",
    ),
    "RUFF_SHA256_X86_64": (
        "RUFF_VERSION",
        RELEASES.format(repo="astral-sh/ruff") + "ruff-x86_64-unknown-linux-gnu.tar.gz",
    ),
    "RUFF_SHA256_AARCH64": (
        "RUFF_VERSION",
        RELEASES.format(repo="astral-sh/ruff")
        + "ruff-aarch64-unknown-linux-gnu.tar.gz",
    ),
    "SHFMT_SHA256_X86_64": (
        "SHFMT_VERSION",
        RELEASES.format(repo="mvdan/sh") + "shfmt_{version}_linux_amd64",
    ),
    "SHFMT_SHA256_AARCH64": (
        "SHFMT_VERSION",
        RELEASES.format(repo="mvdan/sh") + "shfmt_{version}_linux_arm64",
    ),
    "BUILDIFIER_SHA256_X86_64": (
        "BUILDIFIER_VERSION",
        RELEASES.format(repo="bazel-contrib/buildtools") + "buildifier-linux-amd64",
    ),
    "BUILDIFIER_SHA256_AARCH64": (
        "BUILDIFIER_VERSION",
        RELEASES.format(repo="bazel-contrib/buildtools") + "buildifier-linux-arm64",
    ),
    "PRETTIER_SHA256": (
        "PRETTIER_VERSION",
        "https://registry.npmjs.org/prettier/-/prettier-{version}.tgz",
    ),
    "PYRIGHT_SHA256": (
        "PYRIGHT_VERSION",
        "https://registry.npmjs.org/pyright/-/pyright-{version}.tgz",
    ),
}

ATTEMPTS = 3


class RefreshError(Exception):
    """The installer is not in a state this can finish a bump from."""


def _one(text: str, name: str) -> re.Match[str]:
    matches = list(re.finditer(rf"^{name}=(?P<value>\S+)$", text, re.MULTILINE))
    if len(matches) != 1:
        raise RefreshError(
            f"{INSTALLER.name} names {name} {len(matches)} times, not once"
        )
    return matches[0]


def _download(url: str) -> bytes:
    # A refused connection, a rate limit or a server error is retried; a 404
    # is not, since it means the asset name or version is wrong and retrying
    # cannot fix it.
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                body: bytes = response.read()
                return body
        except urllib.error.HTTPError as e:
            if (e.code < 500 and e.code != 429) or attempt == ATTEMPTS:
                raise RefreshError(f"could not download {url}: {e!r}") from e
        except OSError as e:
            if attempt == ATTEMPTS:
                raise RefreshError(f"could not download {url}: {e!r}") from e
        print(f"refresh_tools: retrying {url} ({attempt}/{ATTEMPTS})", file=sys.stderr)
        time.sleep(2 * attempt)
    raise AssertionError("unreachable")


def refresh(text: str) -> str:
    """`text` with each digest line set to its asset's sha256."""
    digests: dict[str, str] = {}
    for name, (version_line, template) in ASSETS.items():
        _one(text, name)
        version = _one(text, version_line)["value"]
        url = template.format(version=version, bare=version.removeprefix("v"))
        digests[name] = hashlib.sha256(_download(url)).hexdigest()
    for name, sha256 in digests.items():
        match = _one(text, name)
        text = text[: match.start("value")] + sha256 + text[match.end("value") :]
    return text


def image_ruby(text: str) -> str:
    """The Ruby version of the image the installer pins, `4.0.9` of
    `RUBY_VERSION=4.0.9-trixie@sha256:...`."""
    value = _one(text, "RUBY_VERSION")["value"]
    match = re.match(r"(\d+\.\d+\.\d+)-", value)
    if not match:
        raise RefreshError(f"RUBY_VERSION {value} does not start with a version")
    return match.group(1)


def main() -> int:
    try:
        text = INSTALLER.read_text()
        updated = refresh(text)
        lock = LOCK.read_text()
        relocked = rubocop_lock.rewrite(
            GEMFILE.read_text(), lock, image_ruby(updated), _download
        )
    except (RefreshError, rubocop_lock.LockError) as e:
        print(f"refresh_tools: {e}", file=sys.stderr)
        return 1
    if updated != text:
        INSTALLER.write_text(updated)
        print(f"refresh_tools: rewrote the digests in {INSTALLER.relative_to(ROOT)}")
    else:
        print("refresh_tools: every digest already matches its asset")
    if relocked != lock:
        LOCK.write_text(relocked)
        print(f"refresh_tools: moved {LOCK.relative_to(ROOT)} to the pinned RuboCop")
    else:
        print("refresh_tools: the RuboCop lock already matches the Gemfile")
    return 0


if __name__ == "__main__":
    sys.exit(main())
