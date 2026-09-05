# 四层架构重构方案（Phase 3 → Phase 7）

> 基于 2026-09 项目现状制定的真实可行迁移路线图。
> 参考样板：`app/routers/defects.py` + `app/services/defect_service.py` + `app/repositories/defect_repo.py` + `app/models/defect.py`

## 一、目标架构

每个业务域统一遵循 **Router → Service → Repository → Database** 四层：

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1  Router  (app/routers/{domain}.py)             │
│  职责: URL 路由 / 参数解析 / Pydantic 请求体验证 / 响应格式  │
│  依赖: 仅 import Service + Model                         │
├─────────────────────────────────────────────────────────┤
│  Layer 2  Service (app/services/{domain}_service.py)     │
│  职责: 业务编排 / 参数归一 / 语义映射 / 状态机校验           │
│  依赖: 仅 import Repository + 业务异常                    │
├─────────────────────────────────────────────────────────┤
│  Layer 3  Repository (app/repositories/{domain}_repo.py) │
│  职责: SQLite CRUD / 表结构管理 / 数据归一化                │
│  依赖: 仅 import Database + BaseRepo                     │
├─────────────────────────────────────────────────────────┤
│  Layer 4  Database (app/core/database.py)               │
│  职责: 统一连接池 / 事务管理 / 跨库合并 (tga.db)            │
└─────────────────────────────────────────────────────────┘
```

**规范约束（新增代码必须遵守）：**

| # | 约束 | 违例示例 |
|---|------|---------|
| 1 | Router 不得直接调用数据访问模块 | `from app.cases.repository import list_cases` ❌ |
| 2 | Router 不得手写 SQL | `conn.execute("SELECT * ...")` ❌ |
| 3 | Service 不得直接拼接 SQL | 应在 Repository 层做 |
| 4 | Repository 不得做业务决策 | 校验状态转换应在 Service 层 |
| 5 | 请求体必须使用 Pydantic 模型 | `request.json()` 读取数据 ❌ |
| 6 | 响应必须使用 `ok()`/`fail()` | 手写 `JSONResponse` ❌ |

## 二、现状盘点

| 业务域 | Router 层 | Service 层 | Repository 层 | Model 层 | 四层完整度 | 备注 |
|--------|-----------|-----------|---------------|---------|-----------|------|
| **defects** | ✅ `routers/defects.py` | ✅ `services/defect_service.py` | ✅ `repositories/defect_repo.py` | ✅ `models/defect.py` | 90% | repo 已接入 service |
| **cases** | ✅ `routers/cases.py` | ✅ `services/case_service.py` | ✅ `repositories/case_repo.py` | ✅ `models/case.py` | 90% | 高级功能部分已迁移 |
| **apitest** | ✅ `routers/apitest.py` | ✅ `services/apitest_service.py` | ✅ `repositories/apitest_repo.py` | ✅ `models/apitest.py` | 85% | store.py 核心 CRUD 已下沉 |
| **projects** | ✅ `routers/projects.py` | ✅ `services/project_service.py` | ✅ `repositories/project_repo.py` | ✅ `models/project.py` | 85% | projects_scan 已迁移 |
| **environments** | ✅ `routers/environments.py` | ✅ `services/environment_service.py` | ✅ `repositories/environment_repo.py` | ✅ `models/environment.py` | 85% | extra 路由已并入 |
| **reports** | ✅ `routers/reports.py` | ✅ `services/report_service.py` | ✅ `repositories/report_repo.py` | ✅ `models/reports.py` | 80% | |
| **insights** | ✅ `routers/insights.py` | ✅ `services/insight_service.py` | ✅ `repositories/insight_repo.py` | ✅ `models/insights.py` | 80% | |
| **generation** | ✅ `routers/generation.py` | ✅ 复用 case/defect/run/insight service | ❌ 无独立 service | ⚠️ `models/schemas.py` | 60% | 多 service 编排，无需独立层 |
| **runs** | ✅ `routers/runs.py` | ✅ `services/run_service.py` | ✅ `repositories/run_repo.py` | ✅ `models/runs.py` | 80% | |
| **scripts** | ✅ `routers/scripts.py` | ✅ `services/script_service.py` | ✅ `repositories/script_repo.py` | ✅ `models/scripts.py` | 80% | |
| **datafactory** | ✅ `routers/datafactory.py` | ✅ `services/datafactory_service.py` | ✅ `repositories/datafactory_repo.py` | ✅ `models/datafactory.py` | 80% | |
| **test_plan** | ✅ `test_plan/router*.py` | ✅ `services/test_plan_service.py` | ✅ `repositories/test_plan_repo.py` | ✅ `models/test_plan.py` | 70% | 大文件需拆分至 <800 行 |
| **auth** | ✅ `auth/router.py` | ✅ `services/auth_service.py` | ✅ `repositories/auth_repo.py` + `user_group_repo.py` | ✅ `models/auth.py` | 80% | user_groups.py 部分迁移 |
| **file_mgmt** | ✅ `file_mgmt/router.py` | ⚠️ 复用 `apitest_service` + `auth_service` | ❌ 无独立 repo | ✅ `models/file.py` | 50% | 文件管理跨域复用 |
| **organizations** | ✅ `routers/organizations.py` | ✅ `services/organization_service.py` | ✅ `repositories/organization_repo.py` | ✅ `models/organizations.py` | 85% | 已从 project 独立 |

### 当前已完成与待办

**已完成**：
- 四层架构已覆盖 10+ 核心业务域（Service + Repository + Model 均已创建并接入）
- `app/routers/` 下核心域路由均已改为调 Service，不再直连旧 store/manager
- P0 全部完成（cases / defects / projects）
- P1 大部分完成（environments / apitest / test_plan / auth 的 service/repo/model 已建）
- adapters/domains 中 A 组 9 个兼容域已迁至 routers（PR #319 已合）

**待办**：
1. **P3 adapters/domains 收敛**：B(#320) 和 C(#321) PR 待合并，剩 12 文件待迁移
2. **request.json() 清零**：目标 0，当前仍存 ~300 处（主要在 adapters/domains 与 routers/cases.py）
3. **手写 JSONResponse → ok()/fail() 统一**：目标 0，全库仍存 ~700 处
4. **最大文件行数门禁 <800**：需拆分 test_plan/router.py(2427行) 等 6 个超大文件
5. **file_mgmt 域规范化**：需独立 service/repo 层
6. **generation 域规范化**：多 service 编排需确认是否独立分层

### 数据访问方式现状

核心 `app/routers/` 中的路由已大部分完成 4 层改造（调 Service），
仍有少量延迟导入遗留：
- `app/routers/cases.py` → `from app.apitest.module_store import build_module_tree`（第 701 行，需改走 Service）
- `app/adapters/domains/` 下文件 → 直接内联 DB 操作或调 store，待 ABC 收敛后统一清理

## 三、迁移路径（按域分步，增量零回归）

每个域遵循相同迁移流程：**Step 0 建档 → Step 1 建 Model → Step 2 建 Repository → Step 3 建 Service → Step 4 改 Router → Step 5 验证**。

### 迁移优先级

| 优先级 | 业务域 | 当前状态 |
|--------|--------|---------|
| ✅ 已完成 | cases / defects / projects / environments | Service+Repo+Model 已建并接入 |
| ✅ 已完成 | apitest | apitest_service/repo/model 已建（~85%） |
| ✅ 已完成 | auth | auth_service/auth_repo/auth_repo 已建（~80%） |
| ✅ 已完成 | test_plan | test_plan_service/repo 已建（~70%） |
| ✅ 已完成 | runs / insights / datafactory / scripts / reports | 均已建（~80%） |
| 🔄 进行中 | adapters/domains 收敛（B #320 / C #321） | 12 文件未迁出 |
| 📋 待办 | file_mgmt 独立 service/repo | 目前复用 apitest/auth service |
| 📋 待办 | 规范清理（request.json/JSONResponse 清零） | ~300 处 + ~700 处 |

### 每个域的标准步骤

#### Step 1: 新建 `app/models/{domain}.py`
- 把路由中所有 `request.json()` / `body: dict` 请求体转换为 Pydantic 模型
- 保留路径参数、查询参数不变
- 用 `Field(...)` 声明必填、范围、格式

#### Step 2: 新建 `app/repositories/{domain}_repo.py`
- 继承 `app.repositories.base.BaseRepo`
- 只写 SQLite CRUD（不写业务逻辑）
- 从现有 domain store/manager 中**复制** CRUD 实现
- 保持输出字段与旧层一致（参考 case_repo 的 `_normalize_record`）

#### Step 3: 新建 `app/services/{domain}_service.py`
- 业务编排：校验 → 调 repo → 组装返回
- 错误用 `app.core.exceptions`（NotFoundError / ValidationError）
- 提供模块级单例（`xxx_service = XxxService()`）

#### Step 4: 改造 `app/routers/{domain}.py`
- 移除所有 `from app.{old_domain} import` 延迟导入
- 替换为 `from app.services.{domain}_service import {domain}_service`
- 把 `async def _body(request: Request)` 改为 Pydantic 参数
- 响应统一用 `ok()`/`fail()`

#### Step 5: 验证（每步必须通过）
```bash
# 1. 增量 lint
python3 scripts/lint_diff.py --all

# 2. 路由冲突（新增路由不允许冲突）
python3 scripts/route_conflict_check.py --check

# 3. 前端契约
python3 scripts/frontend_contract_check.py --check

# 4. 按钮级死链
python3 scripts/button_matrix.py --check

# 5. 前端矩阵
python3 scripts/gen_frontend_matrix.py --check

# 6. 数据库合并
python3 scripts/merge_databases.py --check

# 7. 全量测试
python3 -m pytest tests/ -q --cov=app --cov-branch
python3 scripts/report_coverage.py coverage.lcov 40 20
```

## 四、各域详细迁移计划

### P0-1: Cases ✅ 已完成

**当前状态**：case_service + case_repo + case model 已建立，routers/cases.py 已调用。
剩余：高级功能（relations/reviews/dependencies/versions/requirements）部分仍走
旧 management，需逐步迁移到 service。含 28 处 request.json() 待替换。

### P0-2: Defects ✅ 已完成

**当前状态**：defect_service + defect_repo + defect model 已建立，
routers/defects.py 已走 service 层。repo 已接通。

### P0-3: Projects ✅ 已完成

**当前状态**：project_service + project_repo + organization_repo + project model
均已建立。routers/projects.py + projects_scan.py + organizations.py 均调用 service。
旧 management.py/manager.py/organization_store.py 保留为兼容层供 adapters 引用。

### P1-1: Environments ✅ 已完成

**当前状态**：environment_service + environment_repo + environment model 均已建立，
routers/environments.py + environments_extra.py 均调用 service。

### P1-2: Apitest ✅ 已完成（~85%）

**当前状态**：apitest_service + apitest_repo + apitest model 均已建立。
routers/apitest.py 核心 CRUD 走 service。剩余：
- store.py 中部分业务逻辑（场景/Mock/执行）待逐步下沉
- adapters/domains/api_testing.py（2739 行）迁移后清理

### P1-3: Test Plan ✅ Service/Repo 已建

**当前状态**：test_plan_service + test_plan_repo + test_plan model 已建立。
routers 已在逐步接入 service。剩余工作：
1. router.py（2427 行）需拆分至 <800 行
2. router_dashboard.py 已按业务拆分为 home/layout/stats/mine 4 段（均 <800 行）✅
3. 文件中仍有 request.json() 直接调用（3处）需替换为 read_body

### P1-4: Auth ✅ Service/Repo 已建

**当前状态**：auth_service + auth_repo + user_group_repo + auth model 均已建立。
routers 已接入 service。剩余工作：
- auth/router.py（1204 行）需拆分至 <800 行
- 文件中 89 处手写 JSONResponse 待统一

### P2: Runs / Insights / Datafactory / Scripts / Reports ✅ 已完成

**当前状态**：各域 service + repo + model 均已建立并接入 router。

### P3: adapters/domains/ 收敛 🔄 进行中

**当前进度**：
- 🅰️ 纯兼容占位域（9 文件 214 路由）：PR #319 已合并 ✅
- 🅱️ 已有 Service 覆盖域（7 文件 705 路由）：PR #320 待合并
- 🅲 复杂域（6 文件 477 路由）：PR #321 待合并（部分内容）

ABC 三项全部合入后即可删除 `app/adapters/domains/` 目录及清理 main.py 路由挂载。

## 五、验证门禁清单

| # | 验证 | 命令 | 门槛 |
|---|------|------|------|
| 1 | 增量 lint | `python3 scripts/lint_diff.py --all` | 0 违规 |
| 2 | 路由冲突 | `python3 scripts/route_conflict_check.py --check` | 0 冲突 |
| 3 | 前端契约 | `python3 scripts/frontend_contract_check.py --check` | 0 缺失 |
| 4 | 按钮死链 | `python3 scripts/button_matrix.py --check` | 0 死链 |
| 5 | 前端矩阵 | `python3 scripts/gen_frontend_matrix.py --check` | 无差异 |
| 6 | 数据库合并 | `python3 scripts/merge_databases.py --check` | 无冲突 |
| 7 | 全量测试 | `python3 -m pytest tests/ -q` | 全部通过 |
| 8 | 覆盖率 | `python3 scripts/report_coverage.py coverage.lcov 40 20` | 行≥40% 分支≥20% |

**每步迁移验收标准**：
- ✅ 不影响任何已存在路由（路由冲突检测通过）
- ✅ 不影响前端契约（前端契约检查通过）
- ✅ 不影响已有测试（全量测试零回归）
- ✅ 新增 Repository 输出与旧层完全一致（对齐测试通过）

## 六、分阶段执行时间表

| 阶段 | 内容 | 状态 | 备注 |
|------|------|------|------|
| Phase A | cases 补全 + defects repo 接通 | ✅ 已完成 | service+repo 已接入 |
| Phase B | projects + environments | ✅ 已完成 | 各域 service/repo/model 已建 |
| Phase C | apitest 分 5 批 | 🔄 ~85% | 核心 CRUD 已迁移，场景/Mock/执行待下沉 |
| Phase D | test_plan + auth | 🔄 ~75% | service/repo/model 已建，大文件待拆分 |
| Phase E | runs + insights + datafactory + scripts + reports | ✅ 已完成 | 均已建并接入 |
| Phase F | adapters/domains 收敛 | 🔄 进行中 | A组(#319)已合并，B(#320)/C(#321)待合 |

**当前待办重点**：
1. 合入 B(#320) + C(#321) 完成 adapters/domains 收敛
2. 删除 adapters/domains 目录（ABC 完成后执行）
3. request.json() 清零（~318 处）
4. JSONResponse → ok()/fail() 统一（~764 处）
5. 超大文件拆分（6 个 >800 行文件）
6. sqlite3.connect() 收敛到 Database 类
7. 修复并关闭存量 open bug issue

## 七、风险控制

1. **零回归保证**：每步只做「数据访问方式」的替换，不改变任何行为
2. **对齐测试先行**：Repository 层必须先通过新旧输出对齐测试，再切换 service 调用
3. **旧层兼容保留**：旧 domain store/manager 保留为兼容层，不立即删除
4. **路由不重注册**：迁移过程中路由器已在 main.py 注册的路径不变
5. **逐域推进**：不一次改多域，避免回归排查困难
6. **CI 全量验证**：每个 PR 在合并前必须过全部 CI 检查

## 八、成功指标

| 指标 | 当前 | 目标 | 状态 |
|------|------|------|------|
| Router 直接调数据访问 | 少量遗留 | 0 | 进行中 |
| request.json() 使用点 | ~318 | 0 | 进行中 |
| 手写 JSONResponse | ~764 | 0 | 进行中 |
| Service 层存在 | 15+ 域 | 全部域 | ✅ 大部分完成 |
| Repository 层存在 | 16+ 域 | 全部域 | ✅ 大部分完成 |
| Model 层存在 | 15+ 域 | 全部域 | ✅ 大部分完成 |
| adapters/domains 文件数 | 12（原22，A组已迁出10） | 0 | 🔄 进行中 |
| 最大文件行数 | 2740 (adapters/api_testing.py) | < 800 | 进行中 |
| 测试通过率 | 保持 | 100% | ✅ |


---

## 兼容层（*_compat.py）冻结约束

TestPilot 兼容路由（`app/routers/*_compat.py`）已进入**冻结**状态：

- **禁止新增** `*_compat.py` 文件。`scripts/lint_diff.py` 已在增量 lint 门禁中加入检查，
  一旦新增即阻断 CI。
- 新功能一律写入**正规路由层**（`app/routers/` 下非 `*_compat.py` 的文件）。
- 存量 `*_compat.py` 允许修改，但仅用于**逐步收敛 / 迁移 / 修复缺陷**，不得继续堆积业务。
- 收敛方向：把 compat 中的真实逻辑下沉到 Service / Repository，compat 退化为纯路径转发
  （仅做参数签名适配），最终逐步合并进正规路由。

> 冻结原因：早期为了对齐 TestPilot 前端，兼容层曾无限膨胀并反客为主，体量一度超过
> 正规业务路由总和，导致两套路由/响应体系并存、分层收益被稀释。通过冻结新增从源头遏制。
