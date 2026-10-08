import { defineConfig } from 'tsup'

export default defineConfig([
  {
    entry: ['src/index.ts'],
    format: ['cjs', 'esm'],
    minify: true,
    dts: process.env.OUTCEPTION_SKIP_DTS !== '1',
  },
])
