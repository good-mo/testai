"""脚本领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class ScriptRegistered(DomainEvent):
    """脚本已注册。"""

    def __init__(self, script_id: str, name: str, framework: str = "pytest"):
        super().__init__(aggregate_id=script_id)
        self.name = name
        self.framework = framework


class ScriptUpdated(DomainEvent):
    """脚本已更新。"""

    def __init__(self, script_id: str, action: str = "meta"):
        super().__init__(aggregate_id=script_id)
        self.action = action


class ScriptDeleted(DomainEvent):
    """脚本已删除。"""

    def __init__(self, script_id: str):
        super().__init__(aggregate_id=script_id)


class ScriptExecutionRecorded(DomainEvent):
    """脚本执行已记录。"""

    def __init__(self, script_id: str, success: bool = True,
                 health_score: float = 100.0, status: str = "healthy"):
        super().__init__(aggregate_id=script_id)
        self.success = success
        self.health_score = health_score
        self.status = status


class ScriptAutoRepaired(DomainEvent):
    """脚本定位器已自动修复。"""

    def __init__(self, script_id: str, locator_name: str,
                 new_strategy: str = ""):
        super().__init__(aggregate_id=script_id)
        self.locator_name = locator_name
        self.new_strategy = new_strategy


__all__ = [
    "ScriptRegistered", "ScriptUpdated", "ScriptDeleted",
    "ScriptExecutionRecorded", "ScriptAutoRepaired",
]
