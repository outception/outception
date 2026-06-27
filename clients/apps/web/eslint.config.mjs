import { nextJsConfig } from '@outception-com/eslint-config/next-js'
import outceptionPlugin from './eslint-rules/index.mjs'

/** @type {import("eslint").Linter.Config} */
export default [
  ...nextJsConfig,
  {
    plugins: {
      outception: outceptionPlugin,
    },
    languageOptions: {
      parserOptions: {
        projectService: {
          allowDefaultProject: [
            'vitest.config.ts',
            '*.config.mjs',
            'instrumentation-client.ts',
          ],
        },
      },
    },
  },
  {
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          destructuredArrayIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/refs': 'warn',
      'react-hooks/static-components': 'warn',
      'react-hooks/preserve-manual-memoization': 'warn',
      'react-hooks/immutability': 'warn',
      'react-hooks/purity': 'warn',
      'outception/no-toast-error-detail': 'error',
    },
  },
  {
    files: ['**/*.tsx'],
    rules: {
      'react/no-danger': 'error',
      'react/self-closing-comp': 'warn',
      'react/jsx-no-useless-fragment': 'warn',
      'outception/no-classname-box': 'error',
      'outception/no-classname-text': 'error',
      'outception/no-style-box': 'error',
      'outception/no-style-text': 'error',
      'outception/no-next-image': 'error',
    },
  },
  {
    files: [
      'src/app/(main)/onboarding/**/*.tsx',
      'src/components/Onboarding/**/*.tsx',
    ],
    rules: {
      'outception/no-raw-html-layout': 'error',
    },
  },
  {
    ignores: [
      'node_modules/**',
      '.next/**',
      'out/**',
      'build/**',
      'coverage/**',
      'eslint-rules/**',
      'src/app/.well-known/**',
      'next-env.d.ts',
      'babel.config.js',
    ],
  },
]
