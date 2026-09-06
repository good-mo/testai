"""项目管理 限界上下文（Bounded Context）。

聚合根：`Project`
内聚：成员(ProjectMember)等子实体/值对象；版本(ProjectVersion)、环境
(ProjectEnv)、应用配置(ProjectAppConfig) 由各自仓储在 id 级关联管理。
对应现有：`services/project_service.py` `repositories/project_repo.py`

    app/domain/project/domain/          领域层（与存储/框架零依赖）
        entities/project.py             Project 聚合根（生命周期+成员）
        value_objects/                  状态/角色/语言/成员值对象
        services/project_policy.py      生命周期策略（状态机）
        events.py                       领域事件
        repository.py                   聚合仓储接口（Repository Protocol）
        exceptions.py                   领域异常
    app/domain/project/application/     应用层（用例编排，事务边界）
        project_app_service.py          应用服务门面
        dto.py                          输入/输出传输对象
    app/domain/project/infrastructure/  基础设施层（对接既有 Repo 存储）
        project_repository_impl.py      聚合仓储实现（防腐层）

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
