/**
 * 直连后端 API 的工具（配合"数据能自证"）。
 *
 * 后端登录：POST /login -> { sessionId, csrfToken }
 * 认证头：  X-AUTH-TOKEN / CSRF-TOKEN
 * 业务路由：/functional/case/{add,page,delete,...}
 */
import type { APIRequestContext } from '@playwright/test';

export interface AuthSession {
  sessionId: string;
  csrfToken: string;
  apiBase: string;
}

/**
 * 登录后端并返回一个携带认证头的 APIRequestContext。
 *
 * 直接复用 @playwright/test 注入的 request fixture（其本身即 APIRequestContext），
 * 用绝对 URL 发请求，避免再次 newContext。认证头通过每次请求显式传 header 携带，
 * 从而不污染测试共享的 request 上下文。
 * @param request 由 @playwright/test 注入的 request fixture
 * @param baseUrl 形如 http://127.0.0.1:8000/ms（自动剥离 /ms 得到 API 根）
 */
export async function loginAndGetSession(
  request: APIRequestContext,
  baseUrl: string,
): Promise<AuthSession> {
  const apiBase = baseUrl.replace(/\/ms\/?$/, '');
  const resp = await request.post(`${apiBase}/login`, {
    data: { username: process.env.E2E_USER || 'admin', password: process.env.E2E_PASS || 'admin123' },
  });
  if (resp.status() !== 200) {
    throw new Error(`后端登录失败 HTTP ${resp.status()}: ${await resp.text()}`);
  }
  const body = (await resp.json()) as any;
  const session = body?.data;
  if (!session?.sessionId || !session?.csrfToken) {
    throw new Error(`登录响应缺少凭证: ${JSON.stringify(body)}`);
  }
  return {
    sessionId: session.sessionId,
    csrfToken: session.csrfToken,
    apiBase,
    request,
  };
}

/** 生成认证头。 */
function authHeaders(s: AuthSession): Record<string, string> {
  return { 'X-AUTH-TOKEN': s.sessionId, 'CSRF-TOKEN': s.csrfToken };
}

/** 创建一条功能用例，返回其 id。 */
export async function createFunctionalCase(s: AuthSession, name: string): Promise<string> {
  const resp = await s.request.post(`${s.apiBase}/functional/case/add`, {
    headers: authHeaders(s),
    data: { name, priority: 'P2', test_type: 'functional' },
  });
  if (resp.status() >= 500) {
    throw new Error(`创建功能用例 500: ${await resp.text()}`);
  }
  const body = (await resp.json()) as any;
  const id = body?.data?.id;
  if (!id) throw new Error(`创建功能用例无 id: ${JSON.stringify(body)}`);
  return id;
}

/** 按唯一名在分页列表搜索，返回匹配条目数组。 */
export async function searchFunctionalCaseByName(s: AuthSession, name: string): Promise<any[]> {
  const resp = await s.request.post(`${s.apiBase}/functional/case/page`, {
    headers: authHeaders(s),
    data: { keyword: name, pageSize: 50, current: 1 },
  });
  if (resp.status() >= 500) {
    throw new Error(`搜索功能用例 500: ${await resp.text()}`);
  }
  const body = (await resp.json()) as any;
  const data = body?.data;
  const list = Array.isArray(data?.list) ? data.list : Array.isArray(data) ? data : [];
  return list.filter((it: any) => it.name === name);
}

/** 删除功能用例（进回收站），返回是否成功。 */
export async function deleteFunctionalCase(s: AuthSession, id: string): Promise<boolean> {
  const resp = await s.request.post(`${s.apiBase}/functional/case/delete`, {
    headers: authHeaders(s),
    data: { id },
  });
  return resp.status() < 500;
}

/** 生成一个带前缀的唯一名，用于造数据与回查。 */
export function uniqueName(prefix = 'e2eSmoke'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}
