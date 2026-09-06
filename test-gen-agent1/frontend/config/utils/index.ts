/**
 * Whether to generate package preview
 * 是否生成打包报告
 */
export default {};

export function isReportMode(): boolean {
  return process.env.REPORT === 'true';
}

/**
 * 解析 dev server 允许访问的 host 白名单（server.allowedHosts）
 *
 * 背景：Vite 5.4.x 起内置 host 检查中间件，未显式配置的域名（如 CNB 开发云
 * 自动分配的 `xxx-5173.cnb.run` / 各类内网穿透域名）会被 403 拦截：
 *   Blocked request. This host ("xxx-5173.cnb.run") is not allowed.
 *
 * 优先级（从高到低）：
 *   1. 环境变量 VITE_ALLOWED_HOSTS，多个用逗号分隔，如
 *      VITE_ALLOWED_HOSTS=vlnlj2ddew-5173.cnb.run,dev.example.com
 *      设为 `all` / `true` 时表示放行所有 host（等价于 allowedHosts: true）
 *   2. 环境变量 VITE_DEV_HOST / CNB_ALLOWED_HOST / CNB_HOST 指定的域名
 *   3. 默认兜底：localhost、127.0.0.1 及 .cnb.run / .cnb.cool / .localhost 后缀
 *
 * 注意：放行所有 host 会放宽 DNS rebinding 防护，仅在可信的开发环境使用。
 */
export function resolveAllowedHosts(): string[] | true {
  const raw = process.env.VITE_ALLOWED_HOSTS ?? '';
  const trimmed = raw.trim();

  // 显式声明放行所有 host
  if (trimmed === 'all' || trimmed === 'true' || trimmed === '*') {
    return true;
  }

  const hosts = new Set<string>(['localhost', '127.0.0.1', '0.0.0.0']);

  // 1. 环境变量指定的 host（逗号分隔）
  trimmed
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
    .forEach((item) => hosts.add(item));

  // 2. 显式指定的监听域名（CNB 开发云分配的随机域名等）
  ['VITE_DEV_HOST', 'CNB_ALLOWED_HOST', 'CNB_HOST'].forEach((key) => {
    const value = process.env[key]?.trim();
    if (value) {
      hosts.add(value.replace(/^https?:\/\//, '').replace(/\/.*$/, ''));
    }
  });

  // 3. 后缀白名单（以 . 开头表示匹配该域名及其所有子域名）
  ['.localhost', '.cnb.run', '.cnb.cool', '.dev.local'].forEach((suffix) => hosts.add(suffix));

  return [...hosts];
}
