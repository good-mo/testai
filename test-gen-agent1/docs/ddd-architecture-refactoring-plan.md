# DDD（领域驱动设计）架构改造方案

> 基于 2026 项目现状（已完成 **Router → Service → Repository → Database 四层**分层）制定的
> **由贫血模型演进到领域模型（DDD）** 的完整路线图与试点落地。
>
> 试点代码：`app/domain/`（以 **用例管理 cases** 为第一个落地域，可运行、可单测）
> 本文档用于指导后续将其余 20+ 业务域逐步迁移到 DDD。

---

## 一、为什么还要从「四层架构」演进到 DDD？

当前四层（Router → Service → Repository → Database）解决了**代码组织**问题（职责分层、避免重复实现），
但它仍是经典的 **贫血领域模型**：

| 现状特征 | 问题 |
|---|---|
| `Repository` 直接返回 `dict`，无领域对象 | 业务概念（状态机、优先级、评审）散落在字符串里，无类型约束 |
| 业务规则散落在 `Service` / `Router` / `Repo` 三处 | 规则重复、易失一致，改一处漏一处 |
| 聚合边界不清晰，service 各自为政调用 repo | 无「事务一致性边界」，同一个用例的版本/审计/评审散落多处调用 |
| 跨领域副作用（通知/索引/审计）与主流程强耦合 | 难以扩展，改主流程易破坏次要流程 |

DDD 的核心价值不是换目录名，而是把**业务规则收拢回领域模型**，让**复杂业务可维护、可测试、可演进**。

---

## 二、目标架构：按限界上下文分包的 DDD 分层

```
app/
├── core/                      # 基础设施 / 横切关注点（保留）
├── domain/                    # ★ DDD 领域包（新增）
│   ├── common/                #   通用原语
│   │   ├── entities.py        #   Entity / AggregateRoot / Identifier
│   │   ├── value_objects.py   #   ValueObject（不可变）
│   │   ├── domain_events.py   #   DomainEvent / EventBus
│   │   └── exceptions.py      #   DomainException 家族
│   └── cases/                 #   限界上下文 #1：用例管理（试点）
│       ├── domain/            #   领域层（与存储/框架零依赖）
│       │   ├── entities/case.py        # TestCase 聚合根
│       │   ├── value_objects/          # Priority/Status/TestType/Review
│       │   ├── services/               # CaseStatePolicy 领域服务
│       │   ├── events.py               # 领域事件
│       │   ├── repository.py           # 聚合仓储接口（Port）
│       │   └── exceptions.py
│       ├── application/       #   应用层（用例编排 / 事务边界）
│       │   ├── case_app_service.py     # 应用服务门面
│       │   └── dto.py
│       └── infrastructure/    #   基础设施层（Adapter）
│           └── case_repository_impl.py # 对接既有 CaseRepo
│
├── services/                  # 现有四层 Service（长期将迁入各域的 application）
├── repositories/              # 现有四层 Repository（长期变为各域 infrastructure 的数据源）
├── models/                    # 现有 Web 请求/响应 Pydantic（作为 DTO 保留）
└── routers/                   # 现有 Web 适配层（仅做参数绑定 + 调用 application 服务）
```

每个限界上下文内部遵循 **严格的依赖方向**（外层依赖内层，方向向内）：

```
      Web 层（routers）
            │
            ▼
     Application（application/）——用例编排、事务边界、事件发布
            │
            ▼
       Domain（domain/）——实体/值对象/领域服务/聚合/领域事件
            │
            ▼
   Infrastructure（infrastructure/）——仓储适配器（对接 SQLite/CaseRepo）
```

**依赖铁律（架构守护）：**
- `domain/` 层 **禁止** import `FastAPI`、`sqlite`、`routers`、`services`、`repositories`。
- `domain/` 只能定义**接口（Port）**，具体实现交给 `infrastructure/`。
- `application/` 依赖 `domain/` 接口编程，可注入替身做单测。
- 跨上下文通信一律通过**领域事件**，禁止上下文之间直接 import 对方 `service`。

---

## 三、限界上下文与聚合根识别（全局地图）

依据「业务能力」对现有 20+ 域收敛成以下限界上下文与聚合：

| 限界上下文 | 聚合根 | 主要子实体 / 值对象 | 对应现有目录 |
|---|---|---|---|
| **测试用例 cases**（试点）| `TestCase` | 依赖、关联、版本、变更日志、需求关联 | `services/case_service.py` `repositories/case_repo.py` |
| **用例评审 case_review** | `CaseReview` | 关联用例(ReviewCaseLink)、评审人 | `services/case_review_service.py` `repositories/case_review_repo.py` |
| **接口测试 apitest** | `ApiDefinition` / `ApiCase` / `Scenario` / `Mock` / `Environment` | 断言、脚本、变量提取、控制器 | `services/apitest_service.py` `repositories/apitest_repo.py` |
| **缺陷 defect** | `Defect` | 复现步骤、处理记录 | `services/defect_service.py` `repositories/defect_repo.py` |
| **项目 project** | `Project` | 版本、环境、成员、应用配置 | `services/project_service.py` |
| **测试计划 test_plan** | `TestPlan` | 阶段、用例编排 | `test_plan/*` |
| **报告 report** | `Report` | 步骤、导出 | `services/report_service.py` |
| **组织/成员 identity** | `Organization` / `Member` / `Role` | 邀请、用户视图 | `auth/*` `organization*` |
| **任务运行 runs** | `Run` / `Task` | 结果、状态机 | `runs/` `tasks/` `repositories/run_repo.py` |
| **生成编排 generation** | `GenerationJob` | 生成步骤、修复循环 | `graph/` `generators/` |

> 迁移顺序建议按**业务复杂度与收益**从高到低：
> `cases`（试点，已完成）→ `defect`（已完成）→ `case_review`（已完成）→
> `test_plan`（已完成）→ `project`
> → `apitest`（最大但最规整）→ `runs/task` → `report` → `identity`。

---

## 四、试点落地：用例（cases）域的 DDD 结构

试点已把 **用例管理** 完整按 DDD 重新表达，详见 `app/domain/cases/`：

### 4.1 聚合根 `TestCase`（domain/entities/case.py）
- 内聚 `Priority / CaseStatus / TestType / CaseReview[]` 等值对象。
- **业务命令**：`rename() / change_status() / review() / delete() / restore()` 统一守护不变量，
  不允许从外部直接改字段。
- 变更即产生**领域事件**（暂存在聚合内），供提交后发布。

### 4.2 值对象（domain/value_objects/）
- `Priority`：仅允许 `P0~P3`，越界即抛领域异常。
- `CaseStatus`：自带**状态机迁移矩阵** `ALLOWED_TRANSITIONS`。
- `CaseReview`、`TestType`：类型化约束，替代字符串散落。

### 4.3 领域服务（domain/services/case_policy.py）
- `CaseStatePolicy`：把「状态迁移是否允许」「评审通过条件」抽成无状态策略，
  供聚合与应用层复用，规则单一出处。

### 4.4 领域事件（domain/events.py）
- `CaseCreated / CaseTitleChanged / CaseStatusChanged / CaseSoftDeleted /
  CaseRestored / CaseReviewed / CaseRolledBack` 等。

### 4.5 聚合仓储接口（domain/repository.py，Port）
- 以**聚合**为粒度读写（`save / update / find_by_id / soft_delete / restore`），
  而非散碎的 dict 级 CRUD。

### 4.6 应用服务（application/case_app_service.py）
- 作为**用例门面**：加载聚合 → 执行领域命令 → 保存 → 发布事件 → 驱动审计/版本/缓存副作用。
- 依赖注入仓储，测试可替换。

### 4.7 基础设施适配器（infrastructure/case_repository_impl.py）
- **防腐层**：把聚合仓储接口翻译为既有 `CaseRepo` 命令，复用已验证的存储逻辑，
  换存储只改本文件。

---


## 四-B、并行落地：缺陷（defect）域的 DDD 结构

在 cases 试点之后，**缺陷域**作为迁移顺序中的下一个高价值域，已并行补齐
完整 DDD 分层，详见 `app/domain/defects/`：

### 聚合根 `Defect`（domain/entities/defect.py）
- 内聚 `Severity`（blocker~trivial）与 `DefectStatus`（带状态机）等值对象。
- **业务命令**：`rename() / change_description() / change_severity() / assign() /
  change_status() / delete() / restore()` 统一守护不变量（标题非空、状态迁移合法、
  软删除走 delete() 而非直接置废）。

### 值对象（domain/value_objects/）
- `DefectStatus`：自带 `ALLOWED_TRANSITIONS` 状态机矩阵
  （open ⇄ in_progress → fixed → closed / wont_fix，closed/wont_fix 可重开）。
- `Severity`：仅允许 blocker/critical/major/minor/trivial，越界即抛领域异常，带排序权重。

### 领域服务 / 事件 / 仓储 / 应用 / 基础设施
- `services/defect_policy.py`：无状态生命周期策略（状态迁移合法性、终结态判断）。
- `events.py`：DefectCreated/StatusChanged/SeverityChanged/SoftDeleted/Restored 等领域事件。
- `repository.py`（Port）与 `infrastructure/defect_repository_impl.py`（防腐层，对接既有
  `DefectRepo`）。
- `application/defect_app_service.py`：`DefectAppService` 用例门面（create/get/update/
  change_status/soft_delete/restore/purge/list/list_trash/stats）。

> 落地方式与 cases 试点一致：**新增 `app/domain/defects/`，不改既有四层与对外 API**，
> 双轨并存、逐域验证再切换。

### defects 域 A→B→C 渐进落地进度

- ✅ **阶段 A**：领域/应用层就绪（`app/domain/defects/` 完整分层，`defect_app_service` 可跑、
  `tests/test_ddd_defects_domain.py` 覆盖纯领域逻辑与真实存储全链路）。
- ✅ **阶段 B/C（推进，以四层门面为兼容桥）**：既有 `defect_service` 的**核心生命周期写入口**
  `create` / `update` / `trash` / `restore` / `purge` 已改为**委托 `defect_app_service`**
  （参数经 `CreateDefectCommand` / `UpdateDefectCommand` 翻译），数据流真正经过 DDD 聚合根
  与应用服务；回收站批处理（batch_restore / batch_purge）逐条复用委托路径。
  - 聚合根 `Defect` 守护标题非空、严重程度合法、状态值合法与状态机迁移等不变量。
  - 保持既有方法签名与返回 schema 不变（经 `DefectRepo` 归一化行读回），router / 兼容路由
    及 20+ 处调用方零改动、可回滚。
  - 异常翻译：`AggregateNotFound`→`NotFoundError`(404)、`DomainValidationError`/`InvariantViolation`
    →`ValidationError`(400)，与既有 service 语义一致。
  - `CreateDefectCommand` 支持显式 `status`（兼容 `bug_add` 等以非 open 状态入库的场景）。
- 回归：`tests/test_ddd_defects_migration.py` 覆盖本次 B/C 委托的 schema 与回收站流转契约；
  既有 `tests/test_defect_repo_alignment.py` / `test_ddd_defects_domain.py` 保持绿。
- ✅ **阶段 C（旁路方法面收敛）**：`defect_service` 剩余旁路方法（评论
  list/create/update/delete_comment、auto_create_from_result、permanent_delete）收敛为对
  `defect_app_service` 的薄委托（DDD 仓储 Port / Adapter 透传既有 DefectRepo），不再直连
  `DefectRepo` 做旁路数据访问。回归见 `tests/test_ddd_defects_bypass_migration.py`。

## 四-C、并行落地：性能测试（performance）域的 DDD 结构

性能测试域对应当前 `app/performance/`（企业级性能基准引擎 benchmark/metrics/runner），
已补齐完整 DDD 分层，详见 `app/domain/performance/`：

### 聚合根 `PerformanceTest`（domain/entities/performance_test.py）
- 内聚 `PerformanceMetrics`（性能画像）、`SLOThreshold`/`SLOValidationResult`（SLO 校验）、
  `PerformanceStatus`（状态机）等值对象。
- **业务命令**：`set_target() / set_thresholds() / start() / record_result() /
  fail() / skip()` 统一守护不变量（目标名非空、状态迁移合法、终态不可重入、
  指标名须与目标一致）。

### 值对象（domain/value_objects/）
- `PerformanceStatus`：自带 `ALLOWED_TRANSITIONS` 状态机
  （pending → running → passed / failed / skipped，终态不可回退）。
- `PerformanceMetrics`：不可变性能画像，`from_timings` 聚合 / `to_dict`/`from_dict` 双向转换。
- `SLOThreshold` / `SLOValidationResult`：类型化阈值与校验结果，替代字符串散落。

### 领域服务 / 事件 / 仓储 / 应用 / 基础设施
- `services/performance_policy.py`：`PerformancePolicy` 纯领域策略——按阈值判定达标
  （`validate_slo`），并给出默认 SLO 基线（`default_slo_thresholds`）。
- `events.py`：PerformanceTestCreated/Started/Completed/Passed/Failed/Skipped 等领域事件。
- `repository.py`（Port）与 `infrastructure/performance_repository_impl.py`——
  提供 `InMemoryPerformanceRepository`（该上下文暂以进程内内存落库，可平滑迁到独立表或
  run 的 performance_report）；并提供 `EngineBenchmarkRunner`（防腐层，复用既有
  `app/performance` 引擎跑真实基准，产出领域指标）。
- `application/performance_app_service.py`：`PerformanceAppService` 用例门面
  （create/get/start/record_result/fail/skip/delete/list/configure_thresholds/run）。

> 落地方式与 cases/defects 一致：**新增 `app/domain/performance/`，不改既有四层与对外 API**，
> 双轨并存、逐域验证再切换。

## 四-C、并行落地：用例评审（case_review）域的 DDD 结构

在 defects 域之后，**用例评审域**作为独立限界上下文补齐完整 DDD 分层，
详见 `app/domain/case_review/`：

### 聚合根 `CaseReview`（domain/entities/case_review.py）
- 评审会话（Review Header）聚合根：承载 名称/状态/模块/项目/通过规则/评审人/标签。
- **内聚子实体**：`ReviewCaseLink`（关联的用例 + 评审结论 + 评审人/意见）。
- **业务命令**：`rename() / change_status() / change_module() / set_reviewers() /
  link_cases() / unlink_cases() / update_link_result() / delete()` 统一守护不变量
  （名称非空、状态迁移合法、已删除评审不可关联用例、未关联用例不可评审）。

### 值对象（domain/value_objects/）
- `ReviewStatus`：评审会话状态机（PREPARED → UNDERWAY ⇄ COMPLETED）。
- `CaseReviewResult`：单个用例的评审结论（UN_REVIEWED / UNDER_REVIEWED / PASS /
  UN_PASS / RE_REVIEWED），自带 `is_reviewed` 判断。
- `ReviewPassRule`：通过规则（SINGLE / ALL）。

### 领域服务 / 事件 / 仓储 / 应用 / 基础设施
- `services/case_review_policy.py`：无状态策略（状态迁移合法性、自动完成判断）。
- `events.py`：CaseReviewCreated/Updated/StatusChanged/Deleted/Copied/
  Linked/Unlinked/ResultUpdated/FollowToggled 等领域事件。
- `repository.py`（Port）与 `infrastructure/case_review_repository_impl.py`
  （防腐层，对接既有 `CaseReviewRepo`）。
- `application/case_review_app_service.py`：`CaseReviewAppService` 用例门面
  （create/get/detail/update/soft_delete/copy/link_cases/unlink_cases/
  update_link_result/toggle_follow/list/get_status_counts/count_by_module）。

> 落地方式与前两域一致：**新增 `app/domain/case_review/`，不改既有四层与对外 API**，
> 双轨并存、逐域验证再切换。

## 四-D、并行落地：测试计划（test_plan）域的 DDD 结构

在 defect 之后，**测试计划域**作为迁移顺序中的下一高价值域，已并行补齐
完整 DDD 分层，详见 `app/domain/test_plan/`：

### 聚合根 `TestPlan`（domain/entities/test_plan.py）
- 内聚 `Priority`（P0~P3，默认 P2）与 `PlanStatus`（带状态机）等值对象，
  并将"关联用例"（PlanCase[]）作为聚合内值对象托管。
- **业务命令**：`rename() / change_description() / change_priority() /
  change_status() / archive() / set_threshold() / set_tags() / toggle_features() /
  add_case() / remove_case() / update_case_status() / reorder_cases()`
  统一守护不变量（名称非空、优先级/状态合法、状态机迁移、归档规则、通过阈值
  0~100、用例重复添加规则等）。

### 值对象（domain/value_objects/）
- `Priority`：仅允许 P0~P3，越界即抛领域异常，带排序权重。
- `PlanStatus`：自带 `ALLOWED_TRANSITIONS` 状态机矩阵
  （prepared → running → completed，completed 可重开回 running；`archived`
  为归档终态标记，仅由 `archive()` 进入、不可直接回退）。
- `PlanType`：TEST_PLAN / GROUP；`CaseType`：functional / api / scenario（含别名兼容）。
- `CaseExecutionStatus`：pending / passed / failed / blocked。
- `PlanCase`：聚合内关联用例值对象（记录用例来源、类型、执行状态与排序位置）。

### 领域服务 / 事件 / 仓储 / 应用 / 基础设施
- `services/test_plan_policy.py`：无状态生命周期策略（状态迁移合法性、终结态判断）。
- `events.py`：TestPlanCreated/Updated/StatusChanged/Archived/Deleted/
  CaseAdded/CaseRemoved/CaseStatusChanged/CaseReordered 等领域事件。
- `repository.py`（Port）与 `infrastructure/test_plan_repository_impl.py`
  （防腐层，计划主体行对接 `TestPlanRepo`，关联用例以直连 SQL 同步到
  `test_plan_cases` 表以保留聚合侧 rel_id 与排序）。
- `application/test_plan_app_service.py`：`TestPlanAppService` 用例门面
  （create/get/update/change_status/archive/delete/list/add_case/remove_case/
  update_case_status/reorder_cases/statistics）。

> 落地方式与 cases/defects 一致：**新增 `app/domain/test_plan/`，不改既有四层与
> 对外 API**，双轨并存、逐域验证再切换。

### test_plan 域迁移（阶段 A→B→C）落地登记

在 test_plan DDD 就绪（阶段 A）后，已按 §五"渐进式、可回滚"推进计划聚合生命周期的
**B/C 接入**（`app/services/test_plan_service.py`）：

- **阶段 B（接入）**：计划聚合生命周期写路径 `create / get / delete / archive`
  与统计委托 `TestPlanAppService`（经 `CreatePlanCommand` 等 DTO 编排），让 DDD
  聚合进入既有 `test_plan_service` 调用链。
- **DTO/契约桥**：`TestPlanService._to_legacy` 把 DDD 聚合输出补全为既有
  `_plan_from_row` 行结构（metadata / execution_rate / pass_rate），保证 router
  与 `_to_plan` 等下游读取契约不变。
- **阶段 C（瘦身 + 规则下沉）**：门面核心方法变薄为 DDD 委托；名称非空、优先级/状态
  合法、归档状态机等不变量由 `TestPlan` 聚合根统一守护（空名创建直接抛领域异常）。
- **只读列表委托 DDD**：`list_plans` / `count_plans` 已委托 `TestPlanAppService.list`
  （经 `PlanListQuery` 翻译，含 `module_ids` 过滤穿透）；DDD 仓储协议与防腐层补齐
  `module_ids` 参数，返回行经 `_to_legacy` 契约桥补全 metadata/execution_rate/pass_rate。
- **仍双轨并存（旁路）**：计划头通用编辑 update（含 metadata / execution_rate /
  pass_rate 等应用层专有列）、模块树、关联用例存储级编排、定时任务、
  dashboard 布局保留直连 `TestPlanRepo`，不做破坏性收紧，可回滚。
- **回归**：`tests/test_ddd_test_plan_migration.py`（接入/契约/规则下沉）+
  `tests/test_test_plan.py` + `tests/test_ddd_test_plan_domain.py` 全绿。


## 四-E、并行落地：接口测试（apitest）域的 DDD 结构

在 cases/defect 落地之后，**接口测试域**已补齐完整 DDD 分层，详见
`app/domain/apitest/`：

### 聚合根（domain/entities/）
- `ApiDefinition`（domain/entities/api_definition.py）：接口定义聚合，内聚
  `Protocol`（HTTP/TCP/SQL/DUBBO）等值对象，守护名称非空、请求方法等不变量；
  支持 rename/set_content/delete/restore 业务命令，软删除走 delete()。
- `ApiCase`（domain/entities/api_case.py）：接口用例聚合，内聚
  `ApiCaseStatus`（draft/active/deprecated 带状态机）与 `Priority`（P0~P3），
  请求内容/断言/脚本/变量提取/逻辑控制器均内聚在聚合内统一更新；
  set_content/change_status/delete/restore 等业务命令守护不变量。
- `Scenario`（domain/entities/scenario.py）：接口场景聚合，内聚
  `ScenarioStatus` 状态机，set_steps/change_status/delete/restore 守护步骤与状态。

### 值对象（domain/value_objects/）
- `Protocol`：HTTP/HTTPS/TCP/SQL/DUBBO 协议类型守卫。
- `Priority`：仅允许 P0~P3（复用用例域同类设计）。
- `ApiCaseStatus` / `ScenarioStatus`：各自带 ALLOWED_TRANSITIONS 状态机矩阵。

### 领域服务 / 事件 / 仓储 / 应用 / 基础设施
- `services/apitest_policy.py`：`ApiStatePolicy` 无状态状态机策略。
- `events.py`：ApiDefinitionCreated/Renamed/SoftDeleted 与 ApiCase/Scenario 对应事件族。
- `repository.py`（Port）：`ApiDefinitionRepository` / `ApiCaseRepository` /
  `ScenarioRepository` 三个协议。
- `infrastructure/apitest_repository_impl.py`（防腐层）：三个适配器对接既有 `ApitestRepo`。
- `application/apitest_app_service.py`：`ApitestAppService` 用例门面（create/get/
  update/delete/restore/list 全链路）。

> 落地方式与 cases/defects 一致：**新增 `app/domain/apitest/`，不改既有四层与对外
> API**，双轨并存、逐域验证再切换。

> **A→B→C 渐进迁移（已完成 + Round 1 旁路收敛）**：上述接口测试（apitest）域在阶段 A
> （领域/应用层就绪）基础上已推进到阶段 B/C ——
> - **阶段 B**：`app/routers/*` 经 `apitest_service`（薄门面）到达
>   `apitest_app_service`，完成 Router→应用门面→聚合 的 DDD 路由；
> - **阶段 C（Round 1 旁路收敛）**：新增 Web 适配层
>   `app/domain/apitest/application/apitest_web.py`（DTO 翻译 + 契约保真），
>   `ApitestService` 的 定义/用例/场景 对象级 CRUD 与 **列表/回收站计数/
>   批量删除-恢复/版本** 等旁路方法已收敛为对 `apitest_web` → `apitest_app_service`
>   （DDD 门面）的**薄委托**，Service 仅做方法签名兼容与转发。业务规则
>   （名称非空、状态机、软删/恢复守卫）下沉至聚合。
>   - DDD 列表/回收站查询支持 `protocols` / `module_ids` / `api_definition_id`
>     过滤透传，回收站 total 以真实 COUNT 为准。
>   - 状态值对象新增 `approved`（legacy 兼容）以支持存量数据读取。
>   - **module_tree / execution（含 execution_logs）/ followers /
>     operation_logs / schedules 旁路组**已收敛为对
>     `apitest_app_service`（DDD 门面）的薄委托，Service 仅做签名兼容转发、
>     不再直连 `ApitestRepo`，Router/compat 调用方零改动、可回滚。
> - **阶段 C（Round 3）**：定义/用例/场景的 **回收站 purge（物理删除）、
>   batch_purge、batch_update、rollback_definition** 与 **module stats**
>   （count_definitions_by_module / count_definitions_total /
>   count_cases_for_definition / count_modules），以及 Mock 的 purge / batch_purge，
>   已收敛为对 `apitest_web` → `apitest_app_service`（DDD 门面）的薄委托，
>   复用 `purge_by_repo` / `batch_op_by_repo` 薄门面，对外契约零变化、可回滚。
> - **阶段 C（Round 4 · 本批）**：**mocks（ApiMock 聚合）** 与 **environments /
>   env_groups / global_params**（apitest 侧 api_environments 配置，route 不建模）
>   已收敛为对 `apitest_web` → `apitest_app_service`（DDD 门面）的薄委托，
>   Service 仅做方法签名兼容与转发；回收站列表-计数、恢复-清除、批量删除-恢复-清除
>   与 running / export / import、`env_detail_to_frontend` 契约桥同步收口。
>   - 仍属双轨并存的旁路（dashboard_stats、mgmt_*）保留直连 ApitestRepo。
> - 配套回归：`tests/test_ddd_apitest_migration_service.py` +
>   `tests/test_ddd_apitest_surface.py` + `tests/test_ddd_apitest_mock_aggregate.py` +
>   `tests/test_ddd_apitest_purge_surface.py` +
>   `tests/test_ddd_apitest_env_bypass.py` +
>   `tests/test_ddd_apitest_bypass_surface.py`。

## 四-F、生成编排（generation）域的 DDD 结构与迁移三步

生成编排域对应当前 `graph/` `generators/` 的测试生成执行链路。核心聚合为
`GenerationJob`（生成步骤 `GenerationStep[]` / 修复轮 `FixLoop[]`），阶段 A
已补齐完整 DDD 分层，详见 `app/domain/generation/`：

### 聚合根 `GenerationJob`（domain/entities/generation_job.py）
- 内聚 `GenerationStatus` / `GenerationTestType` / `JobSource` / `CoverageGate`
  值对象。
- **业务命令**：`confirm_created() / start() / record_step() /
  record_test_failure() / do_retry() / set_artifacts() / succeed() / fail() /
  cancel()` 统一守护不变量——file_path 非空、状态机（pending → running →
  succeeded/failed/cancelled）、修复轮与 retry_count 推进、终态不可再流转。

### 值对象 / 领域服务
- `GenerationStatus`：自带 `ALLOWED_TRANSITIONS` 状态机矩阵；
  `GenerationTestType` / `JobSource` / `CoverageGate` 类型化守卫替代字符串散落。
- `services/generation_policy.py`：`GenerationPolicy` 纯领域策略——状态迁移合法性判定。

### 领域服务 / 事件 / 仓储 / 应用 / 基础设施
- `events.py`：GenerationJobCreated/Started/StepCompleted/Retried/Succeeded/
  Failed/Cancelled 等领域事件。
- `repository.py`（Port）与 `infrastructure/generation_repository_impl.py`
  （防腐层，对接既有 `RunRepo`，落库到 run_records，status/steps/fix_loops 收敛进
  metadata JSON 完整持久化）。
- `application/generation_app_service.py`：`GenerationAppService` 用例门面
  （submit/get/start/record_step/update_artifacts/retry/finalize/cancel/delete/
  list_jobs/stats）。

### A→B→C 渐进迁移（generation 特有约束）
- **阶段 A（已落地）**：领域/应用/基础设施就绪 + 单测 `test_ddd_generation_domain.py`。
- **B 前置 · DTO 契约桥**：`application/web_contract.py` 提供聚合 ↔ run_records
  扁平行双向无损翻译，保证 DDD 落库与既有 `run_service.save` 写入**逐字段契约等价**
  （扁平列一致、passed 正确、派生态进 metadata），使生成来源记录可由 `/api/runs` 与
  报告兼容层零感知读取；见 `test_ddd_generation_migration.py`。
- **B · 接入**：生成来源记录落库收敛为对 `GenerationAppService` 生命周期的委托，
  WS/task/结构化生成等旁路保持走 `run_service`，互不阻塞、可回滚。
- **C · 规则下沉 + 回归**：状态机/修复轮/收口规则由领域层守护，Service 变薄。

> 落地方式与其余域一致：**新增 `app/domain/generation/`，不改既有四层与对外 API**，
> 双轨并存、逐域验证再切换。

## 五、试点迁移的改动方式（本次已交付）

试点**以新增 `app/domain/` 方式交付**，不破坏既有四层代码：

1. 新增 `app/domain/common/`（DDD 通用原语）。
2. 新增 `app/domain/cases/`（用例限界上下文完整 DDD 分层）。
3. `infrastructure` 复用既有 `CaseRepo` 作数据源（无表结构变更、无路由改动）。
4. 配套单测：`tests/test_ddd_cases_domain.py`（纯领域 + 全链路仓储）。

> 接入策略（渐进、可回滚）：
> - **阶段 A**：领域/应用层就绪，可用新门面 `case_app_service` 替代 router 对 service 的调用。
> - **阶段 B**：router 改为调用 `case_app_service`（参数经 DTO 翻译）。
> - **阶段 C**：将 `services/case_service.py` 中业务规则下沉到领域层，Service 变薄或移除。
> 每域可独立执行 A→B→C，互不阻塞。

### cases 域 A→B→C 渐进落地进度

- ✅ **阶段 A**：领域/应用层就绪（`app/domain/cases/` 完整分层，`case_app_service` 可跑、有单测）。
- ✅ **阶段 B（推进，以四层门面为兼容桥）**：既有 `case_service` 的**核心生命周期写入口**
  `create` / `soft_delete` / `restore` 已改为**委托 `case_app_service`**（参数经 `CreateCaseCommand`
  / `DeleteCaseCommand` / `RestoreCaseCommand` 翻译），数据流真正经过 DDD 聚合根与应用服务。
  - 保持既有方法签名与返回 schema 不变，router 及 15+ 处调用方零改动、可回滚。
  - `CreateCaseCommand` 支持显式 `status`（兼容 `generation` 等以 `review` 状态入库的场景）。
- ✅ **阶段 B 续（读路径与核心生命周期委托）**：`get`/`update`/`list`/`list_cases`/`count_cases`
  已改为**委托 `case_app_service`**（参数经 `GetCase` / `UpdateCaseCommand` / `ListQuery` 翻译）：
  - `TestCase` 聚合补齐 `last_result` 持久化 round-trip（from_dict→to_dict），
    `CaseRepo` create/update 支持 dict `last_result` 自动 JSON 序列化。
  - `TestCase.change_test_type()` 同步 metadata.test_type，避免顶层与 metadata 字段漂移。
  - `UpdateCaseCommand` 增 `metadata`/`status`：metadata 支持 dict/JSON-string 两态兼容；
    `status` 走 DDD 状态机合法迁移（非法迁移/废弃态拒绝均抛领域异常转 ValueError）。
  - `case_service.update()` 对不存在用例返回 None（兼容旧语义），Ddd 应用服务
    内部 `_find_or_raise` 捕获 AggregateNotFound。
  - `case_repository_impl.update()` 不再向 CaseRepo 传顶层 test_type（已在 metadata 同步），
    避免 CaseRepo.update 用旧顶层值覆盖新 metadata 的 test_type。
- ✅ **防腐层容错**：`TestCase.from_dict` 对历史脏数据（非法 `test_type`/`status`/`priority`，
  如导入脑图把节点 id 误写入 `test_type`）回退默认值，保证 DDD 读路径可安全承载既有真实库。
- ✅ **阶段 B 续·只读列表委托**：`case_service` 的 `list` / `list_cases` /
  `count_cases` 已委托 `case_app_service.list_cases`（参数经 `ListQuery` 翻译），
  并修复 DDD 防腐层 `module_id` 过滤透传；`TestCase` 实体补齐 `last_result`
  持久化/读回（`to_dict` / `from_dict`），解决领域视图 schema 差异。
- ✅ **阶段 B 续（评审）**：`case_service` 评审方法（submit_review/approve_review/reject_review）
  已委托 DDD `case_app_service`——聚合根 `TestCase` 状态机守护草稿→评审中→通过/驳回迁移；
  DDD infrastructure 补齐 `case_reviews` 管理表持久化能力（submit_review_record /
  approve_review_record / reject_review_record），service 门面回读旧 schema 兼容。
- ✅ **阶段 C 续（relations/dependencies/import/export 已委托）**：`case_service`
  关联（add_relation/remove_relation/list_relations）、依赖（add_dependency/
  remove_dependency/list_dependencies）与导入导出（import_excel/import_mindmap/
  export_excel/export_mindmap）已委托 DDD `case_app_service`，参数透传至既有
  CaseRepo 关联/依赖表及格式工具。Review 流、relations、dependencies、
  import/export 等旁路方法已全量收敛（versions/export-task 等协调能力由
  对应协调域承载）。
- 回归：`tests/test_ddd_cases_migration.py` 覆盖本次 B/C 委托的 schema 与回收站流转契约；
  既有 `tests/test_cases_api_full.py` / `test_ddd_cases_domain.py` 等保持绿。
- 回归：`tests/test_ddd_cases_import_export_migration.py` 覆盖 import/export 薄委托
  零回归（字节/结构契约经 DDD 门面端到端一致）。

### 阶段 B/C 落地方案（用例评审 case_review 已应用）
对"骨架就绪、双轨并存"的域，让既有调用链真正消费 DDD，遵循**契约安全**三步：
- **① DTO 契约桥**：在 `application/` 增 `web_dto.py`，把 DDD 聚合视图
  `CaseReview.to_dict()` 翻译回 Repo header 契约（`reviewers_json`/时间等），
  保证返回给上层 schema 与迁移前一致、零回归。
- **② Service 委托接入**：`services/case_review_service.py` 核心生命周期方法
  （create/update/delete/copy/link/unlink/update_link_result）改为委托
  `case_review_app_service`（`case_review_app_service` 单例），参数经命令 DTO；
  纯排序 `pos` 与模块树/人员下拉等超出聚合范围的逻辑仍在 Service 直连 Repo。
- **③ 规则下沉 + 回归**：名称必填、状态机、软删去重、未关联用例不可评审等
  不变量由聚合根守护并落地既有路径；补 `tests/test_case_review_ddd_migration.py`
  迁移回归测试；router 与对外 API 均不动。

> 结论：**router 不动、对外 API 不动**，仅 Service 变薄并让 DDD 聚合成为
> 核心生命周期引擎，可独立验证、可回滚。

---

## 六、落地 Checklist（把其余域迁移到 DDD）

对每个业务域执行：

- [ ] 1. 圈定**限界上下文**与**聚合根**，画出聚合边界与内部组成。
- [ ] 2. 建 `app/domain/{ctx}/domain/`：把散落的常量/状态机收拢为**值对象 + 实体 + 领域服务**。
- [ ] 3. 识别**聚合内事务一致**的子实体（如用例的评审/版本），归入聚合根管辖。
- [ ] 4. 定义 `repository.py`（Port），返回**聚合对象**而非 dict。
- [ ] 5. 建 `infrastructure/` 适配器，对接既有 `repositories/*_repo.py`（防腐层）。
- [ ] 6. 建 `application/*_app_service.py`，承载用例编排与事务边界。
- [ ] 7. 建 `domain/events.py` 领域事件，把通知/索引/审计等副作用解耦成订阅者。
- [ ] 8. Router 改为调用应用服务；Service 层变薄直至收敛。
- [ ] 9. 保留 Web 层 Pydantic（`models/`）作 DTO，不改对外 API。
- [ ] 10. 为**纯领域规则**补单测（无 DB、毫秒级、可读）。

---

## 七、测试策略

| 测试类型 | 针对层 | 示例 |
|---|---|---|
| 领域单测 | domain（纯逻辑）| 状态机非法迁移、优先级越界、评审状态流转 |
| 仓储集成 | infrastructure | 聚合 save/load 往返、软删除/恢复 |
| 应用层单测 | application（注入替身仓储）| 编排顺序、事件发布、副作用触发 |
| 契约/回归 | router + 全栈 | 既有 `tests/test_cases*` 保持绿，保证无回归 |

---

## 八、收益与风险

**收益**
- 业务规则单一来源、类型化，杜绝字符串魔法与三处重复。
- 聚合根守护不变量，改状态/删除/评审不会漏校验。
- 领域事件解耦跨域副作用，新增「通知」「索引」不动主流程。
- 每域可独立演进，逐步收敛风险。

**风险与对策**
- 工作量大 → 采用试点 + 分批迁移，先搬高收益低风险域。
- 既有 20+ 域同步改造破坏面大 → 本方案以新增 DDD 层 + 适配既有仓储方式，
  单域改造不触碰其他域代码，逐域验证再切换。
- 贫血模型遗留调用 → 阶段 A/B 双轨并存，切完一个删一个。

---

## 附：本次试点文件清单

```
app/domain/common/                  # DDD 通用原语
app/domain/cases/*                  # 用例域 DDD（试点一）
app/domain/defects/*                # 缺陷域 DDD（并行落地）
app/domain/case_review/*            # 用例评审域 DDD（并行落地）
app/domain/test_plan/*              # 测试计划域 DDD（并行落地）
app/domain/apitest/*                # 接口测试域 DDD（并行落地）
tests/test_ddd_cases_domain.py      # 用例领域/链路单测
tests/test_ddd_defects_domain.py    # 缺陷领域/链路单测
tests/test_ddd_case_review_domain.py  # 用例评审领域/链路单测
tests/test_ddd_test_plan_domain.py  # 测试计划领域/链路单测
tests/test_ddd_apitest_domain.py    # 接口测试领域/链路单测

docs/ddd-architecture-refactoring-plan.md  # 本文档
```

---

## 四-C、通用支撑域（Generic Subdomain）：身份与访问 / 共享内核

在 cases / defect 核心域落地之后，**通用支撑域**以更低复杂度、更高复用性为
目标落地，原则是：**不引入重型状态机，仅把高频跨域共享概念收拢为聚合 + 强类型
值对象 + 防腐层适配器**，保持与既有四层 API 双轨并存、零破坏。

### #11 身份与访问域（IdentityAndAccess）→ `app/domain/identity/`

聚合根与子实体：
- `User`（账号：可用状态 AccountStatus + ApiKey[] 子实体）
- `Organization`（租户：名称/状态 + Member[] 子实体 + 越权守卫）
- `Role`（用户组/角色：权限集合 PermissionSet + 内置角色保护）
- `Invitation`（邀请：有效期/已用状态机）

关键不变量：
- 组织至少保留一名所有者；角色无法管理比自己权限更高的成员。
- 内置角色（internal）不可删除；账号停用即禁登录。
- 邀请未使用且未过期才能用于注册。

对应既有：`repositories/auth_repo.py` `repositories/organization_repo.py`
`repositories/user_group_repo.py` `repositories/invitation_repo.py`（防腐层适配）。

#### 迁移三步（A→B→C 渐进式）—— 第 1 步 DTO 契约桥（已落地）

身份域是通用支撑域：认证/组织/角色/邀请被邀请注册、组织-项目绑定、成员
权限等**复合流程**深度复用，且 `AuthRepo._row_to_user` 返回 DB 行 schema
（`enable`/`create_time`/`deleted` 等），与 DDD 聚合 `to_dict()`（
`status`/`created_at`/`api_keys`）不一致——没有独立、干净的 CRUD 路由可
整段切换。因此按 §五 A→B→C 渐进，先落地 **DTO 契约桥**（B 前置）：

- `app/domain/identity/application/web_schema.py`：把 `IdentityAppService` /
  聚合输出翻译回既有 Web 行 schema（超集，含只读增强字段），保证后续
  `auth_service`/`organization_service` 门面切到 DDD 时不破坏前端 / 既有单测。
- `tests/test_ddd_identity_web_bridge.py`：契约桥对齐单测（6 项，零回归）。
- 状态：**阶段 A + DTO 桥 + 阶段 C（Service 门面收敛）**。已完成：
  - 第 1 步 DTO 契约桥（web_schema.py）。
  - 第 2 步 Service 委托守卫（delegation.py）。
  - 第 3 步 `services/auth_service.py`：用户核心生命周期（注册 create_user /
    更新 update_user / 启停 set_user_enabled / 改密 change_password /
    重置 reset_password）与角色管理（create_group / update_group /
    delete_group → create_role / update_role / delete_role）委托 DDD，内置
    角色保护 / 邮箱格式 / 账号状态机由领域聚合守护；
    `services/organization_service.py`：组织 CRUD（create/get/list/rename/
    update/enable/disable）与成员增删改（add/update/remove_member）委托 DDD，
    owner 越权守卫 / 唯一 owner 保护由领域聚合守护。
  - 配套（main 已含）：`services/invitation_service.py` 收敛为 DDD 薄门面。
  返回经既有 Repo / `web_schema` 读回归一化，对外 schema 与迁移前零变化（可回滚）。

### #12 基础设施与共享内核（Infrastructure & Shared Kernel）→ `app/domain/runs/`

以异步任务队列（TaskCenter / Run）为核心聚合：
- `Task`（任务：TaskStatus 生命周期状态机 pending→running→success/failed/cancelled，
  失败可重跑 requeue）
- 事件：TaskCreated / Started / Succeeded / Failed / Cancelled / Requeued

对应既有：`app/tasks/` `app/repositories/task_repo.py` `app/core/task_enums.py`。

> 说明：共享内核原语（Entity / AggregateRoot / ValueObject / DomainEvent / 异常）
> 沉淀于 `app/domain/common/`；其余跨域支撑（环境/资源池/报告导出/文件/通知）
> 可在后续按同一"支撑域轻落地"策略逐个收敛，本批先落地 TaskCenter 这一最核心
> 共享内核切面。

#### 运行记录 / 报告补充（RunRecord 聚合）

在 TaskCenter 之上，runs 域进一步补齐 `run_service` 对应的**运行记录（RunRecord /
报告）**通用能力，详见 `app/domain/runs/` 下新增：

- 聚合根 `RunRecord`（domain/entities/run_record.py）：一次测试运行/生成的完整快照，
  派生 `passed`（以 `test_result.passed` 为唯一口径），`file_path` 充当报告名
  （rename 语义 + 非空守卫）。
- 值对象 `RunSource`（domain/value_objects/run_source.py）：来源 single/project/
  websocket/task 合法性守卫。
- 领域策略 `RunRecordPolicy`（domain/services/run_record_policy.py）：报告名非空、
  来源过滤口径。
- 事件：RunRecordSaved / Renamed / Deleted / BatchDeleted / Cleared。
- 仓储接口 `RunRecordRepository`（domain/repository.py，Port）。
- 应用服务 `RunRecordAppService`（application/run_record_app_service.py）：save /
  update / rename / get / list / count / stats / delete / delete_batch / clear。
- 基础设施防腐层 `RunRecordRepoAdapter`（infrastructure/run_record_repository_impl.py，
  对接既有 `RunRepo` / run_records）。

`run_service` 收敛为 runs 域 DDD **薄门面**（委托 `RunRecordAppService`，保留历史
签名与返回形状——passed 仍归一为 0/1），/api/runs 与报告兼容层零感知、可回滚。
与 generation 域 `GenerationJob`（带状态机的高阶视图）共享同一 run_records 底层
存储，本聚合为更底层的通用运行记录读/写视角，互不冲突。回归见
`tests/test_ddd_runs_record_domain.py`。

## 附：本批（通用支撑域）文件清单

```
app/domain/identity/*                   # 身份与访问域 DDD
app/domain/runs/*                       # 任务运行 / TaskCenter DDD（共享内核）
tests/test_ddd_identity_domain.py       # 身份域纯领域 + 应用服务单测
tests/test_ddd_runs_domain.py           # TaskCenter 纯领域 + 应用服务单测
docs/ddd-architecture-refactoring-plan.md  # 本文档
```

---

## 四-D、报告产物（report）域的 DDD 结构

报告产物域对应当前 `app/services/report_service.py` `app/repositories/report_repo.py`
（报告中心：汇总用例快照导出 HTML/JUnit/Markdown，并对报告文件做列表/回收站管理），
已补齐完整 DDD 分层，详见 `app/domain/report/`：

### 聚合根 `Report`（domain/entities/report.py）
- 代表一份**报告产物文件制品**，内聚 `ReportFormat` / `ReportState` / 汇总摘要值对象。
- **业务命令**：`trash() / restore() / mark_purged()` 守护回收站生命周期不变量
  （active ⇄ trash → purged），非法状态迁移抛领域异常。

### 值对象（domain/value_objects/）
- `ReportFormat`：仅允许 html/junit/markdown，越界抛领域异常。
- `ReportState`：产物状态机 active ⇄ trash，purged 为物理删除终态。

### 领域服务 / 事件 / 仓储 / 应用 / 基础设施
- `services/report_policy.py`：`ReportLifecyclePolicy` 生命周期策略 + 汇总/行口径
  纯策略（`compute_summary` / `build_result_rows`），口径单一出处。
- `events.py`：ReportGenerated/Trashed/Restored/Purged 等领域事件。
- `repository.py`（Port）与 `infrastructure/report_repository_impl.py`
  （防腐层，复用既有 `ReportRepo` 的文件生成/回收站语义）。
- `application/report_app_service.py`：`ReportAppService` 用例门面
  （generate/list/download/trash/list_trash/restore/purge）。

> 落地方式与其余域一致：**新增 `app/domain/report/`，不改既有四层与对外 API**，
> 双轨并存、逐域验证再切换。

> 报告域已完成 **A→B→C 渐进接入**：
> - **阶段 B**：`app/routers/reports.py` 改调 `report_app_service`（参数经应用层
>   DTO 翻译，领域异常薄映射为既有 HTTP 状态码），对外 Web 契约与重构前一致。
> - **阶段 C**：`app/services/report_service.py` 收敛为 DDD **薄门面**（委托
>   `report_app_service`，保留历史签名以兼容/回滚）；格式守卫、状态机、汇总口径
>   均由领域层单一守护。

## 附：报告（report）域文件清单

```
app/domain/report/*                     # 报告产物域 DDD
app/routers/reports.py                  # router 接入 DDD（阶段 B）
app/services/report_service.py          # 四层 Service 薄门面委托 DDD（阶段 C）
tests/test_ddd_report_domain.py         # 报告域纯领域 + 应用服务 + 迁移回归单测
docs/ddd-architecture-refactoring-plan.md  # 本文档
```

## 四-E、通用支撑域补齐：环境/文件/消息/脚本/模板

在核心业务域落地之后，**通用支撑域**继续按"支撑域轻落地、双轨并存、零破坏"策略
收敛五个高频跨域支撑模块，详见各自 DDD 分层：

### #15 环境管理（environment）→ `app/domain/environment/`

聚合根 `Environment`：环境资源配置与生命周期状态机。
- **值对象**：`EnvStatus`（offline ⇄ launching → online / error / maintenance）、
  `AlertLevel`（info/warning/critical）。
- **业务命令**：`rename / update_meta / change_status` 守护状态机迁移与名称非空不变量。
- **领域事件**：EnvironmentCreated / Updated / StatusChanged / Trashed / Restored。
- **仓储 Port + Adapter**：复用既有 `EnvironmentRepo` 做防腐层。
- **应用服务** `EnvironmentAppService`：create / get / list / update / change_status /
  delete / trash / restore / purge / list_alerts / resolve_alert / get_stats，
  并提供 before_launch / after_launch_success / after_launch_error 供 Docker 运维编排调用。

> **迁移落地（阶段 A→B→C 渐进式）**：DDD 就绪后，`app/services/environment_service.py`
> 的纯 CRUD / 回收站 / 告警已收敛为对 `environment_app_service` 的**薄委托门面**（阶段 C）；
> Router 经薄门面到达 DDD 门面 → 聚合（阶段 B）。Docker 拉起/停止/健康检查副作用保留在
> Service，状态流转经 DDD 生命周期钩子守护；同步修复 `delete()` 在已 offline 环境上的
> 自环非法迁移。回归：`tests/test_ddd_environment_migration.py`。

### #16 文件管理（file）→ `app/domain/file/`

聚合根 `FileItem`：项目文件制品的元数据聚合。
- **值对象**：`FileName`（净化文件名阻断路径穿越）、`FileType`（IMAGE/DOC/XLS/JAR/CONFIG/FILE）。
- **业务命令**：`move_module / update_meta / mark_deleted`。
- **领域事件**：FileUploaded / FileDeleted / FileMetaUpdated。
- **仓储 Port + Adapter**：复用既有 `FileRepo`（元数据）做防腐层。
- **应用服务** `FileAppService`：save_file / list_files / get_file / delete_file /
  delete_batch / count_by_module / update_meta。

> **迁移落地（阶段 A→B→C 渐进式，双轨并存）**：DDD 就绪后，`app/services/file_service.py`
> 的**落盘写路径** save_file / delete_file / delete_files_batch / update_meta 已委托
> `file_app_service`（阶段 C）；Router 经薄 Service → DDD 门面 → 聚合完成上传/删除（阶段 B）。
> 项目文件列表/附件等富 schema 视图仍保留在 Service（DDD 未完全复刻，双轨并存零破坏）。
> 同步修复 DDD `FileItem` 默认 file_type 恒为 FILE 致扩展名自动识别失效的缺陷。
> 回归：`tests/test_ddd_file_migration.py`。

### #17 消息通知（message）→ `app/domain/message/`

聚合根：`Robot`（消息机器人）与 `Notification`（站内通知）。
- **值对象**：`NotificationStatus`（UNREAD → READ）、`RobotPlatform`。
- **业务命令**：`Robot.update_meta / set_enable`、`Notification.mark_read`（幂等）。
- **领域事件**：RobotCreated / Updated / Deleted / EnabledChanged / NotificationCreated / Read。
- **仓储 Port + Adapter**：复用既有 `MessageRepo`（project_robots / message_tasks / notifications）。
- **应用服务** `MessageAppService`：机器人 CRUD/启停、消息设置配置树构建、通知
  创建/列表/已读/未读数。

> **迁移落地（阶段 A→B→C 渐进式，双轨并存）**：DDD 就绪后，`app/services/message_service.py`
> 的机器人 CRUD/启停与站内通知（list/unread/set_read/set_read_all）已委托
> `message_app_service`（阶段 C）；Router 经薄 Service → DDD 门面 → 聚合完成机器人/通知读写（阶段 B）。
> 消息设置树/接收人/模板详情等富 schema 视图仍保留在 Service（双轨并存零破坏）。
> 回归：`tests/test_ddd_message_migration.py`。

### #18 脚本健康度（script）→ `app/domain/script/`

聚合根 `Script`：UI 测试脚本健康度与执行监控。
- **值对象**：`ScriptStatus`（healthy ⇄ unstable ⇄ degraded）、`ScriptFramework`。
- **领域策略** `script_policy`：`calc_health_score` / `determine_status` 纯计算。
- **业务命令**：`update_meta / record_execution / auto_repair`。
- **领域事件**：ScriptRegistered / Updated / Deleted / ExecutionRecorded / AutoRepaired。
- **仓储 Port + Adapter**：复用既有 `ScriptRepo` 做防腐层。
- **应用服务** `ScriptAppService`：register / get / list / update / delete /
  record_execution / auto_repair / list_executions / evaluate_selector / recommend_strategy。

> **迁移落地（阶段 A→B→C 渐进式）**：DDD 就绪后，`app/services/script_service.py`
> 已收敛为对 `script_app_service` 的**薄委托门面**（阶段 C）；Router 经薄门面到达
> DDD 门面 → 聚合（阶段 B）。脚本 CRUD / 执行记录 / 定位器修复 / 统计全部委托 DDD，
> 缺失语义保持 404 化（get 缺失返回 None、delete 缺失返回 False），对外 API 零破坏、可回滚。
> 回归：`tests/test_ddd_script_migration.py`。

### #19 字段模板（template）→ `app/domain/template/`

聚合根 `Template`：项目/组织字段模板的元数据聚合。
- **值对象**：`TemplateScene`（FUNCTIONAL/API/UI/TEST_PLAN/BUG）、`ScopeType`（PROJECT/ORGANIZATION）。
- **业务命令**：`rename / update_meta / set_default / clear_default / mark_deleted`。
- **领域事件**：TemplateCreated / Updated / Deleted / DefaultSet。
- **仓储 Port + Adapter**：复用既有 `TemplateRepo` 做防腐层。
- **应用服务** `TemplateAppService`：list / get / save / delete / set_default
  （空范围自动播种默认模板）。

> 落地方式与其余域一致：**新增 `app/domain/{ctx}/`，不改既有四层与对外 API**，
> 双轨并存、逐域验证再切换。

### 支撑域 Service 委托（阶段 C 薄门面）

上述五个支撑域的**阶段 C 渐进接入**已完成：既有四层 Service 收敛为对 DDD
应用服务的**薄委托门面**，业务规则/不变量下沉到领域层守护，同时保持对外
方法签名与返回 schema 向后兼容：

- `app/services/script_service.py`：register/get/list/update/delete/
  record_execution/auto_repair/list_executions/evaluate_selector/
  recommend_strategy/get_stats 委托 `script_app_service`（名称非空等
  不变量由聚合根守护）。
- `app/services/template_service.py`：list/get/add/update/delete/set_default
  委托 `template_app_service`（空列表自动播种默认模板、首条自动设为默认）。
- `app/services/environment_service.py`：create/get/list/update/delete/
  trash/restore/purge/告警委托 `environment_app_service`；Docker 拉起/停止/
  健康检查保留编排，状态流转经 `before_launch / after_launch_success /
  after_launch_error / change_status` 生命周期钩子守护（环境状态机）。
- `app/services/message_service.py`：机器人 CRUD / 启停 + 站内通知
  （list/unread/set_read/set_read_all）委托 `message_app_service`；
  消息设置树/接收人/模板详情等复杂视图保留在 Service 层（DDD 未完全复刻
  其丰富 schema，双轨并存、可回滚）。
- `app/services/file_service.py`：save_file/delete_file/delete_batch/
  list_project_files/count_by_module/get_file_meta/update_meta 委托
  `file_app_service`；文件模块树等跨域能力仍委托 apitest 域。

## 附：通用支撑域补齐文件清单

```
app/domain/environment/*             # 环境管理域 DDD
app/domain/file/*                    # 文件管理域 DDD
app/domain/message/*                 # 消息通知域 DDD
app/domain/script/*                  # 脚本健康度域 DDD
app/domain/template/*                # 字段模板域 DDD
tests/test_ddd_support_domains.py    # 支撑域纯领域 + 应用服务单测
tests/test_ddd_support_domains_migration.py  # Service 委托迁移回归单测
docs/ddd-architecture-refactoring-plan.md  # 本文档
```
## 四-E、项目管理（project）域：DDD 结构 + 阶段 B 渐进迁移

项目管理域对应当前 `app/services/project_service.py` `app/repositories/project_repo.py`
（项目 CRUD / 成员 / 环境关联 / 自定义函数字段等），DDD 分层已就绪于
`app/domain/project/`（阶段 A），并对**核心生命周期**完成阶段 B（router 接入）：

> **迁移落地（阶段 A→B→C 渐进式）**：DDD 就绪后，`app/services/template_service.py`
> 已收敛为对 `template_app_service` 的**薄委托门面**（阶段 C）；Router 经薄门面到达
> DDD 门面 → 聚合（阶段 B）。模板 list/get/add/update/delete/set_default 全量委托，
> 空范围播种默认与首条自动默认由 DDD 守护；同步修复 DDD 防腐层 `upsert_template`
> 未反序列化 JSON 字段的缺陷并补齐 `enablePlatformDefault` 别名，保证写路径与旧语义一致。
> 回归：`tests/test_ddd_template_migration.py`。

### 聚合根 `Project`（domain/entities/project.py）
- 内聚 `ProjectMember` 子实体 / `ProjectStatus` / `ProjectLanguage` / `MemberRole`。
- **业务命令**：`rename/change_description/change_language/set_repo/set_organization`、
  生命周期 `archive/activate/change_status`（状态机 active ⇄ archived）、
  回收站 `delete/restore`、成员 `add_member/remove_member/update_member_role`，
  非法迁移/回收站内修改/成员缺身份均抛领域异常。

### 值对象 / 领域服务 / 事件 / 仓储 / 基础设施
- `value_objects/`：`ProjectStatus` 状态机（含迁移矩阵）、`ProjectLanguage`、`MemberRole`。
- `services/project_policy.py`：`ProjectLifecyclePolicy` 状态迁移策略。
- `events.py`：ProjectCreated/Renamed/Archived/Activated/SoftDeleted/Restored/
  StatusChanged/MemberAdded/MemberRemoved 等领域事件。
- `repository.py`（Port）+ `infrastructure/project_repository_impl.py`
  （防腐层 `ProjectRepoAdapter`，复用既有 `ProjectRepo` 落库/回收站语义）。
- `application/project_app_service.py`：`ProjectAppService` 用例门面
  （create/get/get_or_raise/update/change_status/archive/activate/soft_delete/
  restore/add_member/remove_member/list_members/list）。

### 阶段 B：router 接入（A→B→C 渐进 · 试点首个真正接线的生命周期域）
- **DTO 契约桥** `application/web_contract.py`：把 DDD 聚合导出 dict 归一为
  既有仓库行口径（不内嵌 members、deleted 归 int、deleted_at 兼容补 None），
  保证阶段 B 对前端/契约测试/矩阵零破坏。
- **router 接入** `routers/projects.py`：核心生命周期接口（列表/创建/详情/更新/
  删除）改调 `ProjectAppService`，参数经 `dto.py` 翻译、返回经契约桥归一。
- **阶段 C（规则下沉）**：状态机/生命周期/成员不变量由领域层守护并在此 canonical
  router 路径生效；`project_service` 保留为兼容门面供 13+ 旁路/compat router
  双轨过渡，逐域收敛后再变薄。

> 落地原则延续其余域：**对外 API 零变化、可回滚**。已由
> `tests/test_ddd_project_migration.py`（契约桥 + router 接入回归）保障。

### 阶段 C：project_service 收敛为薄门面（核心生命周期委托 DDD）
- 既有 `project_service`（34 方法）作为 13+ 旁路/compat router 的**兼容门面**，
  其**核心生命周期** `create / get / list / update / delete` 已收敛为对
  `project_app_service` 的薄委托（参数经 DTO 翻译、返回经 `web_contract` 契约桥
  归一为既有仓库行口径），让旁路流也真正流经 DDD 聚合根与应用门面。
- **规则下沉**：状态机（active⇄archived）、软删除/回收站、名称非空等不变量由
  领域层守护并在此门面路径生效；`update` 对 active/archived 迁移经 `change_status`
  （带幂等守卫，兼容 admin 重复启用/禁用）。
- **仍双轨保留直连 Repo**：遗留 `disabled`/`deleted` 状态位（组织/系统管理 admin 流
  写入、不在聚合 active⇄archived 状态机语义内）及成员管理、自定义函数/字段、项目
  扫描、批量跨项目统计等超聚合能力，保留原样落库/读取，逐域补充 DDD 能力后再收敛。
- **回归**：`tests/test_ddd_project_migration.py` 新增阶段 C 门面委托回归
  （形状/schema、状态机迁移、幂等、软删除、遗留状态位保持）。

### 阶段 C 续：自定义函数/自定义字段旁路方法面收敛（本轮交付）
- `Project` 聚合域已就绪，但其**自定义函数（custom_funcs）** 与**自定义字段
  （project_custom_fields）** 属于超聚合能力的独立子表 CRUD（custom_funcs 存于
  testcases.db、project_custom_fields 存于 tga.db）。本轮按「阶段 C 续」把它们
  收敛为对 `project_app_service` 的委托，Service 侧的「前端格式转换」作为 Web
  契约桥保留在其上，对外 schema 零变化、可回滚：
  - `ProjectRepository` Port 增补自定义函数/字段契约，`ProjectRepoAdapter` 防腐层
    透传既有 `ProjectRepo`（复用已验证落库/建表逻辑）；
  - `ProjectAppService` 增 `list_custom_funcs / get_custom_func / create_custom_func /
    update_custom_func / update_custom_func_status / delete_custom_func /
    list_custom_func_status / list_custom_fields / get_custom_field /
    upsert_custom_field / delete_custom_field` 门面（参数经 `dto.py` 命令翻译）；
  - `project_service` 对应方法改经 DDD 门面，`_custom_func_to_frontend` /
    `_custom_field_to_frontend` 仍作契约桥保留在 Service 层，保证 compat/compat_extra
    路由对外前端字段对象不变。
- **仍双轨保留直连 Repo**：成员批量/跨项目统计（batch_remove_members /
  count_members_by_project / remove_user_all_projects / list_projects_by_user_ids /
  set_member_group / remove_role_from_all_members）、项目扫描等超聚合能力，
  逐项补 DDD 能力后再收敛。
- **回归**：`tests/test_ddd_project_custom_meta_migration.py`（DDD 门面 + Service
  薄门面经 DDD 委托的前端契约端到端零回归）。

## 附：项目管理（project）域文件清单

```
app/domain/project/*                     # 项目管理域 DDD（阶段 A 就绪）
app/routers/projects.py                  # 阶段 B：核心生命周期接入 ProjectAppService
app/services/project_service.py          # 阶段 C：核心生命周期收敛为 DDD 薄门面
tests/test_ddd_project_domain.py         # 项目域纯领域 + 应用服务单测
tests/test_ddd_project_migration.py      # DTO 契约桥 + router/门面接入迁移回归测试
docs/ddd-architecture-refactoring-plan.md # 本文档
```

---

## 四-E、数据工厂（datafactory）域的 DDD 结构与 A→B→C 迁移落地

数据工厂域对应当前 `app/services/datafactory_service.py` `app/routers/datafactory.py`
（数据模板 CRUD / 一键造数 / 批次清理 / 统计），其 DDD 分层见 `app/domain/datafactory/`，
并已完成 **阶段 A→B→C 渐进式迁移**：

### 聚合根 / 实体（domain/entities/）
- `DataTemplate`：数据模板聚合根，守护名称非空、类别合法、schema 归一化等不变量；
  变更命令 `rename/change_category/set_schema/set_status/delete` 均记录领域事件。
- `DataBatch`：造数批次实体（active → cleaned 生命周期）。

### 值对象 / 领域服务 / 事件 / 仓储 / 应用 / 基础设施
- 值对象：`Category` / `TemplateStatus` / `FieldStrategy`。
- `services/data_gen_policy.py`：字段生成策略（sequence/fixed/uuid/random/timestamp/reference）。
- `repository.py`（Port）与 `infrastructure/datafactory_repository_impl.py`（防腐层，
  复用既有 `DatafactoryRepo`；在读取/水合边界对历史非法类别做归一化，保证读旧数据不回归）。
- `application/datafactory_app_service.py`：`DataFactoryAppService` 用例门面。
- `application/web_mapper.py`：**DTO 契约桥**（阶段 B 前置），翻译 DDD 输出与既有
  Web schema 的差异（generate 补 `batch_id` 别名、列表 `{list}→{templates}` 归一化）。

### 迁移三步（A→B→C）落地方式
- **阶段 A**：领域/应用层就绪，`datafactory_app_service` 可跑、有单测
  `tests/test_ddd_datafactory_domain.py`。
- **阶段 B**：`app/routers/datafactory.py` 核心生命周期接口改调 `datafactory_app_service`，
  输出经 `application/web_mapper.py` DTO 桥翻译；领域异常经统一 `fail()` 翻译为既有
  HTTP 语义（404/422），零破坏、可回滚。
- **阶段 C**：`app/services/datafactory_service.py` 瘦身为**薄门面**，核心方法委托
  DDD 应用服务，业务规则/不变量下沉到领域层，保留方法签名与异常语义向后兼容。

## 附：数据工厂（datafactory）域文件清单

```
app/domain/datafactory/*                # 数据工厂域 DDD（domain/application/infrastructure）
app/routers/datafactory.py              # 阶段 B：改调 datafactory_app_service + DTO 桥
app/services/datafactory_service.py     # 阶段 C：薄门面委托 DDD
tests/test_ddd_datafactory_domain.py    # 数据工厂域纯领域 + 应用服务单测
docs/ddd-architecture-refactoring-plan.md  # 本文档
```
## 四-E、测试洞察（test_insight）域的 DDD 结构 与 A→B→C 迁移

测试洞察域对应当前 `app/services/insight_service.py` `app/repositories/insight_repo.py`
与路由 `app/routers/insights.py`（执行追溯 / 自证清白 / 价值量化 / 风险预警 /
低代码生成），已补齐完整 DDD 分层并完成**渐进式 A→B→C 迁移**，
详见 `app/domain/test_insight/`：

### 聚合根 `TraceRun`（domain/entities/trace_run.py）
- 代表一次"测试执行追溯"（追加式审计记录），内聚 `TestResult` / `Coverage` /
  `Attribution` 等值对象。
- **业务命令** `record()` 统一守护不变量（文件路径非空、计数非负、结果与计数自洽、
  覆盖率 0~100）。

### 值对象（domain/value_objects/）
- `TestResult`：passed / failed / error / unknown，自带 `is_passed` / `is_defective`。
- `Coverage`：0~100 区间守卫 + `is_good` 达标判断。
- `Attribution`：需求变更/环境异常/数据问题/代码回归/覆盖遗漏 归因守卫与标签。
- `RiskLevel`：high / medium / low 风险分级（含中文标签）。

### 领域服务 / 事件 / 仓储 / 应用 / 基础设施
- `services/risk_policy.py`、`services/value_policy.py`：风险分级 / 价值量化纯策略。
- `events.py`：`TraceRunRecorded` 等领域事件。
- `repository.py`（Port）与 `infrastructure/test_insight_repository_impl.py`
  （防腐层：直接以 trace.db 落库 + 委托既有 `InsightRepo` 做跨域价值/风险分析）。
- `application/test_insight_app_service.py`：`TestInsightAppService` 用例门面
  （record_trace / get / list / prove_coverage / stats / get_value /
  incident_avoidance / assess_risk / generate_from_description / skill_path）。

### 迁移落地（A→B→C）
- **阶段 A（领域就绪）**：`app/domain/test_insight/` 分层齐全，`test_ddd_test_insight_domain.py`
  通过。
- **阶段 B（Web 接入）**：路由 `app/routers/insights.py` 改为经
  `application/web_bridge.py`（DTO 桥）调用 DDD 应用服务，对外 API 形态不变；
  `/api/insights/risk` 跨 project/case 收集源码的编排保留在路由内。
- **阶段 C（Service 薄化）**：`app/services/insight_service.py` 收敛为对
  `TestInsightAppService` 的薄门面，业务规则下沉领域层；`generation.py` 等既有
  调用方零改动。

> 落地方式：**保持对外 API 与返回结构不变**，双轨并存、可回滚；新增
> `tests/test_ddd_test_insight_migration.py` 覆盖 B/C 迁移回归。

## 附：测试洞察（test_insight）域文件清单

```
app/domain/test_insight/*                       # 测试洞察域 DDD（领域/应用/基础设施）
app/domain/test_insight/application/web_bridge.py # 阶段 B DTO 桥
tests/test_ddd_test_insight_domain.py           # 域纯领域 + 应用服务单测
tests/test_ddd_test_insight_migration.py        # A→B→C 迁移回归单测
docs/ddd-architecture-refactoring-plan.md       # 本文档
```

---

## 五、遗留骨架「接死为活」逐域接线（Option A · 分多轮 PR）

> 背景：`app/domain/` 存在一批**分层齐全但从未被生产代码引用**的"未接线骨架"域
> （约 4400 行），是双写旁路的死代码。治理采用 **Option A「接死为活」**：对
> **有实体 + 已对接生产 repo** 的 11 个域逐个做**阶段 C 薄门面接线** —— 先把
> 骨架缺陷、与 `app/services/*` 的契约差补齐，再让生产 Service 收敛为对 DDD
> 应用服务的薄委托门面，**彻底消灭双写**。因每个域都要逐方法契约等价验证，故
> **分多轮 PR，每轮 1~2 个域**。

### 11 个待接线域总览与契约差登记

| 域 | 对应生产 Service | 已识别骨架缺陷 / 契约差 | 状态 |
|---|---|---|---|
| project_app_config | `project_app_config_service` | DDD 门面与 service 方法一一对应，输出 schema 一致，无契约差 | ✅ Round1 已接线 |
| resource_pool | `resource_pool_service` | `ResourcePoolRepoAdapter.save` 新建时忽略聚合 id → 返回 id ≠ 落库 id（已修复）；`to_dict` 输出 camelCase 与 router 消费的 snake_case `created_at/updated_at` 不一致（门面契约桥） | ✅ Round2 已接线 |
| user_view | `user_view_service` | DDD `to_dict()` 只返回 payload 丢失 id/type（已修复为完整前端视图对象）；update 分支语义经门面统一 | ✅ Round2 已接线 |
| ai_config | `ai_config_service` | ai_config 子域 4 方法（save/get × functional/API scope）已收敛委托 `ai_config_app_service`；默认兜底合并保留在 service 门面，ai_conversation 子域（无 DDD 域）为独立子域不在接线范围 | ✅ Round8 已接线 |
| ai_model | `ai_model_service` | CRUD（list/get/save/delete）收敛委托 `ai_model_app_service`；`_ensure_system_default` env 种子、`createUserName` 展示补齐为门面内保留逻辑 | ✅ Round8 已接线 |
| debug | `debug_service` | 增删改查/读缓存全部委托 `debug_app_service`（落 debug_items 唯一入口）；仅 `ensure_table` 建表保留在门面 | ✅ Round8 已接线 |
| display_config | `display_config_service` | `save()` 的文件归一化/清空语义在 service 直连 repo（双写旁路）；现收敛到 DDD `DisplayAppService.save` 权威裁决，门面仅保留物理文件落盘 `save_uploaded_file` | ✅ Round3 已接线 |
| export_task | `export_task_service` | infra 反向依赖已修（进程内任务注册表）；DDD 门面 5 方法与 service 一一对应、schema 一致 | ✅ Round3 已接线 |
| fake_error | `fake_error_service` | DDD 聚合 `FakeErrorRule` 原 to_dict 缺 typeList/updateTime、ruleResult 未按枚举派生；adapter save 未传 createUser/ruleResult，round-trip 丢 update_time | ✅ Round4 已接线 |
| project_version | `project_version_service` | `ProjectVersionRepoAdapter.save` 新建忽略聚合 id → 返回 id ≠ 落库 id（双 id 漂移）；`save` 更新分支丢 publish_time；service 12 vs DDD 7，方法不对齐（补 set_latest/toggle_status）；功能开关委托 project_app_config 域 | ✅ Round5 已接线 |
| workflow | `workflow_service` | `WorkflowRepoAdapter.save` 新建忽略聚合 id → 返回 id ≠ 落库 id（双 id 漂移）；`WorkflowStatus` to_dict 丢只读 statusFlowTargets、时间口径秒/毫秒不统一（read-model flows 被丢） | ✅ Round6 已接线 |
| frontend_api（协调空壳） | `frontend_api_service` | 已补齐 ApiImport 聚合并完成阶段 C 薄门面接线 | ✅ Round6 已接线（#725） |
| functional_export（协调空壳） | `functional_export_service` | 已补齐 CaseExportJob 聚合并完成阶段 C 薄门面接线 | ✅ Round6 已接线（#725） |
| admin_system（协调空壳·无实体） | `admin_service` | admin_service 收敛为 admin_app_service 薄门面（转发 identity），替代 `→ organization_service` 冗余中间层 | ✅ Round7 已接线 |
| task_center（协调空壳·无实体） | `task_center_service` | task_center_service 收敛为 task_center_app_service 薄门面（委托 manager / TestPlanRepo），补齐 submit/get/list_raw 提交查询侧 | ✅ Round7 已接线 |

> 注：协调域专项治理已推进——`frontend_api`/`functional_export` 已补齐实体聚合并
> 完成阶段 C 薄门面接线（见 Round 6 交付）；`admin_system`/`task_center` 两个
> **无实体协调空壳域**也已按「阶段 C 薄门面」接线（见 Round 7 交付），其对应
> production service（`admin_service`/`task_center_service`）收敛为对 DDD 应用门面
> 的薄委托，DDD 仓储适配层（`AdminRepoAdapter`/`TaskCenterRepoAdapter`）直接对接
> identity 门面 / `app.tasks.manager` / `TestPlanRepo`，不再反向依赖 `app.services`。
> 至此四个协调空壳域（frontend_api / functional_export / admin_system / task_center）
> 均已接线，删 services 前已具备 DDD 出口。
> `export_task` 的 infra 反向依赖已修复并由架构守护 BASELINE 清零；新增反向依赖
> 将被 CI 阻断。

### Round 1 交付：project_app_config 域阶段 C 薄门面接线

- 既有 `app/services/project_app_config_service.py` 的 7 个对外方法
  （get/save_module_config、get_all_modules、is/set_project_version_enabled、
  get/set_config_value）已收敛为对 `project_app_config_app_service` 的**薄委托**，
  参数经 DTO 翻译，返回沿用 DDD 门面底层同一 `project_app_config_repo`，默认合并 /
  upsert / falsy 值保持等语义零变化。
- 对外方法签名与返回结构不变，`auth/router_system`、`extra_router`、
  `project_compat_application` 等调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_project_app_config_migration.py`（断言确实走 DDD 门面 +
  默认合并/falsy 值保持端到端一致）；既有
  `tests/test_project_app_config_repo_alignment.py` 保持绿。

### Round 2 交付：resource_pool + user_view 域阶段 C 薄门面接线

- `app/services/resource_pool_service.py` 6 个对外方法（create/list/get/update/
  delete/set_enable）收敛为对 `resource_pool_app_service` 的**薄委托**。修复
  `ResourcePoolRepoAdapter.save` 新建时忽略聚合 id 的缺陷（`ResourcePoolRepo.create`
  增加可选 `pool_id`），创建返回 id 与落库 id 一致；DDD `to_dict` 输出 camelCase 毫秒，
  门面处做 **camel→snake 契约桥** 还原 router 消费的 snake_case DB 行，方法签名与返回
  结构不变，`test_resources`/`method_compat` 等调用方零改动、可回滚。
- `app/services/user_view_service.py` 5 个对外方法（list/get/add/update/delete）收敛为对
  `user_view_app_service` 的**薄委托**。修复 `UserView.to_dict()` 只返回 payload 丢失
  id/viewType 等 meta 的缺陷（现返回完整前端视图对象，meta 以聚合结构化字段为权威源）；
  `from_dict` 兼容完整视图对象与 DB 原始行两种输入，update 合并后自定义字段保留。
- 对外方法签名与返回结构不变，`auth/router_system`、`system_compat` 等调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_resource_pool_user_view_migration.py`（6 用例，断言确实走
  DDD 门面 + 两处历史缺陷修复 + 全链路契约保持）；既有
  `tests/test_resource_pool_repo_alignment.py` / `test_user_view_persist.py` /
  `test_roundtrip_drift_regressions.py` 保持绿。
### Round 3 交付：display_config 域阶段 C 薄门面接线

- 既有 `app/services/display_config_service.py` 的 `save/get_all/get_file_url`
  已收敛为对 `display_app_service`（display_config 域 DDD 应用服务）的**薄委托**：
  文件类 key 的 fileName/paramValue 互换、清空文件项删除、文本/文件默认值等保存
  语义统一由 DDD `DisplayAppService.save` 权威裁决，消灭 service→repo 双写旁路。
- 仅 `save_uploaded_file`（物理文件落盘、属 file 限界上下文）保留在门面层。
- 对外方法签名与返回结构不变，`auth/router_system`（display/info、display/save）
  等调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_display_config_migration.py`（断言确实走 DDD 门面 +
  文本保存/ multipart 文件 / JSON 旧值幂等重存 / 文件项清空语义端到端一致）；
  既有 `tests/test_p2_auth_realfix.py`、`tests/test_file_template_msg_display_repos.py`
  保持绿。

### Round 3 交付：export_task 域阶段 C 薄门面接线

- 既有 `app/services/export_task_service.py` 收敛为对 `export_task_app_service` 的
  **薄委托门面**：5 个模块级函数（register_task / get_task / remove_task /
  active_task / wait_task）逐一经 DTO 委托 DDD 门面，返回沿用 DDD 门面底层同一
  进程内任务注册表（register → 聚合 ExportTask 落表，语义零变化）。
- 骨架缺陷先行修复：DDD infra 反向依赖 `app.services` 已在早前轮次改为进程内
  任务注册表，本次接线前已无 `domain → services → domain` 循环依赖。
- 对外函数签名与返回结构不变，`functional_export_service` / `websocket` 等
  调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_export_task_migration.py`（断言确实走 DDD 门面 +
  注册/读取/移除/轮询端到端一致）。

### Round 4 交付：fake_error 域阶段 C 薄门面接线

- 补齐 `FakeErrorRule` 聚合 round-trip 缺陷：持久化/回读 `create_user`/`rule_result`/
  `update_time`；`to_dict` 补齐前端契约字段 `typeList` 与 `updateTime`(毫秒，
  经 `time_from_row` 兼容 DB 秒行与 camel 毫秒行)；`ruleResult` 由域内枚举
  （RESP_TYPE_LABEL/RELATION_LABEL）派生，展示文案与旧 `fake_error_repo` 一致。
- `FakeErrorRepoAdapter.save` 传入 createUser/ruleResult，保证「聚合 → DB →
  聚合」round-trip 无漂移。
- 既有 `app/services/fake_error_service.py` 的 6 个方法收敛为对
  `fake_error_app_service` 的**薄委托**（参数经 `SaveRuleItem` DTO 翻译），
  方法签名与返回结构（含 typeList/ruleResult/updateTime 契约）不变，
  `test_compat.py` 等调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_fake_error_migration.py`（断言确实走 DDD 门面 +
  round-trip 全链路契约保持）；既有 `tests/test_fake_error_repo_alignment.py`
  保持绿；架构守护通过、无新增违规。

### Round 5 交付：project_version 域阶段 C 薄门面接线

- `app/services/project_version_service.py` 的 11 个对外方法（list_items / get_item /
  add / update / delete / options / set_latest / toggle_status / is_feature_enabled /
  set_feature_enabled / toggle_feature_enabled）已收敛为对 `project_version_app_service`
  的**薄委托**，参数经 DTO 翻译；返回沿用 DDD 门面底层同一 `project_version_repo`。
- 修复骨架缺陷：`ProjectVersionRepoAdapter.save` 新建不再忽略聚合 id（`add_version` 增
  可选 `version_id`），返回 id == 落库 id（此前双 id 漂移，落库后按返回 id 查不到）；
  `save` 更新分支补持久化 publish_time / update_time，读改存回不丢字段。
- DDD 应用服务补齐 `set_latest` / `toggle_status`（旧 service 的方法/语义对齐）；版本
  「功能开关」（project_app_configs module=projectVersion）委托 Round 1 已接线的
  `project_app_config_app_service`。
- 门面保留历史 `createTime` **秒**口径契约桥（DDD 对外毫秒 → 秒还原），router 与前端
  零改动、可回滚。对外方法签名与返回结构不变，`project_compat_extra2` 等调用方零改动。
- 回归：新增 `tests/test_ddd_project_version_migration.py`（断言确实走 DDD 门面 + 双 id
  修复 + publish_time 持久化 + set_latest/toggle_status 语义 + 功能开关委托端到端一致）；
  既有 `tests/test_project_version_repo_alignment.py`、`tests/test_project_version_module.py`、
  `tests/test_roundtrip_drift_regressions.py` 保持绿。

### Round 6 交付：workflow 域阶段 C 薄门面接线

- `app/services/workflow_service.py` 的 9 个对外方法（list_statuses / get_status /
  add_status / update_status / delete_status / sort_statuses / update_flows /
  set_definition / seed_default_statuses）已收敛为对 `workflow_app_service` 的
  **薄委托**，参数经 DTO 翻译；返回沿用 DDD 门面底层同一 `workflow_repo`。
- 修复骨架缺陷：`WorkflowRepoAdapter.save` 新建不再忽略聚合 id（`workflow_repo.add_status`
  增可选 `status_id`），返回 id == 落库 id（此前双 id 漂移，落库后按返回 id 查不到）；
  `WorkflowStatus.to_dict/from_dict` 时间口径收敛为「内部秒、对外毫秒」并经
  `time_from_row`/`seconds_to_ms` 归一，补齐透出只读 `statusFlowTargets`（read-model
  flows），与前端 WorkFlowType 一致、round-trip 无漂移。
- 对外方法签名与返回结构（含 statusFlowTargets、createTime/updateTime 毫秒）不变，
  `project_compat_extra`、`system_compat`、`system_compat_extra` 等调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_workflow_migration.py`（断言确实走 DDD 门面 + 双 id 修复 +
  statusFlowTargets/毫秒时间契约 + round-trip 端到端一致）；既有
  `tests/test_workflow_repo_alignment.py` 保持绿。

### Round 6 交付：frontend_api + functional_export 协调域阶段 C 薄门面接线

- `app/services/frontend_api_service.py` 的 28 个对外方法已收敛为对
  `frontend_api_app_service` 的**薄委托**。import 操作以 `ApiImport` 聚合承载
  来源/统计语义（构造时校验 source 并触发 `FrontendApiImported` 事件），
  CRUD/查询经 DTO/infrastructure 薄委托 ApitestRepo。DDD `FrontendApiRepoAdapter`
  补齐全部 mgmt_* 对应方法。对外方法签名与返回结构不变，`routers/frontend.py`
  等调用方零改动、可回滚。
- `app/services/functional_export_service.py` 的 5 个模块级函数已收敛为对
  `export_app_service` 的**薄委托**。`ExportAppService.export_cases` 以
  `CaseExportJob` 聚合承载导出作业语义（校验 kind + 触发 `CaseExportTriggered`
  事件 + 完成/失败状态流转），实际文件生成与任务登记委托既有 infrastructure。
  对外函数签名与返回结构不变，`routers/functional_cases*.py` 等调用方零改动、
  可回滚。
- 回归：新增 `tests/test_ddd_functional_export_migration.py` 与
  `tests/test_ddd_frontend_api_migration.py`（断言确实走 DDD 门面 + 薄委托
  契约端到端一致）。

### Round 7 交付：task_center 协调域阶段 C 薄门面接线（legacy manager 队列协调）

- `app/domain/task_center/` 原有 8 个批量/定时方法（stop/delete/rerun/list_tasks +
  schedule 启停/删/改 cron）经 `task_center_app_service` 门面接线。本次把**提交/查询侧**
  直连 `app.tasks.manager` legacy 队列的方法（`submit_task` / `get_task` /
  `list_raw_tasks`）**补齐进 task_center DDD 门面**，按「task_center 域对 legacy
  manager 队列的协调」处理，**不做跨域搬移**（不引入 runs 域耦合）。在 DDD 应用服务 /
  repo 协调接口 / infra 适配器三层补齐对应协调方法，并新增 `SubmitTaskCommand` /
  `GetTaskCommand` / `ListRawTasksCommand` 三个 DTO。
- `app/services/task_center_service.py` 收敛为对 `task_center_app_service` 的**薄委托
  门面**，11 个对外方法（含 submit/get/list_raw）方法签名与返回结构不变，`routers/
  task_center.py`、`routers/generation.py`、`routers/method_compat.py` 等调用方
  零改动、可回滚。
- 回归：`tests/test_task_center_service_alignment.py` 新增 legacy 队列协调用例（断言
  service 收敛为 DDD 薄委托，submit/get/list_raw 经 DDD 门面协调 legacy manager，
  输出语义与直连一致）。架构守护通过（无新增反向依赖违规）。



### Round 7 交付：admin_system + task_center 无实体空壳协调域阶段 C 薄门面接线

- `app/services/admin_service.py` 的 3 个对外方法（enable_organization /
  disable_organization / remove_org_member）收敛为对 `admin_app_service` 的
  **薄委托**（参数经 EnableOrgCommand / DisableOrgCommand / RemoveMemberCommand
  DTO 翻译），替代此前 `admin_service → organization_service` 的冗余中间层。
  DDD `AdminRepoAdapter` 直接委托 identity 域 `identity_app_service`，组织启停 /
  成员移除语义与重构前一致（返回 bool），`routers/missing_admin.py` 等调用方
  零改动、可回滚。
- `app/services/task_center_service.py` 的 11 个对外方法收敛为对
  `task_center_app_service` 的**薄委托**：exec-task 批量管理（stop/delete/rerun/
  list_tasks）与 schedule 管理（switch/enable/delete/update_cron）经 DTO 委托；
  提交/查询侧 `submit_task / get_task / list_raw_tasks`（直连 `app.tasks.manager`
  的 legacy 队列）补齐进 DDD 门面并透传（DDD `TaskCenterRepoAdapter` 对 manager
  采用函数内 import，兼容既有 `mgr.manager` 替换式 mock）。对外方法签名与返回
  结构不变，`routers/task_center.py` / `generation.py` / `method_compat.py` 等
  调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_task_center_admin_migration.py`（断言确实走 DDD
  门面 + DTO 翻译 + 提交/查询/管理全链路委托端到端一致）；既有
  `tests/test_task_center_service_alignment.py` / `test_ddd_coordination_domains.py`
  保持绿。

### 大域 DDD application 方法面补全（与旧 service 逐方法对齐）

> 目标：`apitest / project / org / case / defect / auth / test_plan` 七个大域，让
> DDD application 门面具备与对应 `app/services/*` **逐方法对齐**的完整方法面，
> 使 Service 能收敛为薄门面（逐步消除旁路直连）。因每个域方法面很大，**分域逐轮
> 推进**，每轮补全 1~2 个域。

#### 已补全域：test_plan

- `app/domain/test_plan/application/test_plan_app_service.py` 补齐与
  `test_plan_service` 对齐的**旁路方法面**：模块树（list/create/update/delete/move
  module）、模块维度统计（count_plans_by_module）、Dashboard 布局（save/load）、
  定时任务配置（save/get/get_schedules/delete_schedule）、关联用例存储级编排
  （add/remove/list_plan_case、update_plan_case_status、update_rel_pos）。实现为
  对既有 `TestPlanRepo` 的薄委托（防腐层，不搬移业务），函数内 import 保持轻耦合。
- `app/services/test_plan_service.py` 相应旁路方法收敛为对 `test_plan_app_service`
  的**薄委托**。计划生命周期（create/get/update/list/count/statistics/archive/
  delete）此前已委托 DDD；至此 test_plan 域除 `_to_legacy` 契约桥读取与计划头
  通用编辑 `update_plan`（应用层专有列，保留既有仓库直连）外，全部方法均经 DDD 门面。
  对外方法签名与返回结构不变，调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_test_plan_bypass_surface.py`（断言 service 经 DDD 门面
  编排旁路方法 + 模块/定时/Dashboard/关联用例薄委托端到端一致）；既有
  `tests/test_ddd_test_plan_migration.py` / `test_ddd_test_plan_domain.py` 保持绿。

#### 已补全域：org（→ identity 域） 与 case

- **org → identity**：`app/domain/identity/application/identity_app_service.py`
  补齐与 `organization_service` 对齐的**旁路方法面**：组织删除/恢复
  （delete_organization / recover_organization）、按名查询（get_organization_by_name）、
  成员列表/详情/计数（list_members / get_member / count_members）、组织反查
  （list_orgs_by_user / list_orgs_by_users）、组织-项目关联（list_projects /
  bind_project）、租户摘要（tenant_summary / get_tenant_summary）。实现为对
  既有 `OrganizationRepo` 的薄委托（防腐层，不搬移业务），函数内 import 保持轻耦合。
  `app/services/organization_service.py` 相应旁路方法收敛为对
  `identity_app_service` 的**薄委托**。对外方法签名与返回结构不变，调用方零改动、
  可回滚。`seed_tenant_data` 跨 auth/projects 编排保留在 Service 层（非本域核心）。
- **case**：`app/domain/cases/application/case_app_service.py` 补齐与
  `case_service` 对齐的**旁路方法面**：版本管理（list_versions / get_version /
  rollback）、变更日志（list_changes / count_changes）、需求关联（add_requirement /
  remove_requirement / list_requirements）、回收站（purge_case / list_trash_cases）、
  物理删除（hard_delete）、统计（get_stats）、执行结果（update_case_result）、
  脑图（get_mindmap）、完整信息（get_full_info）。实现为对既有 `CaseRepo` 的
  薄委托（防腐层，不搬移业务），函数内 import 保持轻耦合。`app/services/case_service.py`
  相应旁路方法收敛为对 `case_app_service` 的**薄委托**。对外方法签名与返回结构
  不变，调用方零改动、可回滚。`build_functional_module_tree` / `to_functional_case`
  为跨 apitest 域编排，保留在 Service 层。
#### 已补全域：identity/auth

- `app/domain/identity/application/identity_app_service.py` 补齐与
  `auth_service` 对齐的**旁路方法面**：API Key（list/create/revoke/toggle）、
  用户组成员（list/add/remove/remove_by_id）、本地配置 local_config
  （add/get/update/toggle）。实现为对既有 `AuthRepo` / `UserGroupRepo` 的
  薄委托（防腐层，不搬移业务），函数内 import 保持轻耦合。
- `app/services/auth_service.py` 相应旁路方法收敛为对 `identity_app_service`
  的**薄委托**。auth_service 的用户核心生命周期（create/get/list/update/
  enable/change_password）此前已委托 DDD；角色/用户组 create/update/delete 也
  已委托 DDD（Role 聚合）。至此 auth→identity 域的 api_key / 用户组成员 /
  local_config 旁路面补齐，覆盖「identity 域覆盖面待补」项。对外方法签名与
  返回结构不变，调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_identity_auth_surface.py`（断言 auth_service 确实经
  DDD 门面编排 api_key/组员/local_config + 端到端契约零回归）；既有
  `tests/test_ddd_identity_domain.py` / `tests/test_ddd_identity_migration.py` /
  `tests/test_auth_repo_alignment.py` 保持绿。

### Round 8 交付：ai_config / ai_model / debug 三域阶段 C 薄门面接线

`ai_config` / `ai_model` / `debug` 三域的 DDD 骨架（分层齐全）此前已就绪并经
早轮（#720）收敛，本 Round 将这三域按与其它 Round 一致的**阶段 C 薄门面**口径
正式登记落地，确认生产 Service 已收敛为对 DDD 应用门面的薄委托：

- `app/services/ai_config_service.py`：**ai_config 子域**（功能/接口用例 AI 配置）
  的 `save_functional_case_config / get_functional_case_config / save_api_case_config /
  get_api_case_config` 经 `SaveAiConfigCommand / GetAiConfigCommand` 委托
  `ai_config_app_service`，默认兜底合并（`merge_case_ai_config` / `merge_api_ai_config`）
  保留在 Service 门面以维持对外 camelCase 契约；`ai_conversation` 子域（无对应
  DDD 域）为独立子域，不在本接线范围。
- `app/services/ai_model_service.py`：CRUD 收敛委托 `ai_model_app_service`
  （`ListModelsCommand / GetModelCommand / upsert / DeleteModelCommand`）；系统内置
  env 种子 `_ensure_system_default` 与前端展示字段 `createUserName` 补齐为门面内
  保留逻辑，不属旁路双写。
- `app/services/debug_service.py`：增删改查与 `list_all / get / save / delete`
  全部委托 `debug_app_service`（落 debug_items 唯一入口），仅 `ensure_table`
  建表保留在门面。

> 三域均已有迁移回归测试（`test_ddd_ai_config_migration.py` /
> `test_ddd_ai_model_migration.py` / `test_ddd_debug_migration.py`）覆盖「确实走
> DDD 门面 + 契约/往返零回归」。Router / 对外 API 零改动、可回滚。

### Round 10 交付：routers 直连 DDD application（阶段 B router-direct）

在 Round 1~7 完成 Service → DDD 薄门面接线后，本次将第一批 routers 从
「router → service(薄门面) → DDD」升级为 **「router 直连 DDD app_service」**
（参照 datafactory.py / reports.py 样板），绕过 services 层直接调
DDD application services：

| Router | 直连 DDD 门面 | 输出契约保持 |
|---|---|---|
| `app/routers/scripts.py` | `script_app_service`（script 域） | 404 语义 / {scripts,total} / 脚本详情 |
| `app/routers/runs.py` | `run_record_app_service`（runs 域） | passed int 0/1 归一 / {records,total} / stats / 404 |
| `app/routers/task_center.py` | `task_center_app_service`（task_center 域） | 批量/单条管理返回结构不变 |

- **scripts.py**：移除对 `app.services.script_service` 的依赖，直接经
  `script_app_service` + application DTO（RegisterCommand / ScriptQuery /
  GetCommand / UpdateCommand / DeleteCommand / RecordExecutionCommand 等）
  调用 script 域。领域异常（AggregateNotFound→404）在路由内联翻译。
- **runs.py**：移除对 `app.services.run_service` 的依赖，直接经
  `run_record_app_service` 调用 runs 域 RunRecord 聚合。`passed` 字段
  在路由侧归一为 int 0/1（兼容既有 /api/runs 契约）。
- **task_center.py**：router 内 `_exec_*` / `_schedule_*` 兼容 helper
  直接委托 `task_center_app_service`（参数经 StopTasksCommand /
  DeleteTasksCommand / RerunTaskCommand / SwitchSchedulesCommand 等 DTO
  翻译），不再经 `task_center_service` 薄门面中转。

- 回归：新增 `tests/test_router_ddd_stage_b.py`（断言 router 不再 import
  services、确实 import DDD app_service、对外 API 契约不变）。
- 既有 services（`script_service` / `run_service` / `task_center_service`）
  保留为过渡兼容层供其余 router（generation / method_compat / reports_compat /
  projects_scan 等）调用，不删除、可回滚。


### Round 11 交付：defect 域旁路方法面收敛到 DDD 门面

在 defects 域核心生命周期（create/update/trash/restore/purge/list/list_trash）
已委托 `defect_app_service` 之后，本次把 `defect_service` 剩余的**旁路方法面**
也收敛为对 DDD 应用门面的薄委托，使 `defect_service` 不再直连 `DefectRepo`
做旁路数据访问：

- **评论**（`defect_comments` 子表读写）：`list_comments` / `create_comment` /
  `update_comment` / `delete_comment` 改为经 `defect_app_service`（新增
  `ListCommentsQuery` / `CreateCommentCommand` / `UpdateCommentCommand` /
  `DeleteCommentCommand` DTO），DDD 仓储 Port / `DefectRepoAdapter` 增对应
  转发实现透传既有 DefectRepo，保持软删除 / 级联删除子评论语义。
- **auto_create_from_result**（测试失败自动建缺陷）：收敛经 `AutoCreateFromResultCommand`
  委托 DDD 门面，passed 短路 / 严重程度判定 / 摘要提取逻辑维持不变。
- **permanent_delete**（绕过回收站的彻底删除）：收敛经 `PermanentDeleteCommand`
  委托 DDD 门面，不存在抛 404。
- 对外方法签名与返回结构不变，`routers/bug.py` / `bug_compat.py` / `tracker` 等
  调用方零改动、可回滚。
- 回归：新增 `tests/test_ddd_defects_bypass_migration.py`（断言评论 / auto_create /
  permanent_delete 确实走 DDD 门面 + 端到端契约零回归）。


### Round 13 交付：apitest 域 mocks / env / env_groups / global_params 旁路收敛到 DDD 门面

`apitest_service` 中 **mocks / environments / env_groups / global_params**
（apitest 侧 `api_environments` 配置，route 不建模）此前为双轨直连 `ApitestRepo`
的旁路方法。本次将其收敛为对 apitest 域 DDD 门面的**薄委托**：

- **mocks**：走 `apitest_web` → `apitest_app_service`（`ApiMock` 聚合）。
  覆盖对象级 CRUD / running / 列表-计数 / 回收站列表-计数 / 恢复-清除 /
  批量删除-恢复-清除。
- **environments / env_groups / global_params**：直接经
  `apitest_app_service`（route 不建模，`app_service` 内转发既有 `ApitestRepo`）
  收口。覆盖环境 CRUD/export/import、环境组 CRUD、全局参数
  get/save/delete/delete_by_id、`env_detail_to_frontend` 前端契约桥。
- 对外方法签名与返回结构零变化，调用方 routers 零改动、可回滚。

> 注：apitest 的 api_environments 与 `app/domain/environment`（Docker 测试资源
> 环境）非同源，此处不做跨域搬移。

- 回归：`tests/test_ddd_apitest_mock_aggregate.py` +
  `tests/test_ddd_apitest_env_bypass.py`（新增，验证 mocks/env/groups/global_params
  经 DDD 门面端到端零回归）。


### Round 14 交付：大域 DDD application 方法面补全（case_review / project / environment）

承接 Round 12-13 完成 apitest / project 自定义函数·字段旁路收敛之后，本轮把
**case_review / project 成员管理 / environment** 三域在 DDD application 层
的「聚合读方法」与「运维编排」方法面补齐，并让既有 Service 层改为对 DDD 门面的
薄委托（对外返回 schema 与迁移前一致、可回滚）：

#### 1) case_review 聚合读方法面
- `case_review_app_service` 增补 `list_links`（评审关联用例原始行）与
  `is_following`（关注状态查询）两个读方法；`list_reviews` / `get_detail` /
  `get_status_counts` / `count_by_module` 等读方法此前已就绪。
- `CaseReviewRepository` Port 增补 `list_links` 契约，Adapter 防腐层透传既有
  `CaseReviewRepo.list_links`。
- `case_review_service` 的 list / get_detail / get_review / list_links /
  list_link_case_ids / is_following / toggle_follow / get_case_status_counts /
  count_reviews / _review_count_by_module 均改为经 `case_review_app_service`
  DDD 门面委托（DTO 契约桥 `to_header_dict` 归一为 Repo header schema）。

#### 2) project 成员管理方法面
- `ProjectRepository` Port + Adapter 增补 `get_member` / `update_member` /
  `batch_remove_members` 契约与防腐转发。
- `project_app_service` 增补 `get_member` / `update_member` /
  `batch_remove_members` 门面；DTO 增 `GetMemberCommand` / `UpdateMemberCommand` /
  `BatchRemoveMembersCommand`。
- `project_service` 的 `get_member` / `update_member` 改经 DDD 门面委托；
  `add_member` 因上游（org router）期望成员行 schema（含行级 member_id），
  保留 `ProjectRepo` 直写（双轨过渡，注释说明原因）；`remove_member` 经 DDD
  门面并带直连回退。

#### 3) environment Docker 运维编排下沉
- 新增 `app/domain/environment/infrastructure/docker_ops.py`：把 Docker 拉起
  / 停止 / 健康检查（compose up/down / docker run / docker inspect / HTTP 探测）
  等外部副作用收敛到 Infrastructure 层。
- `environment_app_service` 增补 `launch` / `stop` / `health_check` /
  `health_check_all` 四个编排方法（使用既有 `LaunchCommand` / `StopCommand` /
  `HealthCheckCommand` DTO），串联 `before_launch` / `after_launch_success` /
  `after_launch_error` 状态钩子与告警联动。
- `environment_service` 的 `launch` / `stop` / `health_check` / `health_check_all`
  改为对 `environment_app_service` 的薄委托，Docker 子进程代码从 Service 层移除。

> 注：apitest 域 module_tree / operation_logs / env_group / mock / execution_logs
> 旁路收敛与 file 域写路径（save/delete/batch/update_meta）已在 Round 12-13
> 及前期交付完成，不在本轮重复。file 域富 schema 列表（list_project_files /
> count_files_by_module）涉及前端字段差异，仍在 Service 保留前端契约桥、
> 双轨过渡。

- 回归：`tests/test_ddd_surface_round726.py`（代码级方法面快照 + DDD 委托断言）。


### Round 12+（推进中）：将 legacy-only / mixed routers + compat routers 逐个切到 DDD application

在 Round 10 验证 router-direct DDD 样板可行后，后续将按域逐个把
仍经 services 中转的 routers 切换为直接调用 DDD application：
- **待切换（services 已为 DDD 薄门面、router 可直连）**：environments.py
  （CRUD/回收站部分）、notifications.py（message 域直连子集）、
  ai_config.py（ai_model/ai_config 子域直连）等。
- **待切换（需先补齐 DDD 方法面）**：cases.py / defects.py / case_review.py
  / apitest*.py / organizations.py / projects*.py / system*.py 等大域 routers
  —— 依赖「补全大域 DDD application 方法面」完成后进行。
- **compat routers**（`*_compat*.py`）：在对应域 DDD 方法面补全后逐个切换。


### 逐轮 PR 接线记录（持续推进）

| 轮次 | 域 | PR |
|---|---|---|
| Round 1 | project_app_config | #713 |
| Round 2 | resource_pool、user_view | #714 |
| Round 3 | export_task | #715 |
| Round 3 | display_config | #717 |
| Round 4 | fake_error | #716 |
| Round 5 | project_version | #719 |
| Round 6 | workflow | #724 |
| Round 6 | frontend_api、functional_export 协调域接线 | #725 |
| Round 7 | admin_system、task_center 空壳协调域接线 | #731 |
| Round 8 | ai_config、ai_model、debug 阶段 C 薄门面接线登记 | #720 |
| Round 9 | 大域方法面对齐 · test_plan（旁路方法面补全） | #733 |
| Round 10 | routers 直连 DDD（scripts/runs/task_center 阶段 B router-direct） | #734 |
| Round 11 | defect 域旁路方法面（评论 / auto_create / permanent_delete）收敛 DDD | #735 |

| Round 12 | 大域方法面对齐 · org + case（旁路方法面补全） | #737 |
| Round 13 | apitest 域 mocks / env / env_groups / global_params 旁路收敛 DDD 薄门面 | #742 |
| Round 14 | 大域方法面对齐 · apitest+case_review+project+file+environment（DDD application 方法面补全） | #726 |
