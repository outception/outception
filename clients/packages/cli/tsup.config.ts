import { defineConfig } from 'tsup'

export default defineConfig({
  entry: ['src/index.ts', 'src/cli.ts'],
  format: ['esm'],
  dts: { entry: ['src/index.ts'] },
  sourcemap: true,
  clean: true,
  banner: ({ format }) =>
    format === 'esm' ? { js: '#!/usr/bin/env node' } : {},
})
