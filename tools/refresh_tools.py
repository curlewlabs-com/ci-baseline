"""Finish a tool bump in CI: rewrite the digests beside the versions.

A bump moves `ACTIONLINT_VERSION`, `SHELLCHECK_VERSION` or `ZIZMOR_VERSION` in
lib/install-tools.sh. The sha256 of each release asset the installer fetches
follows from the version and cannot be typed from it, so this downloads each
asset for the versions the file now names and writes its digest beside it.

    python3 tools/refresh_tools.py

It fails, changing nothing, when the script does not name exactly one of each
line it reads or rewrites, or when an asset cannot be downloaded.
"""

from __future__ import annotations

import hashlib
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "lib/install-tools.sh"

RELEASES = "https://github.com/{repo}/releases/download/{version}/"

# Each digest line the installer checks: the version line it follows, the
# repository that publishes the asset, and the asset's name for that version.
ASSETS = {
    "ACTIONLINT_SHA256_X86_64": (
        "ACTIONLINT_VERSION",
        "rhysd/actionlint",
        "actionlint_{bare}_linux_amd64.tar.gz",
    ),
    "ACTIONLINT_SHA256_AARCH64": (
        "ACTIONLINT_VERSION",
        "rhysd/actionlint",
        "actionlint_{bare}_linux_arm64.tar.gz",
    ),
    "SHELLCHECK_SHA256_X86_64": (
        "SHELLCHECK_VERSION",
        "koalaman/shellcheck",
        "shellcheck-{version}.linux.x86_64.tar.xz",
    ),
    "SHELLCHECK_SHA256_AARCH64": (
        "SHELLCHECK_VERSION",
        "koalaman/shellcheck",
        "shellcheck-{version}.linux.aarch64.tar.xz",
    ),
    "ZIZMOR_SHA256_X86_64": (
        "ZIZMOR_VERSION",
        "zizmorcore/zizmor",
        "zizmor-x86_64-unknown-linux-gnu.tar.gz",
    ),
    "ZIZMOR_SHA256_AARCH64": (
        "ZIZMOR_VERSION",
        "zizmorcore/zizmor",
        "zizmor-aarch64-unknown-linux-gnu.tar.gz",
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
    # A refused connection or a server error is retried; a 404 is not, since
    # it means the asset name or version is wrong and retrying cannot fix it.
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                body: bytes = response.read()
                return body
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == ATTEMPTS:
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
    for name, (version_line, repo, asset) in ASSETS.items():
        _one(text, name)
        version = _one(text, version_line)["value"]
        url = RELEASES.format(repo=repo, version=version) + asset.format(
            version=version, bare=version.removeprefix("v")
        )
        digests[name] = hashlib.sha256(_download(url)).hexdigest()
    for name, sha256 in digests.items():
        match = _one(text, name)
        text = text[: match.start("value")] + sha256 + text[match.end("value") :]
    return text


def main() -> int:
    try:
        text = INSTALLER.read_text()
        updated = refresh(text)
    except RefreshError as e:
        print(f"refresh_tools: {e}", file=sys.stderr)
        return 1
    if updated != text:
        INSTALLER.write_text(updated)
        print(f"refresh_tools: rewrote the digests in {INSTALLER.relative_to(ROOT)}")
    else:
        print("refresh_tools: every digest already matches its asset")
    return 0


if __name__ == "__main__":
    sys.exit(main())
