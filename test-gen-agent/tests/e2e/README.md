# E2E 端到端测试（Playwright + 真实 Chromium）

本目录存放基于 **真实浏览器** 的端到端测试，覆盖两套目标：

1. **P0 核心冒烟**（`specs/p0-smoke.spec.ts`）：核心流程不断 · 状态不错 · 边界不漏 · 数据能自证
2. **前端性能回归护栏**（`specs/perf-regression.spec.ts`）：把登录/首屏优化固化成阈值告警

## 覆盖用例

### P0 核心冒烟

| # | 用例 | 说明 |
|---|------|------|
| 1 | 登录页可达 + 表单渲染 | 登录页能正常打开、用户名/密码/登录按钮齐全 |
| 2 | UI 登录 → 跳转工作台 | 走真实登录表单，登录成功后进入 `/workstation/home` |
| 3 | 工作台渲染 | 工作台不白屏、出现卡片，无致命 JS 异常 |
| 4 | 功能用例列表可达 + 数据加载 | 导航到功能用例，前端成功调用 `/functional/case/page` |
| 5 | 数据自证·业务闭环 | 用唯一名创建 → 回查可见唯一 → 删除 → 回查消失 |
| 6 | 关键页面无致命 JS 异常 | 工作台 + 功能用例全程无 `pageerror` |

### 前端性能回归护栏

将以下已合入的性能优化固化为护栏，防止后续改动把耗时/首屏体积拉回去：

| # | 护栏 | 守护的优化 | 关键指标（本地近冷启动实测）|
|---|------|-----------|---------------------------|
| ① | 登录页加载→表单可交互 | #497 启动阶段并行化 | ~665ms |
| ② | 登录点击→工作台就绪 | #497 启动阶段并行化 | ~2217ms |
| ③ | 登录页首屏**不**拉取 codeEditor/monaco chunk | #498 monaco 懒加载 | 同步拉取即失败 |
| ④ | 功能用例大列表（虚拟滚动）首屏就绪 | #499 base-table 虚拟滚动 | <3s |

> 说明：此前登录/首屏为 **50s 级**，经 #497-#499 优化降到 **~3s 级**。这些护栏就是
> 为防止将来某次改动又把耗时拉回 50s、或把 monaco 重新同步塞回首屏。

## 运行方式

```bash
# 一键（本地 / CI 复用同一入口）：构建前端 → seed → 起后端 → 跑全部 E2E
bash scripts/e2e.sh

# dist 已构建时跳过构建
E2E_SKIP_BUILD=1 bash scripts/e2e.sh

# 只跑性能回归（含 JSON 报告 + 硬闸门）
E2E_SKIP_BUILD=1 PERF_STRICT=1 E2E_RUN_OPTIONS="perf-regression" bash scripts/e2e.sh

# 只跑 P0 冒烟 / 指定端口
E2E_SKIP_BUILD=1 E2E_RUN_OPTIONS="--grep 数据自证" bash scripts/e2e.sh
```

### 性能回归阈值（可用环境变量覆盖，ms）

| 变量 | 默认 | 说明 |
|------|------|------|
| `PERF_GATE_MS` | 15000 | 统一严重/超时闸门 |
| `PERF_LOGIN_LOAD_MS` | 5000 | ① 登录页加载 → 表单可交互 |
| `PERF_LOGIN_ENTER_MS` | 15000 | ② 登录 → 工作台就绪 |
| `PERF_CASE_PAGE_MS` | 20000 | ④ 功能用例大列表首屏 |
| `PERF_STRICT` | 关 | `=1` 时超阈值即断言失败（硬门禁） |

- **默认（宽松/告警）**：耗时节拍写入 `tests/e2e/perf-report.json`（各阶段耗时 + 阈值 + OK/WARN/FAIL 判定）并打日志，适合 CI 巡检、不误伤构建；**③ 的 codeEditor/monaco 结构回归为硬断言**（只要登录页同步拉取该 chunk 即失败，与时间无关）。
- **`PERF_STRICT=1`**：任一超阈值即断言失败，用于本机/发布前严格校验。

## 目录结构

```
tests/e2e/
├── playwright.config.ts   # baseURL 指向后端 /ms（SPA+hash 路由）
├── fixtures/auth.ts       # UI 登录 + 页面错误采集
├── helpers/api.ts         # 直连后端造/查/删数据（数据能自证）
├── specs/
│   ├── p0-smoke.spec.ts           # P0 核心冒烟 6 条
│   └── perf-regression.spec.ts    # 前端性能回归护栏（真实浏览器+阈值）
└── package.json           # 仅依赖 @playwright/test
```

## CI 接入

`.cnb.yml` 的 `$: pull_request` 下已有独立 pipeline `p0-smoke-e2e`：
- 用 `mcr.microsoft.com/playwright` 镜像（自带 node/npm/chromium/python3）
- `ifModify` 仅在 E2E / 前端相关文件变更时触发
- 本地与 CI 共用 `scripts/e2e.sh`，会一并跑 `specs/` 下的冒烟 + 性能护栏

## 关键约定

- **后端 serve SPA**：由 FastAPI 在 `/ms` 前缀 serve 前端 `dist`，Playwright 用 hash 路由访问页面，无需额外 nginx/Vite。
- **数据自证**：通过 `helpers/api.ts` 直连后端造/查/删唯一名数据，不污染业务数据。
- **稳定选择器**：优先用 placeholder / 角色 / 文本，不依赖易变的动态 Tailwind class。
- **性能报告**：`perf-regression` 运行后写 `tests/e2e/perf-report.json`（已 gitignore），供 CI/看板消费。
