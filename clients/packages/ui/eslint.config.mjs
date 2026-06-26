import { config } from '@outception-com/eslint-config/react-internal'

/** @type {import("eslint").Linter.Config[]} */
export default [
  {
    ignores: ['node_modules/**', 'dist/**'],
  },
  ...config,
  {
    rules: {
      'react/prop-types': 'off',
      'react/no-unknown-property': [
        'error',
        { ignore: ['cmdk-input-wrapper'] },
      ],
    },
  },
]
