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
      'src/components/CustomerPortal/**/*.{ts,tsx}',
      'src/app/**/portal/**/*.{ts,tsx}',
    ],
    rules: {
      'outception/no-merchant-queries-in-customer-portal': 'error',
      'outception/no-merchant-api-calls-in-customer-portal': 'error',
    },
  },
  {
    files: ['src/app/**/portal/**/page.tsx'],
    ignores: [
      'src/app/**/portal/page.tsx',
      'src/app/**/portal/request/page.tsx',
      'src/app/**/portal/authenticate/page.tsx',
      'src/app/**/portal/verify-email/page.tsx',
      'src/app/**/portal/claim/page.tsx',
    ],
    rules: {
      'outception/require-customer-portal-page': 'error',
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
