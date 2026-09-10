import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    // src too, not just scripts: config.test.ts sat in src/ and was silently
    // never collected, so the locale-resolution rules it pins ran untested.
    include: ['scripts/**/*.test.ts', 'src/**/*.test.ts'],
  },
})
