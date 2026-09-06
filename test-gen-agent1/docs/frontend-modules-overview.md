# 前端界面总览（15 大模块 / 75+ 页面）

> 基于 `frontend/src/router/routes/` 与 `frontend/src/api/requrls/` 自动整理。
> 生成时间：2026-09-01

---

## 模块总览

| # | 模块名称 | 路由前缀 | 页面数 | 主要功能 |
|---|---------|---------|-------|---------|
| 1 | 工作台 | `/workstation` | 4 | 首页概览 / 我的待办 / 我关注的 / 我创建的 |
| 2 | AI 用例生成 | `/ai-case-gen` | 3 | 用例生成 / 低代码生成 / 项目批量生成 |
| 3 | 测试计划 | `/test-plan` | 7 | 计划列表 / 报告 / 详情 / 配置 / 用例详情 |
| 4 | 用例管理 | `/case-management` | 9 | 功能用例 / 用例详情 / 创建成功 / 回收站 / 评审管理 |
| 5 | 接口测试-调试 | `/api-test/debug` | 1 | 接口调试 |
| 6 | 接口测试-管理 | `/api-test/management` | 2 | 接口定义管理 / 回收站 |
| 7 | 接口测试-场景 | `/api-test/scenario` | 3 | 场景编排 / 场景创建 / 场景回收站 |
| 8 | 接口测试-报告 | `/api-test/report` | 1 | 接口测试报告 |
| 9 | 缺陷管理 | `/bug-management` | 4 | 缺陷列表 / 创建编辑 / 创建成功 / 回收站 |
| 10 | 项目管理-权限 | `/project-management/permission` | 5 | 基本信息 / 菜单管理 / 项目版本 / 成员 / 用户组 |
| 11 | 项目管理-模板 | `/project-management/template` | 7 | 模板管理 / 字段设置 / 模板列表 / 用例模板 / 接口模板 / 缺陷模板 / 工作流 |
| 12 | 项目管理-功能 | `/project-management/*` | 5 | 文件管理 / 消息管理 / 公共脚本 / 误报规则 / 环境管理 |
| 13 | 系统设置-系统 | `/setting/system` | 10 | 用户 / 用户组 / 组织项目 / 参数 / 资源池 / 任务中心 / 插件 / 授权 / 日志 |
| 14 | 系统设置-组织 | `/setting/organization` | 9 | 成员 / 用户组 / 项目 / 服务集成 / 模板 / 任务中心 / 日志 |
| 15 | 分享/全页面 | `/share` `/fullPage` | 7 | 报告分享 / 文档分享 / PDF 导出 |

**合计：15 大模块，77 个页面**

---

## 模块详细页面与 API 映射

### 1. 工作台（4 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 首页 | `/workstation/home` | `workbench/homePage/index.vue` | `/dashboard/project_view`, `/dashboard/case_count`, `/dashboard/bug_count`, `/dashboard/api_count`, `/dashboard/my/*` |
| 我的待办 | `/workstation/wait` | `workbench/myToDo/index.vue` | `/dashboard/todo/*/page` |
| 我关注的 | `/workstation/followed` | `workbench/myFollowed/index.vue` | `/dashboard/my/followed/*` |
| 我创建的 | `/workstation/created` | `workbench/myCreated/index.vue` | `/dashboard/create_by_me` |

### 2. AI 用例生成（3 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 用例生成 | `/ai-case-gen/index` | `ai-case-gen/index.vue` | `/ai/*`, `/api/insights/*`, `/api/tasks` |
| 低代码生成 | `/ai-case-gen/lowcode` | `ai-case-gen/lowcode.vue` | `/ai/conversation/*`, `/api/insights/lowcode` |
| 项目批量生成 | `/ai-case-gen/project` | `ai-case-gen/project.vue` | `/api/insights/value`, `/project/scan/*` |

### 3. 测试计划（7 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 计划列表 | `/test-plan/testPlanIndex` | `test-plan/testPlan/index.vue` | `/test-plan/page`, `/test-plan/add`, `/test-plan/update` |
| 计划报告 | `/test-plan/testPlanReport` | `test-plan/report/index.vue` | `/api/test-plan/report/*` |
| 报告详情 | `/test-plan/testPlanReportDetail` | `test-plan/report/detail/detail.vue` | `/api/test-plan/report/detail/*` |
| 计划详情 | `/test-plan/testPlanIndexDetail` | `test-plan/testPlan/detail/index.vue` | `/test-plan/association/page`, `/test-plan/functional/case/page` |
| 报告配置 | `/test-plan/testPlanIndexConfig` | `test-plan/report/detail/configReport.vue` | `/api/test-plan/report/config/*` |
| 功能用例详情 | `/test-plan/testPlanIndexDetailFeatureCaseDetail` | `test-plan/testPlan/detail/featureCase/detail/index.vue` | `/test-plan/functional/case/*` |
| PDF 导出 | `/fullPage/testPlanExportPDF` | `test-plan/report/detail/exportPDF.vue` | `/api/test-plan/report/export/*` |

### 4. 用例管理（9 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 功能用例 | `/case-management/featureCase` | `case-management/caseManagementFeature/index.vue` | `/functional/case/page`, `/functional/case/add` |
| 用例详情 | `/case-management/featureCaseDetail` | `case-management/caseManagementFeature/components/caseDetail.vue` | `/functional/case/detail/*` |
| 创建成功 | `/case-management/featureCaseCreateSuccess` | `case-management/caseManagementFeature/components/createSuccess.vue` | - |
| 用例回收站 | `/case-management/featureCaseRecycle` | `case-management/caseManagementFeature/components/recycleCaseTable.vue` | `/functional/case/trash/page`, `/functional/case/trash/restore` |
| 评审列表 | `/case-management/caseManagementReview` | `case-management/caseReview/index.vue` | `/case/review/page`, `/case/review/add` |
| 创建评审 | `/case-management/caseManagementReviewCreate` | `case-management/caseReview/create.vue` | `/case/review/create` |
| 评审详情 | `/case-management/caseManagementReviewDetail` | `case-management/caseReview/detail.vue` | `/case/review/detail/*` |
| 评审用例详情 | `/case-management/caseManagementReviewDetailCaseDetail` | `case-management/caseReview/caseDetail.vue` | `/review/functional/case/detail/*` |
| 用例评审-回收站 | `/case-management/caseManagementReviewRecycle` | `case-management/caseReview/components/index/*` | `/case/review/trash/*` |

### 5-8. 接口测试（7 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 接口调试 | `/api-test/debug` | `api-test/debug/index.vue` | `/api/debug/*` |
| 接口定义 | `/api-test/management` | `api-test/management/index.vue` | `/api/definition/page`, `/api/definition/add`, `/api/definition/update` |
| 定义回收站 | `/api-test/recycle` | `api-test/management/recycle.vue` | `/api/definition/delete-to-gc/*` |
| 场景编排 | `/api-test/scenario` | `api-test/scenario/index.vue` | `/api/scenario/page`, `/api/scenario/add` |
| 场景回收站 | `/api-test/scenario/recycle` | `api-test/scenario/recycle.vue` | `/api/scenario/delete-to-gc/*` |
| 接口报告 | `/api-test/report` | `api-test/report/index.vue` | `/api/report/page`, `/api/report/detail/*` |
| Mock 服务 | `/api-test/management` (tab) | `api-test/management/components/management/mock/*` | `/api/mock/*` |

### 9. 缺陷管理（4 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 缺陷列表 | `/bug-management/index` | `bug-management/index.vue` | `/bug/page`, `/bug/add`, `/bug/update` |
| 创建/编辑 | `/bug-management/detail` | `bug-management/createAndEditBug.vue` | `/bug/get/*`, `/bug/template/detail` |
| 创建成功 | `/bug-management/create-success` | `bug-management/createSuccess.vue` | - |
| 回收站 | `/bug-management/recycle` | `bug-management/recycle.vue` | `/bug/trash/page`, `/bug/trash/restore` |

### 10-12. 项目管理（17 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 基本信息 | `/project-management/permission/basicInfo` | `projectAndPermission/basicInfos/index.vue` | `/project/update`, `/project/get/*` |
| 菜单管理 | `/project-management/permission/menuManagement` | `projectAndPermission/menuManagement/menuManagement.vue` | `/project/application/*` |
| 项目版本 | `/project-management/permission/projectVersion` | `projectAndPermission/projectVersion/index.vue` | `/project/version/*` |
| 成员管理 | `/project-management/permission/member` | `projectAndPermission/member/index.vue` | `/project/member/*` |
| 用户组 | `/project-management/permission/projectUserGroup` | `projectAndPermission/userGroup/projectUserGroup.vue` | `/project/group/*` |
| 模板管理 | `/project-management/projectManagementTemplate` | `template/index.vue` | `/project/template/*` |
| 模板字段 | `/project-management/projectManagementTemplateField` | `template/components/projectFieldSetting.vue` | `/project/template/field/*` |
| 模板列表 | `/project-management/projectManagementTemplateList` | `template/components/templateManagement.vue` | `/project/template/list/*` |
| 用例模板 | `/project-management/projectManagementTemplateCaseDetail` | `template/components/detail.vue` | `/project/template/detail/*` |
| 接口模板 | `/project-management/projectManagementTemplateApiDetail` | `template/components/detail.vue` | `/project/template/detail/*` |
| 缺陷模板 | `/project-management/projectManagementTemplateBugDetail` | `template/components/detail.vue` | `/project/template/detail/*` |
| 模板工作流 | `/project-management/templateWorkFlow` | `template/components/workFlowTableIndex.vue` | `/project/template/workflow/*` |
| 文件管理 | `/project-management/fileManagement` | `fileManagement/index.vue` | `/project/file/*` |
| 消息管理 | `/project-management/messageManagement` | `messageManagement/index.vue` | `/project/notification/*` |
| 公共脚本 | `/project-management/commonScript` | `commonScript/index.vue` | `/project/custom/func/*` |
| 误报规则 | `/project-management/errorReportRule` | `projectAndPermission/menuManagement/components/falseAlermRule.vue` | `/project/application/error-report/*` |
| 环境管理 | `/project-management/environmentManagement` | `environmental/index.vue` | `/project/environment/*` |

### 13. 系统设置-系统（10 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 用户管理 | `/setting/system/user` | `system/user/index.vue` | `/system/user/*` |
| 用户组 | `/setting/system/usergroup` | `system/usergroup/systemUserGroup.vue` | `/system/user/group/*` |
| 组织项目 | `/setting/system/organization-and-project` | `system/organizationAndProject/index.vue` | `/system/organization/*`, `/system/project/*` |
| 系统参数 | `/setting/system/parameter` | `system/config/index.vue` | `/system/parameter/*` |
| 资源池 | `/setting/system/resourcePool` | `system/resourcePool/index.vue` | `/system/resource-pool/*` |
| 资源池详情 | `/setting/system/resourcePoolDetail` | `system/resourcePool/detail.vue` | `/system/resource-pool/detail/*` |
| 任务中心 | `/setting/system/taskCenter` | `system/taskCenter/index.vue` | `/system/task-center/*` |
| 插件管理 | `/setting/system/pluginManager` | `system/pluginManager/index.vue` | `/system/plugin/*` |
| 授权管理 | `/setting/system/authorizedmanagement` | `system/authorizedManagement/index.vue` | `/system/license/*` |
| 系统日志 | `/setting/system/log` | `system/log/index.vue` | `/system/log/*` |

### 14. 系统设置-组织（9 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 成员管理 | `/setting/organization/member` | `organization/member/index.vue` | `/organization/member/*` |
| 用户组 | `/setting/organization/usergroup` | `organization/usergroup/orgUserGroup.vue` | `/organization/user/group/*` |
| 项目 | `/setting/organization/project` | `organization/project/orgProject.vue` | `/organization/project/*` |
| 服务集成 | `/setting/organization/serviceIntegration` | `organization/serviceIntegration/index.vue` | `/organization/service/*` |
| 模板 | `/setting/organization/template` | `organization/template/index.vue` | `/organization/template/*` |
| 模板字段 | `/setting/organization/templateFiledSetting` | `organization/template/components/ordFieldSetting.vue` | `/organization/template/field/*` |
| 模板管理 | `/setting/organization/templateManagement` | `organization/template/components/templateManagement.vue` | `/organization/template/list/*` |
| 任务中心 | `/setting/organization/taskCenter` | `organization/taskCenter/index.vue` | `/organization/task-center/*` |
| 组织日志 | `/setting/organization/log` | `organization/log/index.vue` | `/organization/log/*` |

### 15. 分享/全页面（7 页面）

| 页面 | 路由 | 视图文件 | 核心 API |
|------|------|---------|---------|
| 场景报告分享 | `/share/shareReportScenario` | `api-test/report/shareSceneIndex.vue` | `/share/report/scenario/*` |
| 用例报告分享 | `/share/shareReportCase` | `api-test/report/shareCaseIndex.vue` | `/share/report/case/*` |
| 计划报告分享 | `/share/shareReportTestPlan` | `test-plan/report/detail/sharePlanReportIndex.vue` | `/share/report/test-plan/*` |
| 接口文档分享 | `/share/shareDefinitionApi` | `api-test/management/components/management/api/shareApiDocIndex.vue` | `/share/definition/api/*` |
| 计划 PDF | `/fullPage/testPlanExportPDF` | `test-plan/report/detail/exportPDF.vue` | `/api/test-plan/report/export/*` |
| 场景 PDF | `/fullPage/scenarioExportPDF` | `api-test/report/exportScenarioPDF.vue` | `/api/report/scenario/export/*` |
| 用例 PDF | `/fullPage/apiCaseExportPDF` | `api-test/report/exportCasePDF.vue` | `/api/report/case/export/*` |

---

## 前端 API 调用统计

- 前端 URL 定义数：**1055**
- 覆盖的模块：**38** 个 API 文件
- 后端已注册路由：**1636** 条
- 前端调用路径契约对齐：**100%** ✅

| 模块 | API 文件 | URL 数 |
|------|---------|-------|
| 接口测试管理 | `api-test/management.ts` | 119 |
| 测试计划 | `test-plan/testPlan.ts` | 94 |
| 功能用例 | `case-management/featureCase.ts` | 89 |
| 任务中心 | `taskCenter.ts` | 62 |
| 场景 | `api-test/scenario.ts` | 51 |
| 缺陷管理 | `bug-management.ts` | 50 |
| 模板 | `setting/template.ts` | 45 |
| 报告 | `api-test/report.ts` | 25 |
| 组织项目 | `setting/organizationAndProject.ts` | 45 |
| 用户 | `user.ts` | 43 |
| 工作台 | `workbench.ts` | 36 |
| 用例评审 | `case-management/caseReview.ts` | 34 |
| 文件管理 | `project-management/fileManagement.ts` | 31 |
| 系统配置 | `setting/config.ts` | 25 |
| 环境管理 | `project-management/envManagement.ts` | 25 |
| 二维码 | `setting/qrCode.ts` | 21 |
| 接口调试 | `api-test/debug.ts` | 16 |
| 公共脚本 | `project-management/commonScript.ts` | 16 |
| 组织成员 | `setting/member.ts` | 13 |
| 项目成员 | `project-management/projectMember.ts` | 12 |
| 消息管理 | `project-management/messageManagement.ts` | 11 |
| 用户组 | `setting/usergroup.ts` | 10 |
| 项目用户组 | `project-management/usergroup.ts` | 10 |
| 公共 API | `api-test/common.ts` | 9 |
| 项目版本 | `project-management/projectVersion.ts` | 9 |
| AI 用例生成 | `ai-case-gen.ts` | 8 |
| 系统日志 | `setting/log.ts` | 8 |
| 资源池 | `setting/resourcePool.ts` | 8 |
| 服务集成 | `setting/serviceIntegration.ts` | 8 |
| AI | `ai.ts` | 6 |
| 插件 | `setting/plugin.ts` | 6 |
| 系统 | `system.ts` | 5 |
| 项目 | `project-management/project.ts` | 3 |
| 基本信息 | `project-management/basicInfo.ts` | 2 |
| 授权管理 | `setting/authorizedManagement.ts` | 2 |
