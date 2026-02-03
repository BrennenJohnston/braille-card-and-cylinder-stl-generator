import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for E2E tests.
 * 
 * SAFETY-CRITICAL: These tests guard against silent truncation bugs (S0 severity).
 * The silent truncation E2E test (tests/e2e/silentTruncation.spec.ts) MUST NOT
 * be skipped or quarantined without explicit approval.
 */
export default defineConfig({
  testDir: './tests/e2e',
  
  // Run tests in files in parallel
  fullyParallel: true,
  
  // Fail the build on CI if test.only is accidentally left in
  forbidOnly: !!process.env.CI,
  
  // Retry failed tests on CI
  retries: process.env.CI ? 2 : 0,
  
  // Use 1 worker on CI for consistent results
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter configuration
  reporter: process.env.CI ? 'github' : 'html',
  
  // Shared settings for all projects
  use: {
    // Base URL for navigation
    baseURL: 'http://localhost:5001',
    
    // Collect trace on failure for debugging
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
  },

  // Configure projects for different browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Additional browsers can be enabled for full compatibility testing
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // Web server configuration
  // Starts the Flask backend automatically before tests
  webServer: {
    command: 'python backend.py',
    port: 5001,
    reuseExistingServer: !process.env.CI,
    timeout: 120000, // 2 minutes for server startup
    env: {
      PORT: '5001',
      FLASK_ENV: 'development',
    },
  },
  
  // Test timeout
  timeout: 60000, // 1 minute per test
  
  // Expect timeout for assertions
  expect: {
    timeout: 10000, // 10 seconds for assertions
  },
});
