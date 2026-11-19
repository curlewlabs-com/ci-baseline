// The one eslint configuration every repository is linted with, as two layers:
// `baseline` needs no type information and runs on any checkout, and `typed`
// adds the rules that read types, for a package whose dependencies are
// installed. A repository states no rule of its own; what it may state is the
// input below (ignored paths, tsconfig projects), and a line disable that says
// why.
//
// The rule set is built from presets their projects keep stable between major
// releases (ESLint's `recommended`, typescript-eslint's `recommended` and
// `recommendedTypeChecked`: "Rule additions and removals are treated as
// breaking changes and will only be done in major version bumps"), plus rules
// named here one by one. typescript-eslint's `strict` presets are not stable in
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
  // An unawaited subtest can be cancelled when the test that started it
  // finishes, so a subtest is awaited or returned (or `void`ed, to say it is
  // meant). Reported by its shape, since its type is the top-level
  // registration's, which no-floating-promises lets float (below): a member
  // call to `test`, by name or by string (`t.test(...)`, `t["test"](...)`), as
  // a statement; and a `test(...)` or `it(...)` called as a statement inside
  // the callback of another, which node:test runs as a subtest. A subtest
  // registered through an aliased import (`import { test as t2 }`), through
  // another of the module's exports (`test.it(...)`), or through a helper is
  // not seen.
  "no-restricted-syntax": [
    "error",
    {
      selector:
        "ExpressionStatement > CallExpression[callee.type='MemberExpression'][callee.property.name='test']",
      message:
        "Await the subtest: an unawaited t.test() can be cancelled when the test that started it finishes.",
    },
    {
      selector:
        "ExpressionStatement > CallExpression[callee.type='MemberExpression'][callee.computed=true][callee.property.value='test']",
      message:
        'Await the subtest: an unawaited t["test"]() can be cancelled when the test that started it finishes.',
    },
    {
      selector:
        "CallExpression[callee.type='Identifier'][callee.name=/^(test|it)$/] > :function ExpressionStatement > CallExpression[callee.type='Identifier'][callee.name=/^(test|it)$/]",
      message:
        "Await the subtest: a test() or it() called inside another test runs as its subtest, and unawaited can be cancelled when that test finishes.",
    },
  ],
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

// Rules that read types, beyond `recommendedTypeChecked`.
const TYPED_RULES = {
  // A switch over a union names every member, so a member added later is a
  // finding rather than a silent fall-through.
  "@typescript-eslint/switch-exhaustiveness-check": "error",
  // node:test's runner tracks the promise each top-level registration returns;
  // awaiting one changes nothing. Every other promise is still checked. The
  // exemption matches by declared type, and node:test declares a subtest's
  // `t.test` as that same `typeof test`, so a subtest is held by the baseline
  // layer's no-restricted-syntax instead.
  "@typescript-eslint/no-floating-promises": [
    "error",
    {
      allowForKnownSafeCalls: [
        {
          from: "package",
          package: "node:test",
          name: ["describe", "it", "suite", "test"],
        },
      ],
    },
  ],
  "@typescript-eslint/no-deprecated": "error",
  "@typescript-eslint/no-unnecessary-condition": "error",
  "@typescript-eslint/no-unnecessary-type-arguments": "error",
  "@typescript-eslint/no-unnecessary-boolean-literal-compare": "error",
  "@typescript-eslint/no-unnecessary-template-expression": "error",
  "@typescript-eslint/no-unnecessary-type-conversion": "error",
  "@typescript-eslint/no-mixed-enums": "error",
  "@typescript-eslint/prefer-reduce-type-parameter": "error",
  "@typescript-eslint/prefer-return-this-type": "error",
  "@typescript-eslint/related-getter-setter-pairs": "error",
  "@typescript-eslint/return-await": [
    "error",
    "error-handling-correctness-only",
  ],
  "@typescript-eslint/use-unknown-in-catch-callback-variable": "error",
  // Not taken from strictTypeChecked, each for what it reports:
  // - restrict-template-expressions and restrict-plus-operands keep their
  //   recommended options: the strict ones refuse a number or a boolean in
  //   text, which is the intended output wherever the repositories write one,
  //   while the recommended ones still refuse `never`, objects and the like.
  // - no-confusing-void-expression reports `() => expect(x)`, a style.
  // - no-misused-spread reports `[...text]`, which the repositories write to
  //   count code points on purpose.
  // - no-meaningless-void-operator reports `void x;`, written to mark a binding
  //   the compiler would otherwise call unused, and its fix leaves a bare `x;`.
  // - no-unnecessary-type-parameters reports parameters that exist for
  //   inference at the call site of a published signature.
  // - no-unsafe-enum-assignment reports protobuf enums built from wire values.
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
const TYPED_TEST_RULES = {
  // Fixtures, mocks and decoded payloads are deliberately untyped.
  "@typescript-eslint/no-unsafe-argument": "off",
  "@typescript-eslint/no-unsafe-assignment": "off",
  "@typescript-eslint/no-unsafe-call": "off",
  "@typescript-eslint/no-unsafe-member-access": "off",
  "@typescript-eslint/no-unsafe-return": "off",
  // For the same reason `.catch((e) => e)` then reads fields of `e`, which
  // `: unknown` would make a type error.
  "@typescript-eslint/use-unknown-in-catch-callback-variable": "off",
  // Tests narrow fixtures for the reader.
  "@typescript-eslint/no-unnecessary-type-assertion": "off",
  // A fake keeps the async signature of what it stands in for.
  "@typescript-eslint/require-await": "off",
  // bun:test declares `expect(p).rejects` and `.resolves` as returning void,
  // though they return a promise the test must await for the assertion to
  // count; the rule would have that await removed.
  "@typescript-eslint/await-thenable": "off",
};

// baselineConfig(options) -> an eslint flat configuration.
//   ignores: gitignore-style patterns the repository states, each with a
//     reason where it states it. Added to eslint's own default ignores.
//   extraFiles: paths of JavaScript files that carry no extension (found by
//     their shebang), linted as JavaScript.
//   typed: false for the baseline layer alone, or { tsconfigRootDir, projects }
//     to add the typed layer; `projects` empty means each file's nearest
//     tsconfig.json.
//   reportUnusedDisables: whether a disable that suppresses nothing is a
//     finding. Only a run with both layers can tell, since a disable may name a
//     typed rule.
export function baselineConfig({
  ignores = [],
  extraFiles = [],
  typed = false,
  reportUnusedDisables = true,
} = {}) {
  const all = [...TS, ...JS, ...extraFiles];
  const config = [
    { ignores },
    {
      linterOptions: {
        reportUnusedDisableDirectives: reportUnusedDisables ? "error" : "off",
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
    // A typescript-eslint rule reads the AST typescript-eslint's parser builds,
    // and one that reads a property only that parser sets throws on ESLint's
    // own instead of reporting: no-useless-constructor reads each constructor
    // parameter's `decorators`, so it fails the run on any JavaScript class
    // whose constructor takes one. In JavaScript it gives way to the core rule
    // it extends, which checks the same thing there, since what it adds
    // (accessibility modifiers, parameter properties, parameter decorators) is
    // syntax ESLint's parser refuses. The rest of the set runs on ESLint's AST
    // without throwing, which the JavaScript syntax corpus in
    // tests/eslint_cases.py holds it to.
    {
      files: [...JS, ...extraFiles],
      rules: {
        "@typescript-eslint/no-useless-constructor": "off",
        "no-useless-constructor": "error",
      },
    },
    // CommonJS has no import but `require`.
    {
      files: ["**/*.cjs"],
      rules: { "@typescript-eslint/no-require-imports": "off" },
    },
    { files: testsAmong(all), rules: BASELINE_TEST_RULES },
  ];
  if (typed) {
    const typedOnly = tseslint.configs.recommendedTypeCheckedOnly.find((c) =>
      c.name?.endsWith("recommended-type-checked-only"),
    );
    config.push(
      {
        files: TS,
        languageOptions: {
          parserOptions:
            typed.projects && typed.projects.length > 0
              ? {
                  project: typed.projects,
                  tsconfigRootDir: typed.tsconfigRootDir,
                }
              : {
                  projectService: true,
                  tsconfigRootDir: typed.tsconfigRootDir,
                },
        },
        rules: { ...typedOnly.rules, ...TYPED_RULES },
      },
      { files: testsAmong(TS), rules: TYPED_TEST_RULES },
    );
  }
  return config;
}
