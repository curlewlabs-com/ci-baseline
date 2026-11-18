// Print every rule the configuration turns on, with its options, for each kind
// of file and each layer, one sorted line per rule. rules.txt is this output:
// a toolchain bump or an edit that changes what is checked shows up as a diff
// of that file, which CI compares.
//
//   node <install dir>/print-rules.mjs > lint/rules.txt
//
// Each layer is built from config/rules.mjs directly, the function
// eslint.config.mjs calls with a run's plan, rather than by loading that file
// twice: eslint caches a configuration module once imported, so a second
// layer read through it would repeat the first.

import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ESLint } from "eslint";
import { baselineConfig } from "./config/rules.mjs";

const KINDS = {
  "source.ts": "src/source.ts",
  "source.js": "src/source.js",
  "source.cjs": "src/source.cjs",
  "test.ts": "test/source.test.ts",
  "test.js": "test/source.test.js",
};

const dir = mkdtempSync(join(tmpdir(), "ci-baseline-rules-"));
const lines = [];
for (const layer of ["baseline", "typed"]) {
  const eslint = new ESLint({
    cwd: dir,
    overrideConfigFile: true,
    overrideConfig: baselineConfig({
      typed: layer === "typed" ? { tsconfigRootDir: dir, projects: [] } : false,
    }),
  });
  for (const [kind, path] of Object.entries(KINDS)) {
    const config = await eslint.calculateConfigForFile(join(dir, path));
    for (const [rule, setting] of Object.entries(config.rules ?? {})) {
      const [severity, ...options] = Array.isArray(setting)
        ? setting
        : [setting];
      if (severity === 0 || severity === "off") continue;
      const shown = options.length ? ` ${JSON.stringify(options)}` : "";
      lines.push(`${layer} ${kind} ${rule}${shown}`);
    }
  }
}
process.stdout.write(lines.sort().join("\n") + "\n");
