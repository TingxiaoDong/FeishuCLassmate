import { defineConfig } from 'vitest/config';
import { resolve } from 'node:path';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    exclude: ['**/node_modules/**', '**/dist/**'],
  },
  resolve: {
    alias: {
      // Allow tests to import src/ with bare paths when needed.
      // Tools import via relative .js paths so this is mostly for helpers.
      '@src': resolve(import.meta.dirname, '../src'),
    },
  },
});
