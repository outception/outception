# Why this package exports source, not `dist`

`exports` points **both** `types` and `default` at `./src`, unlike
`@outception-com/client` and `@outception-com/i18n`, which point at `./dist`.
This is deliberate - do not "fix" it to match them.

**StyleX must compile from source in the consumer's build.** `tsup` does not run
`@stylexjs/babel-plugin`, so `dist/index.js` still contains raw
`@stylexjs/stylex` imports. Worse, `dist` is bundled and minified, which inlines
`tokens.stylex.ts` and destroys the file paths StyleX uses to resolve token
references (`unstable_moduleResolution: { type: 'commonJS', rootDir }` in
`apps/web/babel.config.js`). Consuming `dist` yields unstyled components.

The consumer opts in via `transpilePackages: ['@outception-com/orbit']` in
`apps/web/next.config.mjs`.

`types` also points at source so the published types can't drift from the code
that actually compiles, and so typechecking a consumer doesn't require a build
of this package first.

The package is `private: true`; `dist` remains as a local build artifact for
anything that wants a pre-bundled copy, but nothing in the monorepo consumes it.
