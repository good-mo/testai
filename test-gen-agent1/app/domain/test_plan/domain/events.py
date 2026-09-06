"""测试计划领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，驱动统计/审计/
通知等跨域副作用解耦。
"""
from __future__ import annotations

from typing import List

from app.domain.common.domain_events import DomainEvent


class TestPlanCreated(DomainEvent):
    def __init__(self, plan_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=plan_id)
        self.name = name
        self.operator = operator


class TestPlanUpdated(DomainEvent):
    def __init__(self, plan_id: str, fields: List[str], operator: str = "system"):
        super().__init__(aggregate_id=plan_id)
        self.fields = fields
        self.operator = operator


class TestPlanStatusChanged(DomainEvent):
    def __init__(self, plan_id: str, old_status: str, new_status: str, operator: str = "system"):
        super().__init__(aggregate_id=plan_id)
        self.old_status = old_status
        self.new_status = new_status
        self.operator = operator


class TestPlanArchived(DomainEvent):
    def __init__(self, plan_id: str, operator: str = "system"):
        super().__init__(aggregate_id=plan_id)
        self.operator = operator


class TestPlanDeleted(DomainEvent):
    def __init__(self, plan_id: str, operator: str = "system"):
        super().__init__(aggregate_id=plan_id)
        self.operator = operator


class TestPlanCaseAdded(DomainEvent):
    def __init__(self, plan_id: str, case_id: str, case_type: str = "functional",
                 operator: str = "system"):
        super().__init__(aggregate_id=plan_id)
        self.case_id = case_id
        self.case_type = case_type
        self.operator = operator


class TestPlanCaseRemoved(DomainEvent):
    def __init__(self, plan_id: str, rel_id: str, operator: str = "system"):
        super().__init__(aggregate_id=plan_id)
        self.rel_id = rel_id
        self.operator = operator


class TestPlanCaseStatusChanged(DomainEvent):
    def __init__(self, plan_id: str, rel_id: str, old_status: str, new_status: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=plan_id)
        self.rel_id = rel_id
        self.old_status = old_status
        self.new_status = new_status
        self.operator = operator


class TestPlanCaseReordered(DomainEvent):
    def __init__(self, plan_id: str, ordered_ids: List[str], operator: str = "system"):
        super().__init__(aggregate_id=plan_id)
        self.ordered_ids = list(ordered_ids)
        self.operator = operator
