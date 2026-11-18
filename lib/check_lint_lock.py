"""Refuse an eslint toolchain lockfile npm would install anything unverified from.

    python3 -I lib/check_lint_lock.py lint/package-lock.json

`npm ci` checks each tarball against the `integrity` its lockfile entry
records, so the lockfile is what the install trusts. This passes it only when
every installed package comes from the npm registry by its tarball URL with a
sha512 digest beside it, and when the root's dependencies are the exact
versions lint/package.json names, which are also the peers
lint/config/package.json, the configuration a repository installs itself,
asks for. A git or file dependency, a tarball from
another host, an entry with no digest or a weaker one, or a range in the
manifest is reported, and the run fails before anything is fetched.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REGISTRY = "https://registry.npmjs.org/"
EXACT = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")


def problems(
    lock: dict[str, Any], manifest: dict[str, Any], config: dict[str, Any]
) -> list[str]:
    found: list[str] = []
    if lock.get("lockfileVersion") != 3:
        found.append("lockfileVersion is not 3")
    packages = lock.get("packages")
    if not isinstance(packages, dict) or "" not in packages:
        return [*found, "no packages table with a root entry"]
    wanted = manifest.get("dependencies", {})
    for name, version in wanted.items():
        if not isinstance(version, str) or not EXACT.fullmatch(version):
            found.append(
                f"{name}: {version!r} in package.json is not one exact version"
            )
    peers = config.get("peerDependencies", {})
    if peers != {name: v for name, v in wanted.items() if name != "typescript"}:
        found.append(
            "lint/config/package.json's peers are not package.json's dependencies"
            " (all but typescript)"
        )
    if packages[""].get("dependencies") != wanted:
        found.append("the lockfile's root dependencies are not package.json's")
    for path, entry in packages.items():
        if path == "":
            continue
        resolved = entry.get("resolved")
        integrity = entry.get("integrity")
        if not isinstance(resolved, str) or not resolved.startswith(REGISTRY):
            found.append(f"{path}: resolved from {resolved!r}, not the npm registry")
        if not isinstance(integrity, str) or not integrity.startswith("sha512-"):
            found.append(f"{path}: no sha512 integrity")
        if entry.get("link"):
            found.append(f"{path}: a link, not a package")
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_lint_lock.py <package-lock.json>", file=sys.stderr)
        return 2
    lock_path = Path(argv[1])
    lock = json.loads(lock_path.read_text())
    manifest = json.loads((lock_path.parent / "package.json").read_text())
    config = json.loads((lock_path.parent / "config" / "package.json").read_text())
    found = problems(lock, manifest, config)
    for line in found:
        print(f"ci-baseline: {lock_path}: {line}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
