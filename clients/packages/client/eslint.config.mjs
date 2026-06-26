import { config } from '@outception-com/eslint-config/base'

/** @type {import("eslint").Linter.Config[]} */
export default [
  {
    ignores: ['node_modules/**', 'dist/**'],
  },
  ...config,
  {
    files: ['src/v1.ts'],
    rules: {
      'max-lines': 'off',
      'max-lines-per-function': 'off',
    },
  },
]
