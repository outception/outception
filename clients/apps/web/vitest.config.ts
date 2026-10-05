import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'
import { defineConfig } from 'vitest/config'

const stylexBabelPlugin = [
  '@stylexjs/babel-plugin',
  {
    dev: true,
    runtimeInjection: false,
    treeshakeCompensation: true,
    unstable_moduleResolution: { type: 'commonJS', rootDir: __dirname },
  },
]

export default defineConfig({
  plugins: [
    tsconfigPaths({ projects: ['tsconfig.json'] }),
    react({ babel: { plugins: [stylexBabelPlugin] } }),
  ],
  test: {
    environment: 'jsdom',
    fsModuleCache: true,
    exclude: ['**/node_modules/**', '**/dist/**'],
    env: {
      NEXT_PUBLIC_API_URL: 'http://api.outception.test',
      NEXT_PUBLIC_FRONTEND_BASE_URL: 'https://outception.com',
    },
  },
})
