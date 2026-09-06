# app/services/environment_service.py
"""环境管理业务逻辑层（environment 域 DDD 接入 · 阶段 C 薄门面）。

本 Service 作为路由器与 `environment_app_service` 之间的**薄门面**：
纯 CRUD / 回收站 / 告警 / Docker 拉起-停止-健康检查 均已委托 DDD 应用服务
（含 Docker 运维副作用编排）。

对外返回 schema 与迁移前一致，调用方零改动、可回滚。
"""
from __future__ import annotations

from dataclasses import fields as _dataclass_fields
from typing import Any, Dict, Optional

from app.core.exceptions import NotFoundError
from app.domain.common.exceptions import AggregateNotFound, DomainException
from app.domain.environment.application.dto import (
    CreateCommand,
    DeleteCommand,
    EnvQuery,
    GetCommand,
    HealthCheckCommand,
    LaunchCommand,
    ListAlertsQuery,
    ResolveAlertCommand,
    StopCommand,
    UpdateCommand,
)
from app.domain.environment.application.environment_app_service import (
    environment_app_service as _ddd,
)
from app.repositories.environment_repo import EnvironmentRepo


class EnvironmentService:
    """环境管理服务（DDD 薄门面 + 兼容层）。"""

    # ── CRUD（委托 DDD 门面）─────────────────────────────
    @staticmethod
    def _filter_create(data: dict) -> dict:
        """过滤掉 DDD CreateCommand 之外的宽松入参（如 base_url）。"""
        allowed = {f.name for f in _dataclass_fields(CreateCommand)}
        return {k: v for k, v in data.items() if k in allowed}

    def create(self, data: dict) -> dict:
        return _ddd.create(CreateCommand(**self._filter_create(data)))

    def get(self, env_id: str) -> Optional[dict]:
        try:
            return _ddd.get(GetCommand(env_id=env_id))
        except AggregateNotFound:
            return None

    def list(self, search: str = "", status: str = "", env_type: str = "") -> list:
        return _ddd.list(EnvQuery(search=search, status=status, env_type=env_type))

    def update(self, env_id: str, data: dict) -> Optional[dict]:
        try:
            return _ddd.update(UpdateCommand(env_id=env_id, data=data))
        except AggregateNotFound:
            return None

    def delete(self, env_id: str) -> bool:
        try:
            return _ddd.delete(DeleteCommand(env_id=env_id))
        except (AggregateNotFound, DomainException):
            return False

    # ── 环境生命周期（Docker 运维副作用已下沉到 DDD 应用服务）──
    def launch(self, env_id: str) -> Dict[str, Any]:
        """拉起环境容器（经 DDD 应用服务，Docker 副作用由 infra 编排）。"""
        self._ensure_exists(env_id)
        return _ddd.launch(LaunchCommand(env_id=env_id))

    def stop(self, env_id: str) -> Dict[str, Any]:
        """停止环境容器（经 DDD 应用服务）。"""
        self._ensure_exists(env_id)
        return _ddd.stop(StopCommand(env_id=env_id))

    def health_check(self, env_id: str) -> Dict[str, Any]:
        """检查环境健康状况（经 DDD 应用服务）。"""
        try:
            _ddd.get(GetCommand(env_id=env_id))
        except AggregateNotFound:
            return {"success": False, "error": f"环境 {env_id} 不存在"}
        return _ddd.health_check(HealthCheckCommand(env_id=env_id))

    def health_check_all(self) -> Dict[str, Any]:
        """批量检查所有环境健康状态（经 DDD 应用服务）。"""
        return _ddd.health_check_all()

    @staticmethod
    def _ensure_exists(env_id: str) -> dict:
        """校验环境存在，不存在抛 NotFoundError（由全局处理器转 404）。"""
        env = EnvironmentRepo.get(env_id)
        if not env or env.get("deleted"):
            raise NotFoundError(f"环境 {env_id} 不存在")
        return env

    # ── 回收站（委托 DDD 门面）────────────────────────────
    def list_trash(self) -> list:
        return _ddd.list_trash()

    def restore(self, env_id: str) -> bool:
        return _ddd.restore(env_id)

    def trash(self, env_id: str) -> bool:
        return _ddd.trash(env_id)

    def purge(self, env_id: str) -> bool:
        return _ddd.purge(env_id)

    # ── 告警（委托 DDD 门面）────────────────────────────
    def list_alerts(self, limit: int = 50, level: str = "") -> list:
        return _ddd.list_alerts(ListAlertsQuery(limit=limit, level=level))

    def resolve_alert(self, alert_id: str) -> bool:
        return _ddd.resolve_alert(ResolveAlertCommand(alert_id=alert_id))

    def get_stats(self) -> dict:
        return _ddd.get_stats()


environment_service = EnvironmentService()

__all__ = ["environment_service", "EnvironmentService"]
