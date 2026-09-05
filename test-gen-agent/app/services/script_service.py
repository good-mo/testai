# app/services/script_service.py
"""脚本健康度业务逻辑层（script 域 DDD 接入 · 阶段 C 薄门面）。

业务规则已下沉到 script 域领域层（`app/domain/script/`：健康度评分、
状态判定、定位器修复策略）。本四层 Service 收敛为对 DDD 应用服务
`script_app_service` 的薄委托门面，仅保留既有方法签名以兼容调用方 /
便于回滚。对外语义与返回形状与重构前保持一致（复用 DDD 聚合 to_dict）。

> 推荐调用方直接使用 `script_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Optional

from app.domain.common.exceptions import AggregateNotFound, DomainException
from app.domain.script.application.dto import (
    AutoRepairCommand,
    DeleteCommand,
    EvaluateSelectorCommand,
    GetCommand,
    ListExecutionsCommand,
    RecommendStrategyCommand,
    RecordExecutionCommand,
    RegisterCommand,
    ScriptQuery,
    UpdateCommand,
)
from app.domain.script.application.script_app_service import script_app_service as _ddd


class ScriptService:
    """脚本健康度服务（script 域 DDD 薄门面）。"""

    def list(self, status: Optional[str] = None, framework: Optional[str] = None,
             search: Optional[str] = None, limit: int = 100, offset: int = 0) -> list:
        # framework 为历史宽松入参，列表口径不按框架过滤（与重构前一致）
        return _ddd.list(ScriptQuery(
            status=status, search=search, limit=limit, offset=offset,
        ))

    def register(self, name: str, file_path: str = "", framework: str = "",
                 description: str = "", locators: list = None) -> dict:
        return _ddd.register(RegisterCommand(
            name=name, file_path=file_path, framework=framework,
            description=description, locators=locators or [],
        ))

    def get(self, script_id: str) -> Optional[dict]:
        try:
            return _ddd.get(GetCommand(script_id=script_id))
        except AggregateNotFound:
            return None

    def update(self, script_id: str, **kwargs) -> Optional[dict]:
        try:
            return _ddd.update(UpdateCommand(script_id=script_id, **kwargs))
        except AggregateNotFound:
            return None

    def delete(self, script_id: str) -> bool:
        try:
            return _ddd.delete(DeleteCommand(script_id=script_id))
        except AggregateNotFound:
            return False

    def record_execution(self, script_id: str, success: bool = True,
                         duration: float = 0, error_type: str = "",
                         error_message: str = "", locator_failures: list = None) -> dict:
        return _ddd.record_execution(RecordExecutionCommand(
            script_id=script_id, success=success, duration=duration,
            error_type=error_type, error_message=error_message,
            locator_failures=locator_failures,
        ))

    def auto_repair(self, script_id: str, locator_name: str) -> dict:
        return _ddd.auto_repair(AutoRepairCommand(
            script_id=script_id, locator_name=locator_name,
        ))

    def list_executions(self, script_id: str, limit: int = 20) -> list:
        return _ddd.list_executions(ListExecutionsCommand(
            script_id=script_id, limit=limit,
        ))

    def evaluate_selector(self, strategy: str, selector: str) -> dict:
        return _ddd.evaluate_selector(EvaluateSelectorCommand(
            strategy=strategy, selector=selector,
        ))

    def recommend_strategy(self, selector: str, strategy: str) -> dict:
        return _ddd.recommend_strategy(RecommendStrategyCommand(
            selector=selector, strategy=strategy,
        ))

    def get_stats(self) -> dict:
        return _ddd.get_stats()


script_service = ScriptService()
