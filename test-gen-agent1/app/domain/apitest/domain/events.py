"""接口测试领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，
驱动审计日志、通知、索引等副作用（跨聚合/跨域解耦）。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


# ── ApiDefinition 事件 ──────────────────────────────────
class ApiDefinitionCreated(DomainEvent):
    """接口定义创建。"""

    def __init__(self, definition_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=definition_id)
        self.name = name
        self.operator = operator


class ApiDefinitionUpdated(DomainEvent):
    """接口定义内容更新。"""

    def __init__(self, definition_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=definition_id)
        self.name = name
        self.operator = operator


class ApiDefinitionRenamed(DomainEvent):
    """接口定义改名。"""

    def __init__(self, definition_id: str, old_name: str, new_name: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=definition_id)
        self.old_name = old_name
        self.new_name = new_name
        self.operator = operator


class ApiDefinitionSoftDeleted(DomainEvent):
    """接口定义软删除（进回收站）。"""

    def __init__(self, definition_id: str, operator: str = "system", reason: str = ""):
        super().__init__(aggregate_id=definition_id)
        self.operator = operator
        self.reason = reason


class ApiDefinitionRestored(DomainEvent):
    """接口定义从回收站恢复。"""

    def __init__(self, definition_id: str, operator: str = "system"):
        super().__init__(aggregate_id=definition_id)
        self.operator = operator


class ApiDefinitionVersionCreated(DomainEvent):
    """接口定义创建新版本。"""

    def __init__(self, definition_id: str, version: str = "",
                 operator: str = "system"):
        super().__init__(aggregate_id=definition_id)
        self.version = version
        self.operator = operator


# ── ApiCase 事件 ────────────────────────────────────────
class ApiCaseCreated(DomainEvent):
    """接口用例创建。"""

    def __init__(self, case_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.name = name
        self.operator = operator


class ApiCaseUpdated(DomainEvent):
    """接口用例内容更新。"""

    def __init__(self, case_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.name = name
        self.operator = operator


class ApiCaseRenamed(DomainEvent):
    """接口用例改名。"""

    def __init__(self, case_id: str, old_name: str, new_name: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.old_name = old_name
        self.new_name = new_name
        self.operator = operator


class ApiCaseStatusChanged(DomainEvent):
    """接口用例状态变更。"""

    def __init__(self, case_id: str, old_status: str, new_status: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.old_status = old_status
        self.new_status = new_status
        self.operator = operator


class ApiCasePriorityChanged(DomainEvent):
    """接口用例优先级变更。"""

    def __init__(self, case_id: str, old_priority: str, new_priority: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.old_priority = old_priority
        self.new_priority = new_priority
        self.operator = operator


class ApiCaseSoftDeleted(DomainEvent):
    """接口用例软删除。"""

    def __init__(self, case_id: str, operator: str = "system", reason: str = ""):
        super().__init__(aggregate_id=case_id)
        self.operator = operator
        self.reason = reason


class ApiCaseRestored(DomainEvent):
    """接口用例恢复。"""

    def __init__(self, case_id: str, operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.operator = operator


# ── Scenario 事件 ───────────────────────────────────────
class ScenarioCreated(DomainEvent):
    """接口场景创建。"""

    def __init__(self, scenario_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=scenario_id)
        self.name = name
        self.operator = operator


class ScenarioUpdated(DomainEvent):
    """接口场景更新。"""

    def __init__(self, scenario_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=scenario_id)
        self.name = name
        self.operator = operator


class ScenarioRenamed(DomainEvent):
    """接口场景改名。"""

    def __init__(self, scenario_id: str, old_name: str, new_name: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=scenario_id)
        self.old_name = old_name
        self.new_name = new_name
        self.operator = operator


class ScenarioStatusChanged(DomainEvent):
    """接口场景状态变更。"""

    def __init__(self, scenario_id: str, old_status: str, new_status: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=scenario_id)
        self.old_status = old_status
        self.new_status = new_status
        self.operator = operator


class ScenarioSoftDeleted(DomainEvent):
    """接口场景软删除。"""

    def __init__(self, scenario_id: str, operator: str = "system", reason: str = ""):
        super().__init__(aggregate_id=scenario_id)
        self.operator = operator
        self.reason = reason


class ScenarioRestored(DomainEvent):
    """接口场景恢复。"""

    def __init__(self, scenario_id: str, operator: str = "system"):
        super().__init__(aggregate_id=scenario_id)
        self.operator = operator


# ── Mock 服务事件 ───────────────────────────────────────
class MockCreated(DomainEvent):
    """Mock 服务创建。"""

    def __init__(self, mock_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=mock_id)
        self.name = name
        self.operator = operator


class MockUpdated(DomainEvent):
    """Mock 服务内容更新。"""

    def __init__(self, mock_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=mock_id)
        self.name = name
        self.operator = operator


class MockActiveChanged(DomainEvent):
    """Mock 服务启用/禁用状态切换。"""

    def __init__(self, mock_id: str, old_active: bool, new_active: bool,
                 operator: str = "system"):
        super().__init__(aggregate_id=mock_id)
        self.old_active = old_active
        self.new_active = new_active
        self.operator = operator


class MockSoftDeleted(DomainEvent):
    """Mock 服务软删除（进回收站）。"""

    def __init__(self, mock_id: str, operator: str = "system", reason: str = ""):
        super().__init__(aggregate_id=mock_id)
        self.operator = operator
        self.reason = reason


class MockRestored(DomainEvent):
    """Mock 服务从回收站恢复。"""

    def __init__(self, mock_id: str, operator: str = "system"):
        super().__init__(aggregate_id=mock_id)
        self.operator = operator
