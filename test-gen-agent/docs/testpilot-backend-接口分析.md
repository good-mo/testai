# TestPilot v3.x Backend 接口分析报告

> 分析对象：`https://github.com/metersphere/metersphere/tree/v3.x/backend`
> 说明：本文覆盖后端整体架构、7 大业务模块概览、核心接口（api-test 接口测试模块）的路径/请求方式/入参/返回值/业务逻辑，以及全量接口清单索引。

---

## 一、整体架构

### 技术栈
- **Spring Boot 3.5.7**（基于 spring-boot-starter-parent）
- **Java 21**
- **MyBatis**（分页使用 `PageHelper`）+ MySQL
- **Apache Shiro**（权限控制，`@RequiresPermissions`）
- **Swagger/OpenAPI 3**（接口文档注解 `@Operation`/`@Tag`）
- 微服务化趋势：按业务域拆分为独立 `services/*` 子模块（单 jar 多模块聚合）

### 模块划分（backend/services）
| 模块 | 用途 | Controller 数 |
|------|------|------|
| **api-test** | 接口测试（接口定义/用例/场景/Mock/调试/报告） | 21 |
| **case-management** | 功能用例管理（用例/评审/脑图/关联） | 15 |
| **bug-management** | 缺陷管理 | 6 |
| **dashboard** | 工作台/概览/待办 | 3 |
| **project-management** | 项目/成员/环境/文件/通知/模板 | 22 |
| **system-setting** | 系统设置/组织/用户/角色/插件/资源池 | 41 |
| **test-plan** | 测试计划/报告/执行/任务中心 | 13 |
| **framework** | AI 引擎/领域模型/插件 SDK（非 REST 业务） | - |

### 通用设计范式
- **Controller 薄、Service 厚**：Controller 只做参数校验 + 权限/日志/通知注解 + 调 Service。
- **统一权限注解**：`@RequiresPermissions(权限常量)` + `@CheckOwner(资源归属校验)`。
- **统一审计**：`@Log(type=..., msClass=日志Service)` 记录操作日志；`@SendNotice` 发通知。
- **分页统一**：入参继承 `BasePageRequest`（含 `current/pageSize/sort`），返回 `Pager<T>`。
- **回收站机制**：软删除 `deleted` 标志（`/delete-to-gc` 进回收站，`/recover` 恢复）。
- **关注/收藏**：统一 `follow`/`unfollow`（GET 切换）。
- **多版本**：接口定义/用例支持版本管理（`/version/{id}`）。
- **任务中心**：统一异步执行，执行入口返回 `TaskRequestDTO`，通过任务中心轮询实时结果。

---

## 二、api-test（接口测试）模块 —— 核心详细分析

### 2.1 接口定义管理 `ApiDefinitionController`
类路径 `@RequestMapping("/api/definition")`，权限前缀 `PROJECT_API_DEFINITION_*`。

| 方法 | 路径 | 请求方式 | 入参 | 返回值 | 业务逻辑 |
|------|------|------|------|--------|----------|
| 接口列表 | `/api/definition/page` | POST | `ApiDefinitionPageRequest`（继承 BasePageRequest，含 projectId[必填]、name、protocols、moduleIds、versionId、refId、deleted、includeIds/excludeIds） | `Pager<List<ApiDefinitionDTO>>` | 分页查询；`deleted=1` 查回收站（按 delete_time 排序），否则按 pos 排序；先 `initApiSelectIds` 计算含/排除 ID |
| 接口覆盖率 | `/api/definition/rage/{projectId}` | GET | 路径参数 projectId | `ApiCoverageDTO`（apiAllIds + 有用例的ID + 被场景/自定义引用的ID） | 统计接口被用例/场景/自定义请求覆盖情况，计算接口覆盖率 |
| 添加接口 | `/api/definition/add` | POST | `ApiDefinitionAddRequest`（name[必填]、protocol[默认http]、projectId[必填]、method、path、status[必填枚举]、moduleId[必填]、versionId、description、tags、request[必填Object]、response[必填List]、uploadFileIds、linkFileIds、customFields） | `ApiDefinition` | 生成 num/pos → 插入定义 → 存请求/响应 blob → 处理文件资源 → 写操作日志、发通知 |
| 更新接口 | `/api/definition/update` | POST | `ApiDefinitionUpdateRequest` | `ApiDefinition` | 校验归属 → 更新 → 保存新版本 → 日志/通知 |
| 批量更新 | `/api/definition/batch-update` | POST | `ApiDefinitionBatchUpdateRequest`（selectIds + 批量字段） | void | 按 ID 批量更新标签/描述等 |
| 复制接口 | `/api/definition/copy` | POST | `ApiDefinitionCopyRequest`（selectIds） | `ApiDefinition` | 深拷贝定义+请求+文件 |
| 复制文件 | `/api/definition/file/copy` | POST | `ApiFileCopyRequest` | `Map<String,String>` | 复制时复制关联文件 |
| 批量移动 | `/api/definition/batch-move` | POST | `ApiDefinitionBatchMoveRequest` | void | 移动模块并重排 pos |
| 版本列表 | `/api/definition/version/{id}` | GET | 路径参数 id | `List<ApiDefinitionVersionDTO>` | 查询接口多版本记录 |
| 接口详情 | `/api/definition/get-detail/{id}` | GET | 路径参数 id | `ApiDefinitionDTO` | 拼装请求/响应/自定义字段/关注状态 |
| 关注切换 | `/api/definition/follow/{id}` | GET | 路径参数 id | void | 关注/取消关注切换 |
| 回收站 | `/api/definition/delete-to-gc/{id}` | GET | 路径参数 id | void | 软删除进回收站 |
| 批量回收 | `/api/definition/batch/delete-to-gc` | POST | `TableBatchProcessDTO` | void | 批量软删除 |
| 删除 | `/api/definition/delete/{id}` | GET | 路径参数 id | void | 彻底删除（含 blob/文件） |
| 恢复 | `/api/definition/recover` | POST | `ApiDefinitionBatchRequest` | void | 从回收站恢复 |
| 文档分页 | `/api/definition/page-doc` | POST | `ApiDefinitionDocPageRequest` | `Pager<List<ApiDefinitionDTO>>` | 文档模式分页 |
| 导入接口 | `/api/definition/import` | POST | `ImportRequest` + MultipartFile | void | 支持 Postman/Swagger/Jmeter 导入 |
| 导出 | `/api/definition/export/{type}` | POST | `ApiDefinitionExportRequest` + 路径 type | String(导出任务ID) | 异步导出（type=postman/jmeter/swagger） |
| 调试接口 | `/api/definition/debug` | POST | `ApiDefinitionRunRequest`（id、reportId、request、projectId、frontendDebug） | `TaskRequestDTO` | 组装请求 → 获取执行参数 → 生成任务 → 提交执行引擎（实时/异步） |
| JSON预览 | `/api/definition/json-schema/preview` | POST | `JsonSchemaItem` | String | 生成 JsonSchema 预览 |
| 操作历史 | `/api/definition/operation-history` | POST | `OperationHistoryRequest` | `Pager<List<OperationHistoryDTO>>` | 查询版本变更历史 |

### 2.2 接口用例管理 `ApiTestCaseController`
类路径 `@RequestMapping("/api/case")`。

| 方法 | 路径 | 请求方式 | 入参 | 返回值 | 业务逻辑 |
|------|------|------|------|--------|----------|
| 用例列表 | `/api/case/page` | POST | `ApiTestCasePageRequest` | `Pager<List<ApiTestCaseDTO>>` | 分页，支持按接口筛选/优先级/状态 |
| 添加用例 | `/api/case/add` | POST | `ApiTestCaseAddRequest` | `ApiTestCase` | 基于接口创建用例，复制请求 |
| 用例详情 | `/api/case/get-detail/{id}` | GET | 路径参数 id | `ApiTestCaseDTO` | 拼装用例+请求断言 |
| 运行用例 | `/api/case/run` | POST | `ApiCaseRunRequest`（id、environmentId、apiDefinitionId、request...） | `TaskRequestDTO` | 单条执行，绑定环境 |
| 批量运行 | `/api/case/batch/run` | POST | `ApiCaseBatchRunRequest` | void | 异步批量执行 |
| 调试 | `/api/case/debug` | POST | `ApiCaseRunRequest` | `TaskRequestDTO` | 同运行，实时返回 |
| 批量编辑 | `/api/case/batch/edit` | POST | `ApiCaseBatchEditRequest` | void | 批量改状态/优先级/标签 |
| 同步接口变更 | `/api/case/batch/api-change/sync` | POST | `ApiCaseBatchSyncRequest` | void | 接口变更同步到用例 |
| 接口对比 | `/api/case/api/compare/{id}` | GET | 路径参数 id | `ApiCaseCompareData` | 比对用例与接口请求差异 |
| 用例统计 | `/api/case/statistics` | POST | `ApiCaseStatisticsRequest` | `List<ApiTestCaseDTO>` | 统计用例分布 |
| 回收站/恢复 | `/api/case/delete-to-gc/{id}`、`/recover/{id}` | GET | 路径参数 id | void | 软删除/恢复 |
| 关注 | `/api/case/follow/{id}`、`/unfollow/{id}` | GET | 路径参数 id | void | 关注/取消 |
| 执行历史 | `/api/case/execute/page` | POST | `ExecutePageRequest` | `Pager<List<ExecuteReportDTO>>` | 用例执行报告历史 |
| AI 对话 | `/api/case/ai/chat` | POST | `ApiCaseAIChatRequest` | String | AI 辅助生成用例 |

### 2.3 场景编排 `ApiScenarioController`
类路径 `@RequestMapping("/api/scenario")`。

| 方法 | 路径 | 请求方式 | 入参 | 返回值 | 业务逻辑 |
|------|------|------|------|--------|----------|
| 场景列表 | `/api/scenario/page` | POST | `ApiScenarioPageRequest` | `Pager<List<ApiScenarioDTO>>` | 分页，含步骤数/关联用例数 |
| 添加场景 | `/api/scenario/add` | POST | `ApiScenarioAddRequest`（含 steps 步骤集合） | `ApiScenario` | 保存场景+步骤 |
| 场景详情 | `/api/scenario/get/{scenarioId}` | GET | 路径参数 | `ApiScenarioDetailDTO` | 拼装步骤树 |
| 运行场景 | `/api/scenario/run` | POST | `ApiScenarioRunRequest` | `TaskRequestDTO` | 整场景执行 |
| 调试 | `/api/scenario/debug` | POST | `ApiScenarioDebugRequest`（id、projectId、steps、frontendDebug） | `TaskRequestDTO` | 步骤级实时调试 |
| 步骤详情 | `/api/scenario/step/get/{stepId}` | GET | 路径参数 | Object | 获取单步骤配置 |
| 批量操作 | `/api/scenario/batch-operation/*` | POST | 各类 Batch 请求 | `ApiScenarioBatchOperationResponse` | 批量删除/恢复/移动/复制/运行/定时配置 |
| 定时配置 | `/api/scenario/schedule-config` | POST | `ApiScheduleConfigRequest` | String | 设置定时执行 |
| 关联用例 | `/api/scenario/association/page` | POST | `ApiScenarioAssociationRequest` | `Pager<List<ApiScenarioAssociationDTO>>` | 查询被关联的用例/计划 |

### 2.4 Mock 服务
| Controller | 路径 | 说明 |
|---|---|---|
| `ApiDefinitionMockController` | `/api/definition/mock/*` | Mock 定义 CRUD、启停、URL 获取、批量编辑 |
| `MockServerController` | `/mock-server/{projectNum}/{apiNum}/**` | 运行时 Mock 响应，按项目编号+接口编号命中配置返回模拟数据 |

### 2.5 接口调试 `ApiDebugController`（独立调试/快捷请求）
| 路径 | 请求方式 | 入参 | 返回值 | 说明 |
|------|------|------|--------|------|
| `/api/debug/list/{protocol}` | GET | 路径参数 protocol | `List<ApiDebugSimpleDTO>` | 快捷请求列表 |
| `/api/debug/add` | POST | `ApiDebugAddRequest` | `ApiDebug` | 保存快捷请求 |
| `/api/debug/update` | POST | `ApiDebugUpdateRequest` | `ApiDebug` | 更新 |
| `/api/debug/debug` | POST | `ApiDebugRunRequest` | `TaskRequestDTO` | 实时调试执行 |
| `/api/debug/get/{id}` | GET | 路径参数 id | `ApiDebugDTO` | 详情 |
| `/api/debug/import-curl` | POST | `CurlEntity` | `CurlEntity` | 导入 cURL 生成请求 |
| `/api/debug/delete/{id}` | GET | 路径参数 id | void | 删除 |

### 2.6 执行/报告 `ApiReportController`、`ApiExecuteResourceController`
| 路径 | 请求方式 | 说明 |
|---|---|---|
| `/api/report/case/page` | POST | 用例/接口执行报告分页 |
| `/api/report/case/get/{id}` | GET | 报告详情（含步骤结果） |
| `/api/report/case/get/detail/{reportId}/{stepId}` | GET | 单步骤执行详情 |
| `/api/report/case/export/{reportId}` | POST | 导出报告 |
| `/api/report/share/*` | GET/POST | 报告分享（生成链接、查看） |
| `/api/execute/resource/script` | POST | 获取执行脚本 |
| `/api/execute/resource/file` | POST | 下载执行文件 |
| `/task/center/api/*` | POST/GET | 任务中心（项目/组织/系统级实时任务分页、停止） |

### 2.7 其他辅助 Controller
- `ApiTestController`：协议列表 `/api/protocol/{orgId}`、Mock 触发、插件脚本、环境列表、资源池、下载、公共脚本。
- `ApiDefinitionModuleController`（模块树）：`/api/definition/module/tree|add|update|delete/{id}|move|count|env/tree|only/tree`。
- `ApiScenarioModuleController`（场景模块树）：`/api/scenario/module/*`。
- `ApiDocShareController`：API 文档分享 `/api/doc/share/*`。

---

## 三、case-management（功能用例）模块 —— 核心接口

类路径 `@RequestMapping("/functional/case")`（主）、`/case/review`（评审）、`/functional/case/*`（子资源）。

| 路径 | 请求方式 | 入参 | 返回值 | 说明 |
|------|------|------|--------|------|
| `/functional/case/page` | POST | `FunctionalCasePageRequest` | `Pager<List<FunctionalCasePageDTO>>` | 功能用例分页 |
| `/functional/case/add` | POST | `FunctionalCaseAddRequest` | `FunctionalCase` | 新增用例 |
| `/functional/case/detail/{id}` | GET | 路径参数 id | `FunctionalCaseDetailDTO` | 用例详情 |
| `/functional/case/update` | POST | `FunctionalCaseUpdateRequest` | `FunctionalCase` | 更新 |
| `/functional/case/version/{id}` | GET | 路径参数 id | `List<FunctionalCaseVersionDTO>` | 版本 |
| `/functional/case/batch/*` | POST | Batch 请求 | void | 批量删除/移动/复制/编辑 |
| `/functional/case/import/excel` | POST | MultipartFile | `FunctionalCaseImportResponse` | Excel 导入 |
| `/functional/case/import/xmind` | POST | MultipartFile | `FunctionalCaseImportResponse` | XMind 导入 |
| `/functional/case/export/excel` | POST | `FunctionalCaseExportRequest` | String(任务ID) | 异步导出 Excel |
| `/functional/case/module/tree/{projectId}` | GET | 路径参数 | `List<BaseTreeNode>` | 用例模块树 |
| `/functional/mind/case/tree` | POST | 请求体 | `List<BaseTreeNode>` | 脑图树 |
| `/functional/case/trash/page` | POST | 分页请求 | `Pager` | 回收站 |
| `/functional/case/ai/chat` | POST | 请求体 | String | AI 生成用例 |
| `/case/review/page` | POST | `CaseReviewPageRequest` | `Pager<List<CaseReviewDTO>>` | 用例评审分页 |
| `/case/review/add` | POST | `CaseReviewAddRequest` | `CaseReview` | 发起评审 |
| `/review/functional/case/save` | POST | 评审请求 | void | 提交评审结论 |

---

## 四、bug-management（缺陷）模块 —— 核心接口

类路径 `@RequestMapping("/bug")`。

| 路径 | 请求方式 | 入参 | 返回值 | 说明 |
|------|------|------|--------|------|
| `/bug/page` | POST | `BugPageRequest` | `Pager<List<BugDTO>>` | 缺陷分页 |
| `/bug/add` | POST | `BugAddRequest` | `Bug` | 新增缺陷 |
| `/bug/update` | POST | `BugUpdateRequest` | `Bug` | 更新缺陷 |
| `/bug/get/{id}` | GET | 路径参数 id | `BugDetailDTO` | 详情 |
| `/bug/delete/{id}` | GET | 路径参数 id | void | 删除 |
| `/bug/sync/{projectId}` | GET | 路径参数 | void | 同步平台缺陷 |
| `/bug/sync/all` | POST | 请求体 | void | 全量同步 |
| `/bug/export` | POST | `BugExportRequest` | `ResponseEntity<byte[]>` | 导出 Excel |
| `/bug/batch-delete` | POST | `BugBatchRequest` | void | 批量删除 |
| `/bug/comment/add` | POST | `BugComment` | `BugComment` | 评论 |
| `/bug/comment/get/{bugId}` | GET | 路径参数 | `List<BugCommentDTO>` | 评论列表 |
| `/bug/attachment/*` | 各方式 | - | - | 附件管理 |
| `/bug/history/page` | POST | `OperationHistoryRequest` | `Pager<List<OperationHistoryDTO>>` | 变更历史 |
| `/bug/trash/*` | - | - | - | 回收站 |
| `/bug/case/*` | - | - | - | 关联用例 |

---

## 五、test-plan（测试计划）模块 —— 核心接口

类路径 `@RequestMapping("/test-plan")`（主）、`/test-plan-execute`（执行）、`/test-plan/report`（报告）。

| 路径 | 请求方式 | 入参 | 返回值 | 说明 |
|------|------|------|--------|------|
| `/test-plan/page` | POST | `TestPlanPageRequest` | `Pager<List<TestPlanResponse>>` | 计划分页 |
| `/test-plan/add` | POST | `TestPlanCreateRequest` | `TestPlan` | 新增计划 |
| `/test-plan/update` | POST | `TestPlanUpdateRequest` | `TestPlan` | 更新 |
| `/test-plan/{id}` | GET | 路径参数 | `TestPlanDetailResponse` | 详情 |
| `/test-plan/copy/{id}` | GET | 路径参数 | `TestPlanSingleOperationResponse` | 复制 |
| `/test-plan/archived/{id}` | GET | 路径参数 | void | 归档/取消归档 |
| `/test-plan/delete/{id}` | GET | 路径参数 | void | 删除 |
| `/test-plan/association/*` | POST | 关联请求 | `Pager` | 关联功能/接口/场景用例 |
| `/test-plan/api/case/*`、`/test-plan/api/scenario/*`、`/test-plan/functional/case/*` | 各方式 | - | - | 计划内各类型用例管理/执行/关联缺陷 |
| `/test-plan-execute/single` | POST | `TestPlanExecuteRequest` | String(执行ID) | 执行整个计划 |
| `/test-plan-execute/batch` | POST | Batch 请求 | void | 批量执行 |
| `/test-plan/report/page` | POST | `TestPlanReportPageRequest` | `Pager<List<TestPlanReportPageResponse>>` | 计划报告分页 |
| `/test-plan/report/get/{reportId}` | GET | 路径参数 | `TestPlanReportDetailResponse` | 报告详情 |
| `/test-plan/report/auto-gen`、`/manual-gen` | POST | 请求体 | String | 自动/手动生成报告 |
| `/test-plan/module/tree/{projectId}` | GET | 路径参数 | `List<BaseTreeNode>` | 计划模块树 |
| `/task/center/plan/*` | 各方式 | - | - | 计划任务中心 |

---

## 六、project-management（项目管理）模块 —— 核心接口

| 路径 | 请求方式 | 说明 |
|---|---|---|
| `/project/page` | POST | 项目分页 |
| `/project/add` | POST | 新增项目 |
| `/project/update` | POST | 更新 |
| `/project/member/*` | 各方式 | 成员管理 |
| `/project/application/*` | 各方式 | 项目应用配置 |
| `/project/environment/*`（EnvironmentController） | 各方式 | 环境管理 |
| `/project/file/*`（FileManagementController） | 各方式 | 文件管理 |
| `/project/global/params/*` | 各方式 | 全局参数 |
| `/project/custom/field/*` | 各方式 | 自定义字段 |
| `/project/template/*` | 各方式 | 模板管理 |
| `/project/robot/*` | 各方式 | 机器人通知 |
| `/project/task-center/*` | 各方式 | 项目任务中心 |
| `/project/status/flow/setting/*` | 各方式 | 状态流设置 |
| `/project/file-module/*` | 各方式 | 文件模块 |
| `/project/file/association/*` | 各方式 | 文件关联 |
| `/project/file/repository/*` | 各方式 | 文件仓库 |

---

## 七、system-setting（系统设置）模块 —— 核心接口

| 路径 | 请求方式 | 说明 |
|---|---|---|
| `/system/organization/*`、`/organization/*` | 各方式 | 组织管理 |
| `/system/project/*` | 各方式 | 系统级项目 |
| `/system/user/*` | 各方式 | 用户管理 |
| `/user/role/global`、`/user/role/organization`、`/user/role/project` | 各方式 | 三层角色管理 |
| `/test/resource/pool/*` | 各方式 | 测试资源池 |
| `/plugin/*` | 各方式 | 插件管理 |
| `/service/integration/*` | 各方式 | 服务集成（Jira/TAPD 等） |
| `/ai/config/*` | 各方式 | AI 配置 |
| `/operation/log/*` | 各方式 | 操作日志 |
| `/system/version` | GET | 系统版本 |
| `/license/*` | 各方式 | License |
| `/personal/*` | 各方式 | 个人中心 |
| `/notification/*`、`notice/*` | 各方式 | 消息通知 |
| `/dashboard/*`、`/dashboard/my`、`/dashboard/todo` | 各方式 | 工作台/待办 |

---

## 八、关键业务实现逻辑要点

### 1. 接口执行链路（debug/run）
```
Controller(debug) 
 → ApiDebugService/ApiTestCaseRunService/ApiScenarioRunService.debug()
 → ApiExecuteService.getApiResourceRunRequest()  # 组装 AbstractMsTestElement 测试元素树
 → ApiExecuteService.getApiParamConfig()          # 解析环境变量/全局参数
 → ApiExecuteService.getTaskRequest()             # 构造 TaskRequestDTO（含 TaskInfo/TaskItem）
 → ApiExecuteService.apiExecute()                 # 提交到执行引擎（本地或资源池）
返回 TaskRequestDTO（含 reportId/taskId），前端据此轮询/订阅实时结果
```
关键点：`saveResult=false + realTime=true` 为调试模式；`frontendDebug=true` 本地执行。

### 2. 分页查询范式
```java
Page<Object> page = PageHelper.startPage(req.getCurrent(), req.getPageSize(), sort);
return PageUtils.setPageInfo(page, service.query(...));
```
返回 `Pager<T>`（含 list / total / current / pageSize）。

### 3. 权限与归属校验
- `@RequiresPermissions` 控制功能权限。
- `@CheckOwner(resourceId = "#request.getProjectId()", resourceType = "project")` 校验资源归属，防止越权。

### 4. 软删除/回收站
- 各资源表含 `deleted`（0/1）字段；`delete-to-gc` 置 1 进回收站；`recover` 置 0 恢复；`delete` 彻底删除。

### 5. 异步任务中心
- 长耗时操作（执行、导入导出、批量运行）提交异步任务，任务中心按 项目/组织/系统 三个维度分页查询实时状态，支持停止。

---

## 九、对 test-gen-agent（仿 TestPilot）的接口对照建议

当前工作区 `test-gen-agent` 采用 FastAPI 实现，前端用 TestPilot v3.x 风格路径，后端业务路径做了适配映射。建议对照本报告校验以下映射完整性：

| TestPilot 真实路径 | test-gen-agent 现有适配路径 | 建议核对项 |
|---|---|---|
| `/api/definition/*` | `/api/apitest/definitions/*` | 增删改查/回收站/复制/导入导出是否齐备 |
| `/api/case/*` | `/api/apitest/cases/*` | run/debug 是否支持环境绑定、实时报告 |
| `/api/scenario/*` | `/api/apitest/scenarios/*` | 步骤树/运行/调试/定时 |
| `/api/definition/mock/*` + `/mock-server/**` | `/api/apitest/mocks/*` + `/mock/**` | Mock 命中规则 |
| `/api/environment/*` | `/api/apitest/environments/*` | 环境变量/全局参数 |
| `/api/report/*` | `/api/apitest/reports/*` | 报告详情/分享 |
| `/task/center/api/*` | 任务中心 | 实时任务/停止 |

---

## 十、接口清单索引（全量路径速查）

完整接口方法级清单（各模块）已通过脚本提取，关键清单如下：

**api-test（21 Controller）**：见本文第二章各子章节，覆盖接口定义/用例/场景/Mock/调试/报告/任务中心。
**case-management（15）**：`/functional/case/*`、`/functional/mind/*`、`/case/review/*`、`/review/functional/case/*`、`/functional/case/ai|comment|attachment|demand|relationship|review|test|trash|module|test` 等。
**bug-management（6）**：`/bug*`、`/bug/comment`、`/bug/attachment`、`/bug/history`、`/bug/trash`、`/bug/case`。
**test-plan（13）**：`/test-plan*`、`/test-plan-execute`、`/test-plan/report*`、`/task/center/plan/*`、各用例子模块。
**project-management（22）**：`/project*`、`/project/file*`、`/project/environment*`（EnvironmentController 路径见类）、`/user/role/project`、`/file/preview`、`/notice/*` 等。
**system-setting（41）**：`/system/*`、`/organization/*`、`/user/*`、`/plugin`、`/test/resource/pool`、`/service/integration`、`/ai/config`、`/operation/log`、`/dashboard/*` 等。
**dashboard（3）**：`/dashboard`、`/dashboard/my`、`/dashboard/todo`。
