# app/models/__init__.py
"""Pydantic 数据模型（Phase 3 重构：请求体统一建档）。

各业务域的请求体模型独立建档为 `app/models/{domain}.py`：
- apitest.py      接口测试（定义/用例/场景/Mock/环境/模块/调试/导入）
- case_review.py  用例评审（评审头/关联用例/评审模块/批量评审）
- ai_config.py     AI 配置源与 AI 对话
- app_config.py    项目应用配置（project_app_config）
- auth.py         认证 / 用户 / 会话 / API Key / 成员
- case.py         功能用例
- datafactory.py  数据工厂
- debug.py         接口调试（Debug CRUD / 模块 / 执行 / curl 导入）
- defect.py       缺陷
- environment.py  环境
- file.py         文件 / 附件
- gap_fixes.py  补齐差异兼容（资源脚本执行/任务中心实时分页）
- integration.py   服务集成 / SSO 平台配置（we_com/ding_talk/lark/lark_suite）
- insights.py     测试洞察
- invitation.py   邀请注册
- other_compat.py  other 兼容（文档分享 /api/doc/share 与 LDAP 登录）
- organizations.py 组织（租户）
- project.py      项目
- plugins.py     插件管理（占位兼容路由）
- reports.py      报告中心
- runs.py         运行记录
- schemas.py      共享模型（迁移自 main.py，逐步收敛）
- platform.py     平台（授权 /license/*）
- scripts.py      脚本健康度
- task_center.py  任务中心（exec-task/schedule 批量操作与 cron 更新）
- test_plan.py    测试计划
- user_role.py     用户组 / 视图（用户角色）
- workflow.py     工作流（状态流：增删改/排序/流转/初始态结束态）
"""
