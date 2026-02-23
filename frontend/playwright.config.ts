import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E テスト設定
 *
 * フロントエンド (Vite dev server port 5290) に対してE2Eテストを実行する。
 * APIはPlaywrightのroute interceptでモックするため、バックエンド不要。
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['github']] : 'html',
  timeout: 30_000,

  use: {
    baseURL: 'http://localhost:5290',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5290',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
