"""The configuration tarball a release attaches carries the licences the
package.json names, byte for byte the root's, beside the configuration itself:
a repository that installs it has the terms it is licensed under.

    python3 -I tests/config_tarball.py
"""

from __future__ import annotations

import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "package/LICENSE-MIT": ROOT / "LICENSE-MIT",
    "package/LICENSE-APACHE": ROOT / "LICENSE-APACHE",
    "package/rules.mjs": ROOT / "lint/config/rules.mjs",
    "package/package.json": ROOT / "lint/config/package.json",
}


def main() -> int:
    with tempfile.TemporaryDirectory() as out:
        packed_run = subprocess.run(
            [sys.executable, "-I", str(ROOT / "tools/pack_config.py"), out],
            check=False,
            capture_output=True,
            text=True,
        )
        if packed_run.returncode != 0:
            print(f"packing failed:\n{packed_run.stdout}{packed_run.stderr}")
            return 1
        tarball = packed_run.stdout.strip()
        with tarfile.open(tarball) as packed:
            names = set(packed.getnames())
            if names != set(EXPECTED):
                print(f"the tarball holds {sorted(names)}, not {sorted(EXPECTED)}")
                return 1
            for name, source in EXPECTED.items():
                member = packed.extractfile(name)
                if member is None or member.read() != source.read_bytes():
                    print(f"{name} in the tarball is not {source.relative_to(ROOT)}")
                    return 1
    print(f"{Path(tarball).name} holds the configuration and both licences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
