// The one eslint configuration every repository is linted with: the rules
// that need no type information, so it runs on any checkout with none of the
// repository's dependencies installed. A repository states no rule of its own;
// what it may state is the input below (ignored paths), and a line disable that
// says why.
//
// The rule set is built from presets their projects keep stable between major
// releases (ESLint's `recommended` and typescript-eslint's `recommended`:
// "Rule additions and removals are treated as breaking changes and will only be
// done in major version bumps"), plus rules named here one by one. typescript-eslint's `strict` presets are not stable in
// that sense, so their rules are named rather than extended: a minor or patch
// release cannot add a rule to this set, and rules.txt beside this file is the
// resolved list a change has to rewrite.

import js from "@eslint/js";
import comments from "@eslint-community/eslint-plugin-eslint-comments";
import globals from "globals";
import tseslint from "typescript-eslint";

export const TS = ["**/*.ts", "**/*.mts", "**/*.cts", "**/*.tsx"];
export const JS = ["**/*.js", "**/*.mjs", "**/*.cjs", "**/*.jsx"];

// A test, by where it lives or how it is named. A helper that sits beside the
// code it supports, named for what it is rather than `test-*`, is linted as
// source.
export const TESTS = [
  "**/test/**",
  "**/tests/**",
  "**/*.test.*",
  "**/*_test.*",
  "**/test-*.*",
];

// The files among `globs` that are tests. A test glob alone would also have
// eslint lint a test of another language (`tests/helper_test.py`), since a
// `files` pattern names files to lint as well as where a block applies, so
// each is paired with each of `globs`, which a file must match too.
const testsAmong = (globs) =>
  globs.flatMap((glob) => TESTS.map((test) => [glob, test]));

// Rules that need no type information, beyond the presets.
const BASELINE_RULES = {
  // An underscore marks a binding as deliberately unused, for a parameter a
  // signature fixes, a key a rest pattern drops, or an error a catch ignores.
  "@typescript-eslint/no-unused-vars": [
    "error",
    {
      argsIgnorePattern: "^_",
      varsIgnorePattern: "^_",
      caughtErrorsIgnorePattern: "^_",
      destructuredArrayIgnorePattern: "^_",
    },
  ],
  // `x!` crashes at run time exactly where the type said it could not be
  // null; a check or an early return says what happens instead.
  "@typescript-eslint/no-non-null-assertion": "error",
  "@typescript-eslint/ban-ts-comment": [
    "error",
    { minimumDescriptionLength: 10 },
  ],
  "@typescript-eslint/no-dynamic-delete": "error",
  "@typescript-eslint/no-extraneous-class": "error",
  "@typescript-eslint/no-invalid-void-type": "error",
  "@typescript-eslint/no-non-null-asserted-nullish-coalescing": "error",
  "@typescript-eslint/no-useless-constructor": "error",
  "@typescript-eslint/prefer-literal-enum-member": "error",
  "@typescript-eslint/unified-signatures": "error",
  eqeqeq: ["error", "smart"],
  // Every finding in the repositories measured is a deliberate control
  // character class, a non-ASCII test (`[^\x00-\x7f]`) or a path or log
  // sanitizer (`[\x00-\x1f\x7f]`); the accidental control character the rule
  // looks for appears in none of them. Off whole: the rule has no option that
  // tells a deliberate class from an accidental character, so there is no
  // narrower form to keep.
  "no-control-regex": "off",
  // The configuration lives here, not in a file's comments: only line disables
  // and `global` are allowed, and each says why after `--`.
  "eslint-comments/require-description": "error",
  "eslint-comments/no-unlimited-disable": "error",
  "eslint-comments/no-unused-enable": "error",
  "eslint-comments/no-duplicate-disable": "error",
  "eslint-comments/no-use": [
    "error",
    {
      allow: [
        "eslint-disable-line",
        "eslint-disable-next-line",
        "global",
        "globals",
      ],
    },
  ],
};

// Test code: the strict rules minus those that fight how tests are written,
// plus the one that only makes sense there.
const BASELINE_TEST_RULES = {
  // `x!` after an assertion is how a test narrows.
  "@typescript-eslint/no-non-null-assertion": "off",
  // A test reports through assertions, so a print is a debug aid left behind,
  // and a passing run looks the same with it. Deliberate output disables the
  // rule on its line and says why.
  "no-console": "error",
};

// baselineConfig(options) -> an eslint flat configuration.
//   ignores: gitignore-style patterns the repository states, each with a
//     reason where it states it. Added to eslint's own default ignores.
//   extraFiles: paths of JavaScript files that carry no extension (found by
//     their shebang), linted as JavaScript.
export function baselineConfig({ ignores = [], extraFiles = [] } = {}) {
  const all = [...TS, ...JS, ...extraFiles];
  return [
    { ignores },
    {
      linterOptions: {
        reportUnusedDisableDirectives: "error",
        reportUnusedInlineConfigs: "error",
      },
    },
    { files: all, ...js.configs.recommended },
    // The plugin and the rules apply to every file, and typescript-eslint's
    // parser to TypeScript only: it reads TypeScript syntax anywhere without
    // complaint, so JavaScript keeps ESLint's own parser, which refuses what
    // Node would (a type annotation in a script, an `import` in CommonJS). The
    // preset's own `files` block, which switches off core rules TypeScript's
    // compiler already enforces (no-undef among them), keeps to TypeScript.
    ...tseslint.configs.recommended.map((c) => {
      if (c.files !== undefined) return c;
      return { ...c, files: c.languageOptions ? TS : all };
    }),
    {
      files: ["**/*.jsx"],
      languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } },
    },
    // Node's own globals everywhere, and CommonJS's (`require`, `module`,
    // `__dirname` and the rest) only where a file may be CommonJS: a `.cjs`,
    // and a `.js` or a script found by its shebang, which is either by its
    // package.json, a file eslint is not told about. An `.mjs` is a module.
    {
      files: all,
      plugins: {
        "eslint-comments": comments,
        "@typescript-eslint": tseslint.plugin,
      },
      languageOptions: { globals: globals.nodeBuiltin },
      rules: BASELINE_RULES,
    },
    {
      files: ["**/*.cjs", "**/*.js", ...extraFiles],
      languageOptions: { globals: globals.node },
    },
    // CommonJS has no import but `require`.
    {
      files: ["**/*.cjs"],
      rules: { "@typescript-eslint/no-require-imports": "off" },
    },
    { files: testsAmong(all), rules: BASELINE_TEST_RULES },
  ];
}
