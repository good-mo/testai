"""数据工厂领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，驱动清理索引、
审计、缓存等跨域副作用解耦。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class DataTemplateCreated(DomainEvent):
    """数据模板已创建。"""

    def __init__(self, template_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=template_id)
        self.name = name
        self.operator = operator


class DataTemplateContentChanged(DomainEvent):
    """数据模板内容/元信息被更新（改名/描述/类别/字段/依赖/标签）。"""

    def __init__(self, template_id: str, field: str, operator: str = "system"):
        super().__init__(aggregate_id=template_id)
        self.field = field
        self.operator = operator


class DataTemplateStatusChanged(DomainEvent):
    """数据模板启用/停用。"""

    def __init__(self, template_id: str, old_status: str, new_status: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=template_id)
        self.old_status = old_status
        self.new_status = new_status
        self.operator = operator


class DataTemplateDeleted(DomainEvent):
    """数据模板被删除。"""

    def __init__(self, template_id: str, operator: str = "system"):
        super().__init__(aggregate_id=template_id)
        self.operator = operator


class DataBatchGenerated(DomainEvent):
    """已按模板生成一批测试数据。"""

    def __init__(self, batch_id: str, template_id: str = "", batch_size: int = 1,
                 env_key: str = "", operator: str = "system"):
        super().__init__(aggregate_id=batch_id)
        self.template_id = template_id
        self.batch_size = batch_size
        self.env_key = env_key
        self.operator = operator


class DataBatchCleaned(DomainEvent):
    """生成批次的数据被清理。"""

    def __init__(self, batch_id: str, env_key: str = "", operator: str = "system"):
        super().__init__(aggregate_id=batch_id)
        self.env_key = env_key
        self.operator = operator


__all__ = [
    "DataTemplateCreated",
    "DataTemplateContentChanged",
    "DataTemplateStatusChanged",
    "DataTemplateDeleted",
    "DataBatchGenerated",
    "DataBatchCleaned",
]
