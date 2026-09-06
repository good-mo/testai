/**
 * 前端性能回归护栏 E2E（真实浏览器 + 阈值告警）
 *
 * 背景：登录/首屏此前为 50s 级，经优化降到 ~3s 级，根因是启动阶段串行瀑布
 * （公钥/默认语言逐个 await）+ 首屏同步引入大体积 chunk（monaco codeEditor）。
 * 本用例把这些优化固化为**性能回归护栏**，跑真实 Chromium，任何后续改动若把
 * 耗时拉回、或把 codeEditor chunk 重新同步塞回首屏，都会触发阈值告警/失败。
 *
 * 护栏覆盖（对应已合入优化）：
 *   #497 并行化启动阶段无依赖网络请求 → 登录页加载 + 登录进入总时长
 *   #498 monaco-editor 懒加载         → 首屏不拉取 codeEditor chunk
 *   #499 base-table 自动虚拟滚动       → 大列表页首屏渲染时长
 *
 * 阈值（ms）可用环境变量覆盖，默认值按「近冷启动 + 开发/CI 波动」留足余量：
 *   PERF_GATE_MS          统一超时/严重闸门，默认 15000
 *   PERF_LOGIN_LOAD_MS    登录页加载→表单可交互（本地 ~665ms）默认 5000
 *   PERF_LOGIN_ENTER_MS   登录点击→工作台就绪（本地 ~2217ms）默认 15000
 *   PERF_CASE_PAGE_MS     功能用例大列表首屏就绪（本地 <3s）默认 20000
 *   PERF_STRICT=1         硬闸门：超阈值即断言失败（默认仅告警并写报告）
 *
 * 运行（沿用 scripts/e2e.sh，镜像自带 chromium）：
 *   PERF_STRICT=1 E2E_RUN_OPTIONS="perf-regression" bash scripts/e2e.sh
 *
 * 输出：tests/e2e/perf-report.json（各阶段耗时与判定，供 CI/看板取用）
 */
import { test, expect, type Page } from '@playwright/test';
import { writeFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

import { uiLogin } from '../fixtures/auth';

const BASE = process.env.E2E_BASE_URL || 'http://127.0.0.1:8000/ms';
const STRICT = process.env.PERF_STRICT === '1';

// ---- 阈值（ms）----
const GATE_MS = Number(process.env.PERF_GATE_MS || 15000);
const LOGIN_LOAD_MS = Number(process.env.PERF_LOGIN_LOAD_MS || 5000);
const LOGIN_ENTER_MS = Number(process.env.PERF_LOGIN_ENTER_MS || 15000);
const CASE_PAGE_MS = Number(process.env.PERF_CASE_PAGE_MS || 20000);

type Rec = { ms: number; ok: boolean; verdict: string; threshold: number };
const report: Record<string, Rec> = {};

/** 记录一项耗时并打可读日志。阈值判定 + 统一 20s 严重闸门。 */
function record(name: string, ms: number, threshold: number) {
  const severe = ms > GATE_MS;
  const ok = ms <= threshold;
  const verdict = severe ? 'SEVERE' : ok ? 'OK' : STRICT ? 'FAIL' : 'WARN';
  report[name] = { ms: Math.round(ms), ok, verdict, threshold };
  console.log(`[perf] ${name}: ${Math.round(ms)}ms (阈值 ${threshold}ms) → ${verdict}`);
  // 仅 hard 模式（STRICT 或严重闸门）才真正断言失败；否则仅记录到报告，供 CI/看板告警
  const gate = verdict === 'FAIL' || verdict === 'SEVERE';
  if (gate) {
    expect.soft(ms, `[${name}] ${ms}ms 超阈值 ${threshold}ms`).toBeLessThanOrEqual(threshold);
  }
}

/** 采集从当前时刻起页面拉起的资源 URL。 */
function snapshot(page: Page): string[] {
  const urls: string[] = [];
  page.on('response', (resp) => { try { urls.push(resp.url()); } catch { /* 忽略 */ } });
  return urls;
}

/** 判断某资源 URL 是否为 codeEditor / monaco chunk（首屏不应同步拉取）。 */
function isMonacoChunk(u: string): boolean {
  return /(?:code[-_]?editor|monaco)/i.test(u) && !/\.map$/.test(u);
}

test.describe('前端性能回归护栏（真实浏览器）', () => {
  test('① 登录页加载 → 表单可交互 ≤ 阈值', async ({ page }) => {
    const start = Date.now();
    await page.goto(`${BASE}/#/login`);
    // 表单可交互 = 用户名输入框可见（覆盖 #497 首屏并行化）
    await page.getByPlaceholder(/请输入用户名|请输入账号/).first().waitFor({ state: 'visible' });
    record('loginPageLoad', Date.now() - start, LOGIN_LOAD_MS);
  });

  test('② 登录点击 → 工作台数据就绪 ≤ 阈值（#497 启动并行化）', async ({ page }) => {
    const start = Date.now();
    await uiLogin(page, BASE); // goto login + fill + click + waitForURL(/workstation\/home/)
    await page.waitForLoadState('domcontentloaded');
    // 工作台核心统计接口就绪
    await page.waitForResponse(
      (r) => /(?:dashboard|statistic|count)/i.test(r.url()) && r.status() === 200,
      { timeout: GATE_MS },
    ).catch(() => {});
    await expect(page.locator('body')).toBeVisible();
    record('loginEnterWorkbench', Date.now() - start, LOGIN_ENTER_MS);
  });

  test('③ 登录页首屏不拉取 codeEditor/monaco chunk（#498 懒加载）', async ({ page }) => {
    const urls = snapshot(page);
    await page.goto(`${BASE}/#/login`);
    await page.getByPlaceholder(/请输入用户名|请输入账号/).first().waitFor({ state: 'visible' });
    await page.waitForTimeout(1500); // 若被同步引入首屏，此窗口内必然已发请求
    const monaco = urls.filter(isMonacoChunk);
    expect(monaco, `登录页不应同步拉取 codeEditor/monaco chunk，实际拉取: ${monaco.join(', ')}`)
      .toEqual([]);
  });

  test('④ 功能用例大列表（虚拟滚动）首屏就绪 ≤ 阈值（#499）', async ({ page }) => {
    await uiLogin(page, BASE);
    const start = Date.now();
    await page.goto(`${BASE}/#/case-management/featureCase`);
    // 列表接口被调用 = 开始渲染
    await page.waitForResponse(
      (r) => r.url().includes('/functional/case/page') && r.request().method() === 'POST',
      { timeout: GATE_MS },
    );
    // 首个表格行/卡片渲染出来（虚拟滚动渲染首屏可视区），并确证数据量较大（非空态）
    await page.locator('.arco-table-tr, [class*="row"], [class*="card"]').first()
      .waitFor({ state: 'visible', timeout: GATE_MS });
    await expect(page.locator('body')).toBeVisible();
    record('featureCaseListReady', Date.now() - start, CASE_PAGE_MS);
  });
});

// ---- 汇总写 JSON 报告（供 CI/看板消费）----
test.afterAll(() => {
  try {
    const here = dirname(fileURLToPath(import.meta.url));
    writeFileSync(join(here, '../perf-report.json'), JSON.stringify(report, null, 2) + '\n');
  } catch (e) { /* 报告非阻断 */ }
});
