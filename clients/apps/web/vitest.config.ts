import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
    env: {
      NEXT_PUBLIC_FRONTEND_BASE_URL: 'https://outception.com',
      NEXT_PUBLIC_SANDBOX_FRONTEND_BASE_URL: 'https://sandbox.outception.com',
    },
  },
})
