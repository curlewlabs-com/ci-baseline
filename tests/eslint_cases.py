"""The eslint check's cases: each one is a small repository the check is run on,
and what it must report.

    python3 -I tests/eslint_cases.py <install dir>

Every exemption the configuration makes comes as a pair: what it is meant to
allow passes, and the nearest thing it must not allow is still reported. A case
that must fail names the rule or the refusal it fails on, so it cannot pass by
failing for another reason, and each such case has a twin without its cause
that must pass. The toolchain's own refusals are cases too, run on a copy of
this tree.

The install directory is where lib/install-lint.sh puts the toolchain once for
every lint case; the install cases make their own.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Lint:
    name: str
    files: Mapping[str, str]
    # Rule ids or messages the output must hold; empty means the run passes.
    reports: Sequence[str] = ()
    env: Mapping[str, str] = field(default_factory=dict)
    executable: Sequence[str] = ()
    # A directory in the case's repository put first on PATH.
    path_first: str | None = None


def pair(
    name: str,
    allowed: Mapping[str, str],
    refused: Mapping[str, str],
    reports: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    executable: Sequence[str] = (),
    path_first: str | None = None,
) -> list[Lint]:
    """The allowed case, which must pass, and the refused one, which must fail
    on each of `reports`. Both run with the same environment."""

    def case(label: str, files: Mapping[str, str], want: Sequence[str]) -> Lint:
        return Lint(
            f"{name}: {label}", files, want, dict(env or {}), executable, path_first
        )

    return [case("allowed", allowed, ()), case("refused", refused, reports)]


CASES: list[Lint] = [
    *pair(
        "a finding in JavaScript",
        {"case.mjs": "export const value = 1;\n"},
        {"case.mjs": "export const value = undefinedName;\n"},
        ["no-undef"],
    ),
    *pair(
        "a finding in TypeScript",
        {"case.ts": "export const size = (v: string): number => v.length;\n"},
        {"case.ts": "export const size = (v: string | null): number => v!.length;\n"},
        ["@typescript-eslint/no-non-null-assertion"],
    ),
    *pair(
        "a script found by its shebang",
        {"bin/tool": "#!/usr/bin/env node\nconsole.log(1);\n"},
        {"bin/tool": "#!/usr/bin/env node\nconsole.log(undefinedName);\n"},
        ["no-undef"],
    ),
    *pair(
        "an underscore marks an unused binding",
        {
            "case.ts": (
                "export function f(_unused: number): number {\n"
                "  const { a: _dropped, ...rest } = { a: 1, b: 2 };\n"
                "  const [_first, second] = [1, 2];\n"
                "  try {\n"
                "    return rest.b + second;\n"
                "  } catch (_error) {\n"
                "    return 0;\n"
                "  }\n"
                "}\n"
            )
        },
        {"case.ts": "export function f(unused: number): number {\n  return 1;\n}\n"},
        ["@typescript-eslint/no-unused-vars"],
    ),
    *pair(
        "require in CommonJS",
        {
            "case.cjs": 'const path = require("node:path");\nmodule.exports = path.sep;\n'
        },
        {
            "case.js": 'const path = require("node:path");\nexport const sep = path.sep;\n'
        },
        ["@typescript-eslint/no-require-imports"],
    ),
    *pair(
        "JavaScript is parsed as JavaScript",
        {
            "bin/tool": "#!/usr/bin/env node\nconsole.log(1);\n",
            "src/view.jsx": "export const view = <div>hello</div>;\n",
            "src/module.js": 'import path from "node:path";\nexport const sep = path.sep;\n',
        },
        {
            "bin/tool": "#!/usr/bin/env node\nconsole.log(1 as number);\n",
            "src/view.jsx": "export const view = <div>hello</div>;\n",
        },
        ["bin/tool", "Parsing error"],
    ),
    *pair(
        "a script with an extension and a shebang",
        {
            "bin/tool.mjs": "#!/usr/bin/env node\nconsole.log(1);\n",
            "bin/tool.ts": "#!/usr/bin/env node\nconsole.log(1);\n",
        },
        {
            "bin/tool.mjs": "#!/usr/bin/env node\nconsole.log(undefinedName);\n",
            "bin/tool.ts": "#!/usr/bin/env node\nconsole.log(1);\n",
        },
        ["no-undef", "bin/tool.mjs"],
    ),
    *pair(
        "a declaration file is read as one",
        {
            "src/env.d.ts": (
                "declare namespace Runtime {\n  interface Env {\n    store: string;\n  }\n}\n"
            )
        },
        {
            "src/env.ts": (
                "declare namespace Runtime {\n  interface Env {\n    store: string;\n  }\n}\n"
            )
        },
        ["@typescript-eslint/no-namespace"],
    ),
    *pair(
        "CommonJS's globals only where a file may be CommonJS",
        {
            "case.cjs": "module.exports = __dirname;\n",
            "case.js": "module.exports = __filename;\n",
        },
        {"case.mjs": "export const directory = __dirname;\n"},
        ["no-undef", "'__dirname' is not defined"],
    ),
    *pair(
        "CommonJS is parsed as CommonJS",
        {
            "case.cjs": (
                'const path = require("node:path");\n'
                "if (!path.sep) {\n"
                "  return;\n"
                "}\n"
                "module.exports = path.sep;\n"
            )
        },
        {"case.cjs": 'import path from "node:path";\nmodule.exports = path.sep;\n'},
        ["'import' and 'export' may appear only with 'sourceType: module'"],
    ),
    *pair(
        "a line disable says why",
        {
            "case.mjs": (
                "// eslint-disable-next-line no-undef -- a global the page provides\n"
                "export const value = undefinedName;\n"
            )
        },
        {
            "case.mjs": (
                "// eslint-disable-next-line no-undef\n"
                "export const value = undefinedName;\n"
            )
        },
        ["eslint-comments/require-description"],
    ),
    *pair(
        "a global comment, not a configuration comment",
        {
            "case.mjs": "/* global pageValue -- the page provides it */\nexport const value = pageValue;\n"
        },
        {"case.mjs": '/* eslint no-undef: "off" */\nexport const value = pageValue;\n'},
        ["eslint-comments/no-use"],
    ),
    *pair(
        "a disable names its rule",
        {
            "case.mjs": (
                "/* eslint-disable-next-line no-undef -- read from the page */\n"
                "export const value = pageValue;\n"
            )
        },
        {"case.mjs": "/* eslint-disable */\nexport const value = pageValue;\n"},
        ["eslint-comments/no-unlimited-disable"],
    ),
    *pair(
        "a disable that suppresses nothing",
        {
            "case.mjs": (
                "// eslint-disable-next-line no-undef -- a global the page provides\n"
                "export const value = undefinedName;\n"
            )
        },
        {
            "case.mjs": (
                "// eslint-disable-next-line no-undef -- a global the page provides\n"
                "export const value = 1;\n"
            )
        },
        ["Unused eslint-disable directive"],
    ),
    *pair(
        "a ts-expect-error says why",
        {
            "case.ts": (
                "// @ts-expect-error the fixture is a string on purpose\n"
                "export const n: number = 'one';\n"
            )
        },
        {"case.ts": "// @ts-expect-error nope\nexport const n: number = 'one';\n"},
        ["@typescript-eslint/ban-ts-comment"],
    ),
    *pair(
        "eqeqeq allows a null comparison",
        {"case.mjs": "export const missing = (x) => x == null;\n"},
        {"case.mjs": "export const one = (x) => x == 1;\n"},
        ["eqeqeq"],
    ),
    *pair(
        "a non-null assertion in a test",
        {
            "test/case.test.ts": "export const size = (v: string | null): number => v!.length;\n"
        },
        {
            "src/case.ts": "export const size = (v: string | null): number => v!.length;\n"
        },
        ["@typescript-eslint/no-non-null-assertion"],
    ),
    *pair(
        "a helper named test-* is a test, a name ending in test is not",
        {
            "src/test-helper.ts": "export const size = (v: string | null): number => v!.length;\n"
        },
        {
            "src/latest.ts": "export const size = (v: string | null): number => v!.length;\n"
        },
        ["@typescript-eslint/no-non-null-assertion"],
    ),
    *pair(
        "console in source, not in a test",
        {"src/report.mjs": "console.log('report');\n"},
        {"test/report.test.mjs": "console.log('debug');\n"},
        ["no-console"],
    ),
    *pair(
        "an ignored path, with a reason, and only that path",
        {
            ".ci-baseline/eslint.json": json.dumps(
                {"ignore": [{"path": "fixture/**", "reason": "read as data"}]}
            ),
            "fixture/data.mjs": "export const value = undefinedName;\n",
        },
        {
            ".ci-baseline/eslint.json": json.dumps(
                {"ignore": [{"path": "fixture/**", "reason": "read as data"}]}
            ),
            "fixture/data.mjs": "export const value = undefinedName;\n",
            "src/near.mjs": "export const value = undefinedName;\n",
        },
        ["no-undef", "src/near.mjs"],
    ),
    *pair(
        "an ignore entry needs a reason",
        {
            ".ci-baseline/eslint.json": json.dumps(
                {"ignore": [{"path": "fixture/**", "reason": "read as data"}]}
            ),
            "fixture/data.mjs": "export const value = 1;\n",
        },
        {
            ".ci-baseline/eslint.json": json.dumps(
                {"ignore": [{"path": "fixture/**", "reason": ""}]}
            ),
            "fixture/data.mjs": "export const value = 1;\n",
        },
        ["each ignore entry is a path and a reason"],
    ),
    *pair(
        "an ignore entry matches a tracked file",
        {
            ".ci-baseline/eslint.json": json.dumps(
                {"ignore": [{"path": "fixture/**", "reason": "read as data"}]}
            ),
            "fixture/data.mjs": "export const value = 1;\n",
        },
        {
            ".ci-baseline/eslint.json": json.dumps(
                {"ignore": [{"path": "gone/**", "reason": "removed"}]}
            ),
            "fixture/data.mjs": "export const value = 1;\n",
        },
        ["matches no tracked JavaScript or TypeScript file"],
    ),
    *pair(
        "an ignore entry outlives no file, even the last one",
        {"README.md": "No JavaScript here.\n"},
        {
            "README.md": "No JavaScript here.\n",
            ".ci-baseline/eslint.json": json.dumps(
                {"ignore": [{"path": "fixture/**", "reason": "read as data"}]}
            ),
        },
        ["matches no tracked JavaScript or TypeScript file"],
    ),
    *pair(
        "the statement states nothing else",
        {
            ".ci-baseline/eslint.json": json.dumps({"ignore": []}),
            "case.mjs": "export {};\n",
        },
        {
            ".ci-baseline/eslint.json": json.dumps({"rules": {"no-undef": "off"}}),
            "case.mjs": "export {};\n",
        },
        ["it may state only ignore"],
    ),
    *pair(
        "nothing the checkout or the job carries turns a rule off",
        {"case.mjs": "export const value = 1;\n"},
        {
            "case.mjs": "export const value = undefinedName;\n",
            "eslint.config.mjs": 'export default [{ rules: { "no-undef": "off" } }];\n',
            ".eslintrc.json": json.dumps({"root": True, "rules": {"no-undef": "off"}}),
            ".eslintignore": "case.mjs\n",
            "eslint-suppressions.json": json.dumps(
                {"case.mjs": {"no-undef": {"count": 1}}}
            ),
        },
        ["no-undef"],
        env={
            "ESLINT_USE_FLAT_CONFIG": "false",
            "ESLINT_FLAGS": "unstable_config_lookup_from_file",
            "NODE_OPTIONS": "--require=./preload.cjs",
            "NODE_PATH": ".",
            "TSESTREE_SINGLE_RUN": "true",
        },
    ),
    *pair(
        "a node from the checkout",
        {"case.mjs": "export const value = 1;\n"},
        {
            "case.mjs": "export const value = 1;\n",
            "shim/node": "#!/bin/sh\necho the checkout's node ran\nexit 1\n",
        },
        ["resolves to", "inside the checkout being checked"],
        executable=["shim/node"],
        path_first="shim",
    ),
]


@dataclass
class Exported:
    """A repository that runs eslint from its own install with the configuration
    the release tarball carries, as `eslint .` over the whole tree."""

    name: str
    files: Mapping[str, str]
    reports: Sequence[str] = ()


EXPORTED: list[Exported] = [
    Exported(
        "the exported configuration lints a tree of several languages: allowed",
        {
            "tests/helper_test.py": "def helper():\n    return 1\n",
            "tests/case.test.mjs": "export const value = 1;\n",
        },
    ),
    Exported(
        "the exported configuration lints a tree of several languages: refused",
        {
            "tests/helper_test.py": "def helper():\n    return 1\n",
            "tests/case.test.mjs": "console.log('debug');\n",
        },
        ["no-console", "tests/case.test.mjs"],
    ),
]


def exported_case(case: Exported, install: Path, scratch: Path) -> str | None:
    repo = scratch / "repo"
    for name, text in case.files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
    (repo / "eslint.config.mjs").write_text(
        f"import {{ baselineConfig }} from {json.dumps(str(install / 'config/rules.mjs'))};\n"
        "export default baselineConfig();\n"
    )
    status, out = run(
        ["node", str(install / "node_modules/eslint/bin/eslint.js"), "."],
        repo,
        os.environ,
    )
    if not case.reports:
        return None if status == 0 else f"expected a pass, got {status}:\n{out}"
    if status == 0:
        return f"expected a failure on {', '.join(case.reports)}, got a pass:\n{out}"
    missing = [want for want in case.reports if want not in out]
    if missing or "Parsing error" in out:
        return f"failed, but not on {', '.join(missing) or 'only them'}:\n{out}"
    return None


@dataclass
class Install:
    name: str
    # Edits a copy of this tree's lint/package-lock.json.
    lock_edit: str | None = None
    env: Mapping[str, str] = field(default_factory=dict)
    foreign_dest: bool = False
    reports: Sequence[str] = ()


INSTALLS: list[Install] = [
    Install(
        "npm and node pointed elsewhere change nothing",
        env={
            "npm_config_registry": "https://registry.example.com/",
            "NPM_CONFIG_DRY_RUN": "true",
            "npm_config_ignore_scripts": "false",
            "NODE_OPTIONS": "--require=/nonexistent/preload.cjs",
        },
    ),
    Install(
        "a package from another host",
        lock_edit="host",
        reports=["resolved from", "not the npm registry"],
    ),
    Install(
        "a package with no digest", lock_edit="digest", reports=["no sha512 integrity"]
    ),
    Install(
        "a directory the install did not create",
        foreign_dest=True,
        reports=["is not an eslint install of ours"],
    ),
]


# A step that runs longer than this is reported as a failure of its case
# rather than left to stall the job: a protection that stopped refusing a
# checkout's own node, say, lets that node run.
STEP_SECONDS = 300


def run(cmd: Sequence[str], cwd: Path, env: Mapping[str, str]) -> tuple[int, str]:
    try:
        done = subprocess.run(
            cmd,
            cwd=cwd,
            env=dict(env),
            capture_output=True,
            text=True,
            check=False,
            timeout=STEP_SECONDS,
        )
    except subprocess.TimeoutExpired as err:
        return -1, f"ran past {STEP_SECONDS}s: {err}"
    return done.returncode, done.stdout + done.stderr


def git_repo(path: Path, tracked: Mapping[str, str]) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    for name, text in tracked.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    if tracked:
        subprocess.run(["git", "-C", str(path), "add", "--", *tracked], check=True)


def lint_case(case: Lint, install: Path, scratch: Path) -> str | None:
    repo = scratch / "repo"
    git_repo(repo, case.files)
    for name in case.executable:
        if (repo / name).exists():
            (repo / name).chmod(0o755)
    env = {**os.environ, **case.env}
    env["RUNNER_TEMP"] = str(scratch / "runner")
    env["CI_BASELINE_LINT_DIR"] = str(install)
    if case.path_first:
        env["PATH"] = f"{repo / case.path_first}{os.pathsep}{env['PATH']}"
    status, out = run(["sh", str(ROOT / "lib/tracked-files.sh")], repo, env)
    if status == 0:
        status, out = run(["sh", str(ROOT / "lib/eslint.sh")], repo, env)
    if not case.reports:
        return None if status == 0 else f"expected a pass, got {status}:\n{out}"
    if status == 0:
        return f"expected a failure on {', '.join(case.reports)}, got a pass:\n{out}"
    missing = [want for want in case.reports if want not in out]
    if missing:
        return f"failed, but not on {', '.join(missing)}:\n{out}"
    return None


def install_case(case: Install, scratch: Path) -> str | None:
    tree = scratch / "ci-baseline"
    for part in ("lib", "lint"):
        shutil.copytree(ROOT / part, tree / part)
    lock_path = tree / "lint/package-lock.json"
    if case.lock_edit:
        lock = json.loads(lock_path.read_text())
        entry = lock["packages"]["node_modules/eslint"]
        if case.lock_edit == "host":
            entry["resolved"] = entry["resolved"].replace(
                "registry.npmjs.org", "registry.example.com"
            )
        else:
            del entry["integrity"]
        lock_path.write_text(json.dumps(lock))
    dest = scratch / "dest"
    if case.foreign_dest:
        dest.mkdir()
        (dest / "kept").write_text("kept\n")
    env = {**os.environ, **case.env}
    status, out = run(
        ["sh", str(tree / "lib/install-lint.sh"), str(dest)], scratch, env
    )
    if case.foreign_dest and (dest / "kept").read_text() != "kept\n":
        return f"changed a directory it did not create:\n{out}"
    if not case.reports:
        if status != 0 or not (dest / "node_modules/eslint/package.json").is_file():
            return f"expected an install, got {status}:\n{out}"
        return None
    if status == 0:
        return (
            f"expected a refusal on {', '.join(case.reports)}, got an install:\n{out}"
        )
    missing = [want for want in case.reports if want not in out]
    if missing:
        return f"refused, but not on {', '.join(missing)}:\n{out}"
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: eslint_cases.py <install dir>", file=sys.stderr)
        return 2
    install = Path(argv[1]).resolve()
    failed = 0
    for lint in CASES:
        with tempfile.TemporaryDirectory() as scratch:
            problem = lint_case(lint, install, Path(scratch))
        failed += problem is not None
        print(f"{'FAIL' if problem else 'ok  '} {lint.name}")
        if problem:
            print(problem)
    for exported in EXPORTED:
        with tempfile.TemporaryDirectory() as scratch:
            problem = exported_case(exported, install, Path(scratch))
        failed += problem is not None
        print(f"{'FAIL' if problem else 'ok  '} {exported.name}")
        if problem:
            print(problem)
    for inst in INSTALLS:
        with tempfile.TemporaryDirectory() as scratch:
            problem = install_case(inst, Path(scratch))
        failed += problem is not None
        print(f"{'FAIL' if problem else 'ok  '} install: {inst.name}")
        if problem:
            print(problem)
    total = len(CASES) + len(EXPORTED) + len(INSTALLS)
    print(f"{total - failed} of {total} cases hold")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
