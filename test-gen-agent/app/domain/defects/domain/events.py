"""缺陷领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，驱动通知/审计/
指标统计等跨域副作用解耦。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class DefectCreated(DomainEvent):
    def __init__(self, defect_id: str, title: str = "", operator: str = "system"):
        super().__init__(aggregate_id=defect_id)
        self.title = title
        self.operator = operator


class DefectTitleChanged(DomainEvent):
    def __init__(self, defect_id: str, old_title: str, new_title: str, operator: str = "system"):
        super().__init__(aggregate_id=defect_id)
        self.old_title = old_title
        self.new_title = new_title
        self.operator = operator


class DefectContentChanged(DomainEvent):
    def __init__(self, defect_id: str, field: str, operator: str = "system"):
        super().__init__(aggregate_id=defect_id)
        self.field = field
        self.operator = operator


class DefectSeverityChanged(DomainEvent):
    def __init__(self, defect_id: str, old_severity: str, new_severity: str, operator: str = "system"):
        super().__init__(aggregate_id=defect_id)
        self.old_severity = old_severity
        self.new_severity = new_severity
        self.operator = operator


class DefectStatusChanged(DomainEvent):
    def __init__(self, defect_id: str, old_status: str, new_status: str, operator: str = "system"):
        super().__init__(aggregate_id=defect_id)
        self.old_status = old_status
        self.new_status = new_status
        self.operator = operator


class DefectSoftDeleted(DomainEvent):
    def __init__(self, defect_id: str, operator: str = "system"):
        super().__init__(aggregate_id=defect_id)
        self.operator = operator


class DefectRestored(DomainEvent):
    def __init__(self, defect_id: str, operator: str = "system"):
        super().__init__(aggregate_id=defect_id)
        self.operator = operator
