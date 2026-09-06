"""接口测试 限界上下文（Bounded Context）。

聚合根：`ApiDefinition` / `ApiCase` / `Scenario` / `ApiMock`
内聚：断言(Assertion)、脚本(Script)、变量提取(VariableExtractor)、
控制器(Controller) 等值对象。
对应现有：`services/apitest_service.py` `repositories/apitest_repo.py`

    app/domain/apitest/domain/          领域层（与存储/框架零依赖）
        entities/                      ApiDefinition/ApiCase/Scenario/ApiMock 聚合根
        value_objects/                 值对象（Priority/Protocol/ApiStatus）
        services/                      领域服务（状态机策略）
        events.py                      领域事件
        repository.py                  聚合仓储接口（Repository Protocol）
        exceptions.py                  领域异常
    app/domain/apitest/application/     应用层（用例编排，事务边界）
        apitest_app_service.py          应用服务门面
        dto.py                         输入/输出传输对象
    app/domain/apitest/infrastructure/  基础设施层（对接既有 Repo 存储）
        apitest_repository_impl.py      聚合仓储实现（防腐层）

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.apitest.domain.entities.api_case import ApiCase
from app.domain.apitest.domain.entities.api_definition import ApiDefinition
from app.domain.apitest.domain.entities.mock import ApiMock
from app.domain.apitest.domain.entities.scenario import Scenario
from app.domain.apitest.domain.repository import (
    ApiCaseRepository,
    ApiDefinitionRepository,
    MockRepository,
    ScenarioRepository,
)

__all__ = [
    "ApiDefinition",
    "ApiCase",
    "Scenario",
    "ApiMock",
    "ApiDefinitionRepository",
    "ApiCaseRepository",
    "ScenarioRepository",
    "MockRepository",
]
