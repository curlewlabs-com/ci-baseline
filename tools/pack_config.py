"""Pack lint/config as the tarball a release attaches, with this repository's
licence files in it.

    python3 tools/pack_config.py <output dir>

The licence files live once, at the root; lint/config names them in its
`files` but does not hold copies, so the package is packed from a copy of
lint/config with them beside it. It fails, writing nothing, when the packed
file list is not exactly the one below, so a tarball without its licences
cannot be attached. It prints the tarball's path.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "lint/config"
LICENSES = ("LICENSE-MIT", "LICENSE-APACHE")
PACKED = {"package.json", "rules.mjs", *LICENSES}


def pack(out: Path) -> Path:
    with tempfile.TemporaryDirectory() as scratch:
        staged = Path(scratch) / "config"
        shutil.copytree(CONFIG, staged)
        for name in LICENSES:
            shutil.copyfile(ROOT / name, staged / name)
        built = Path(scratch) / "out"
        built.mkdir()
        listing = subprocess.run(
            [
                "npm",
                "pack",
                "--json",
                "--ignore-scripts",
                "--pack-destination",
                str(built),
            ],
            cwd=staged,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        (result,) = json.loads(listing)
        files = {entry["path"] for entry in result["files"]}
        if files != PACKED:
            raise SystemExit(
                f"pack_config: the tarball would hold {sorted(files)},"
                f" not {sorted(PACKED)}"
            )
        tarball: str = result["filename"]
        shutil.move(built / tarball, out / tarball)
    return out / tarball


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: pack_config.py <output dir>", file=sys.stderr)
        return 2
    print(pack(Path(argv[1]).resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
