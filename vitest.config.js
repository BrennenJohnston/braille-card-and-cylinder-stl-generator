import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Test file patterns
    include: ['tests/frontend/**/*.test.{js,ts}'],
    
    // Environment configuration
    environment: 'node',
    
    // Enable globals (describe, it, expect, etc.)
    globals: true,
    
    // Coverage configuration (optional, enable when needed)
    coverage: {
      reporter: ['text', 'html'],
      exclude: [
        'node_modules/**',
        'tests/**',
        '**/*.config.*',
      ],
    },
    
    // Test timeout
    testTimeout: 10000,
    
    // Hook timeout for setup/teardown
    hookTimeout: 10000,
  },
});
