"""用例领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，
进而驱动审计日志、版本快照、通知、索引等副作用（跨聚合/跨域解耦）。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class CaseCreated(DomainEvent):
    def __init__(self, case_id: str, operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.operator = operator
        self.title = ""


class CaseTitleChanged(DomainEvent):
    def __init__(self, case_id: str, old_title: str, new_title: str, operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.old_title = old_title
        self.new_title = new_title
        self.operator = operator


class CaseStatusChanged(DomainEvent):
    def __init__(self, case_id: str, old_status: str, new_status: str, operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.old_status = old_status
        self.new_status = new_status
        self.operator = operator


class CaseSoftDeleted(DomainEvent):
    def __init__(self, case_id: str, operator: str = "system", reason: str = ""):
        super().__init__(aggregate_id=case_id)
        self.operator = operator
        self.reason = reason


class CaseRestored(DomainEvent):
    def __init__(self, case_id: str, operator: str = "system"):
        super().__init__(aggregate_id=case_id)
        self.operator = operator


class CaseVersionCreated(DomainEvent):
    def __init__(self, case_id: str, version: int, operator: str = "system", change_desc: str = ""):
        super().__init__(aggregate_id=case_id)
        self.version = version
        self.operator = operator
        self.change_desc = change_desc


class CaseReviewed(DomainEvent):
    def __init__(self, case_id: str, outcome: str, reviewer: str = ""):
        super().__init__(aggregate_id=case_id)
        self.outcome = outcome
        self.reviewer = reviewer


class CaseRolledBack(DomainEvent):
    def __init__(self, case_id: str, version: int, operator: str = ""):
        super().__init__(aggregate_id=case_id)
        self.version = version
        self.operator = operator
