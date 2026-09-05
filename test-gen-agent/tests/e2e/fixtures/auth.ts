/**
 * 登录相关 fixture / 步骤函数。
 *
 * P0 通过真实 UI 登录（顺带验证登录主流程），成功后注入已登录态到 page，
 * 供后续页面用例复用，避免每条用例重复走登录。
 */
import type { Page } from '@playwright/test';

const USER = process.env.E2E_USER || 'admin';
const PASS = process.env.E2E_PASS || 'admin123';

/**
 * 通过登录页 UI 登录并等待跳转到工作台。
 * @param baseURL 形如 http://127.0.0.1:8000/ms（含 /ms 前缀，hash 路由）
 */
export async function uiLogin(page: Page, baseURL: string): Promise<void> {
  await page.goto(`${baseURL}/#/login`);
  await page.getByPlaceholder(/请输入用户名|请输入账号/).first().waitFor({ state: 'visible' });
  await page.getByPlaceholder(/请输入用户名|请输入账号/).first().fill(USER);
  await page.getByPlaceholder('请输入密码').first().fill(PASS);
  await page.getByRole('button', { name: /登\s*录/ }).first().click();
  // 登录成功后跳转到工作台
  await page.waitForURL(/workstation\/home/, { timeout: 30_000 });
}

/** 采集页面运行期间的 JS 异常，供"无致命异常"断言使用。 */
export function collectPageErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(`console.error: ${msg.text()}`);
    }
  });
  return errors;
}
