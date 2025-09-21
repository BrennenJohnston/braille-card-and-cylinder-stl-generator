/**
 * Vitest Configuration for Braille STL Generator
 * Phase 2+ Testing Setup
 */

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: [],
    include: [
      'tests/**/*.test.js',
      'tests/**/*.spec.js'
    ],
    exclude: [
      'node_modules/**',
      'dist/**'
    ],
    reporter: ['verbose', 'json'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.js'],
      exclude: [
        'src/**/*.test.js',
        'src/**/*.spec.js'
      ]
    },
    // Timeout for async operations
    testTimeout: 10000,
    hookTimeout: 10000
  }
});
