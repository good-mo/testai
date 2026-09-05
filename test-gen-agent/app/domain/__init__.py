"""DDD 领域包（Domain-Driven Design）。

按限界上下文（Bounded Context）分包，每个上下文内部遵循
「domain → application → infrastructure」严格依赖方向：

    app/domain/common/             DDD 通用原语（Entity/ValueObject/事件/异常）
    app/domain/cases/              限界上下文：用例管理（试点，已完成）
    app/domain/defects/            限界上下文：缺陷管理（已落地）
    app/domain/case_review/        限界上下文：用例评审（已落地）
    app/domain/performance/        限界上下文：性能测试（已落地）
    app/domain/project/            限界上下文：项目管理（已落地）
    app/domain/test_plan/          限界上下文：测试计划（已落地）
    app/domain/datafactory/        限界上下文：数据工厂（已落地）
    app/domain/test_insight/       限界上下文：测试洞察（已落地）
    app/domain/generation/         限界上下文：生成编排（已落地）
    app/domain/apitest/            限界上下文：接口测试（已落地）
    app/domain/runs/               限界上下文：任务运行/TaskCenter（通用支撑域，已落地）
    app/domain/report/             限界上下文：报告（已落地）
    app/domain/identity/           限界上下文：身份与访问/组织/成员/认证（通用支撑域，已落地）
    app/domain/template/           限界上下文：字段模板管理（通用支撑域，已落地）
    app/domain/script/             限界上下文：脚本健康度（通用支撑域，已落地）
    app/domain/environment/        限界上下文：环境管理（通用支撑域，已落地）
    app/domain/message/            限界上下文：消息通知（通用支撑域，已落地）
    app/domain/file/               限界上下文：文件管理（通用支撑域，已落地）

    # 以下为 2026-09 新增批量支撑域
    app/domain/ai_config/          限界上下文：AI 用例生成配置（已落地）
    app/domain/ai_model/           限界上下文：AI 模型源管理（已落地）
    app/domain/debug/              限界上下文：接口调试暂存（已落地）
    app/domain/display_config/     限界上下文：展示配置（页面/登录页 UI 配置）（已落地）
    app/domain/export_task/        限界上下文：导出任务注册表（已落地）
    app/domain/fake_error/         限界上下文：误报规则/错误注入（已落地）
    app/domain/project_app_config/ 限界上下文：项目应用配置（菜单/模块配置）（已落地）
    app/domain/project_version/    限界上下文：项目版本管理（已落地）
    app/domain/resource_pool/      限界上下文：资源池管理（已落地）
    app/domain/user_view/          限界上下文：用户自定义视图（已落地）
    app/domain/workflow/           限界上下文：工作流状态管理（已落地）
    app/domain/admin_system/       限界上下文：系统管理（组织启停/成员移除）（已落地）
    app/domain/task_center/        限界上下文：任务中心协调（exec-task/schedule）（已落地）
    app/domain/frontend_api/       限界上下文：前端兼容接口测试适配（已落地）
    app/domain/functional_export/  限界上下文：功能用例导出（Excel/XMind）（已落地）

依赖铁律：
  - domain 层禁止 import FastAPI / sqlite / services / repositories。
  - domain 只定义 Port 接口，具体实现交给 infrastructure。
  - application 依赖 domain 接口编程，可注入替身做单测。
  - 跨上下文通信一律通过领域事件，禁止直接 import 对方 service。
"""
