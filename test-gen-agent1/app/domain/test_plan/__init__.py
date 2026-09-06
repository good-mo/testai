"""测试计划 限界上下文（Bounded Context）。

聚合根：`TestPlan`
内聚：阶段(Stage)、用例编排(TestPlanCase) 等子实体/值对象。
对应现有：`test_plan/*` `repositories/test_plan_repo.py`

    app/domain/test_plan/domain/          领域层（与存储/框架零依赖）
        entities/                      TestPlan 聚合根及子实体
        value_objects/                 值对象
        services/                      领域服务（跨聚合逻辑）
        events.py                      领域事件
        repository.py                  聚合仓储接口（Repository Protocol）
        exceptions.py                  领域异常
    app/domain/test_plan/application/     应用层（用例编排，事务边界）
        test_plan_app_service.py          应用服务门面
        dto.py                           输入/输出传输对象
    app/domain/test_plan/infrastructure/  基础设施层（对接既有 Repo 存储）
        test_plan_repository_impl.py      聚合仓储实现（防腐层）

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
