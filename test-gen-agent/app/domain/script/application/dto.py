"""脚本应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RegisterCommand:
    """注册脚本。"""
    name: str
    file_path: str = ""
    framework: str = "pytest"
    description: str = ""
    locators: list = None


@dataclass
class ScriptQuery:
    """脚本列表查询。"""
    status: Optional[str] = None
    search: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass
class UpdateCommand:
    """更新脚本。"""
    script_id: str
    name: Optional[str] = None
    file_path: Optional[str] = None
    framework: Optional[str] = None
    description: Optional[str] = None
    locators: Optional[list] = None


@dataclass
class GetCommand:
    """获取脚本。"""
    script_id: str


@dataclass
class DeleteCommand:
    """删除脚本。"""
    script_id: str


@dataclass
class RecordExecutionCommand:
    """记录执行。"""
    script_id: str
    success: bool = True
    duration: float = 0
    error_type: str = ""
    error_message: str = ""
    locator_failures: Optional[list] = None


@dataclass
class AutoRepairCommand:
    """自动修复。"""
    script_id: str
    locator_name: str


@dataclass
class ListExecutionsCommand:
    """列出执行记录。"""
    script_id: str
    limit: int = 20


@dataclass
class EvaluateSelectorCommand:
    """评估选择器。"""
    strategy: str
    selector: str


@dataclass
class RecommendStrategyCommand:
    """推荐策略。"""
    selector: str
    strategy: str = "css"


__all__ = [
    "RegisterCommand", "ScriptQuery", "UpdateCommand", "GetCommand",
    "DeleteCommand", "RecordExecutionCommand", "AutoRepairCommand",
    "ListExecutionsCommand", "EvaluateSelectorCommand", "RecommendStrategyCommand",
]
