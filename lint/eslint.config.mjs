// The configuration ci-baseline points eslint at, built from the plan
// lib/eslint_plan.py writes for one run: which layer, the tsconfig projects a
// repository states, and the JavaScript files found by their shebang alone.
// The rules themselves are config/rules.mjs's.

import { readFileSync } from "node:fs";
import { baselineConfig } from "./config/rules.mjs";

const planPath = process.env.CI_BASELINE_ESLINT_PLAN;
if (!planPath) {
  throw new Error("ci-baseline: CI_BASELINE_ESLINT_PLAN names no plan");
}
const plan = JSON.parse(readFileSync(planPath, "utf8"));

export default baselineConfig({
  extraFiles: plan.extraFiles,
  typed: plan.typed
    ? { tsconfigRootDir: plan.root, projects: plan.projects }
    : false,
  reportUnusedDisables: plan.reportUnusedDisables,
});
