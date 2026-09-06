"""接口测试领域层（domain layer）。

仅表达业务概念与规则（ApiDefinition/ApiCase/Scenario/ApiMock 聚合、
断言/脚本/变量提取等不变量），不依赖 FastAPI / sqlite / 具体存储实现。
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
from app.domain.apitest.domain.value_objects.priority import Priority
from app.domain.apitest.domain.value_objects.protocol import Protocol, ProtocolEnum
from app.domain.apitest.domain.value_objects.status import (
    ApiCaseStatus,
    ApiCaseStatusEnum,
    ScenarioStatus,
    ScenarioStatusEnum,
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
    "Priority",
    "Protocol",
    "ProtocolEnum",
    "ApiCaseStatus",
    "ApiCaseStatusEnum",
    "ScenarioStatus",
    "ScenarioStatusEnum",
]
