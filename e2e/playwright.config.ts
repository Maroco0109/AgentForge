import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [['github'], ['html', { open: 'never' }]]
    : 'html',
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // In CI, services are started by Docker Compose in the workflow
  // Locally, start services via Docker Compose
  ...(process.env.CI
    ? {}
    : {
        webServer: {
          command: 'cd ../docker && docker compose up -d',
          url: 'http://localhost:3000',
          reuseExistingServer: true,
          timeout: 120000,
        },
      }),
});
