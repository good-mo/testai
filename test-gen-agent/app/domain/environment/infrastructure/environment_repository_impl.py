"""环境聚合仓储实现（Adapter / Anti-Corruption Layer）。"""
from __future__ import annotations

from typing import List, Optional

from app.domain.environment.domain.entities.environment import Environment
from app.domain.environment.infrastructure.environment_store import EnvironmentRepo


class EnvironmentRepoAdapter:
    """将既有 EnvironmentRepo 封装为面向聚合 Environment 的仓储。"""

    def create(self, env: Environment) -> Environment:
        data = env.to_dict()
        row = EnvironmentRepo.create(data)
        return Environment.from_dict(row) if row else env

    def get(self, env_id: str) -> Optional[Environment]:
        row = EnvironmentRepo.get(env_id)
        return Environment.from_dict(row) if row else None

    def list(self, search: str = "", status: str = "",
             env_type: str = "") -> List[Environment]:
        rows = EnvironmentRepo.list(search=search, status=status, env_type=env_type)
        return [Environment.from_dict(r) for r in rows]

    def update(self, env: Environment) -> Optional[Environment]:
        data = env.to_dict()
        row = EnvironmentRepo.update(env.id.value, data)
        return Environment.from_dict(row) if row else None

    def delete(self, env_id: str, permanent: bool = False) -> bool:
        return EnvironmentRepo.delete(env_id, permanent=permanent)

    def list_trash(self) -> List[dict]:
        return EnvironmentRepo.list_trash()

    def restore(self, env_id: str) -> bool:
        return EnvironmentRepo.restore(env_id)

    def trash(self, env_id: str) -> bool:
        return EnvironmentRepo.trash(env_id)

    def purge(self, env_id: str) -> bool:
        return EnvironmentRepo.purge(env_id)

    def create_alert(self, env_id: str, env_name: str, level: str,
                     message: str, detail: str = "") -> dict:
        return EnvironmentRepo.create_alert(env_id, env_name, level, message, detail)

    def list_alerts(self, limit: int = 50, level: str = "") -> list:
        return EnvironmentRepo.list_alerts(limit=limit, level=level)

    def resolve_alert(self, alert_id: str) -> bool:
        return EnvironmentRepo.resolve_alert(alert_id)

    def get_stats(self) -> dict:
        return EnvironmentRepo.get_alerts_stats()


__all__ = ["EnvironmentRepoAdapter"]
