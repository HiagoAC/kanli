import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    isolate: true,
    pool: 'forks',

    coverage: {
      provider: 'v8',
      reportsDirectory: 'coverage',
      reporter: ['text', 'lcov'],
      include: ['src/**/*'],
      exclude: [
        '**/*.d.ts',
        '**/*.test.*',
        '**/*.spec.*',
        'src/main.tsx',
        'src/vite-env.d.ts',
        '**/types.ts', 
      ],
    },
  },
})
