import { defineConfig, devices } from '@playwright/test';

/**
 * P0 核心冒烟 E2E 配置。
 *
 * 页面由 FastAPI 后端在 /ms 前缀下 serve（SPA + hash 路由）：
 *   - /ms/#/login            登录页
 *   - /ms/#/workstation/home 工作台
 *   - /ms/#/case-management/featureCase  功能用例列表
 *
 * 因此 baseURL 指向 /ms，用 hash 路由访问具体页面，无需额外 nginx/Vite。
 */
export default defineConfig({
  testDir: './specs',
  timeout: 90_000,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:8000/ms',
    headless: true,
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 30_000,
    navigationTimeout: 60_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
