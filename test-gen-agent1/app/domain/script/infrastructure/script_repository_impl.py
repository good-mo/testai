"""脚本聚合仓储实现（Adapter / Anti-Corruption Layer）。

将既有 ScriptRepo 封装为面向聚合 Script 的仓储接口。
"""
from __future__ import annotations

from typing import List, Optional

from app.domain.script.domain.entities.script import Script
from app.repositories.script_repo import ScriptRepo


class ScriptRepoAdapter:
    """将既有 ScriptRepo 封装为面向聚合 Script 的仓储。"""

    def register(self, script: Script) -> Script:
        row = ScriptRepo.register(
            name=script.name,
            file_path=script.file_path,
            framework=script.framework.value,
            description=script.description,
            locators=script.locators,
        )
        return Script.from_dict(row)

    def get(self, script_id: str) -> Optional[Script]:
        row = ScriptRepo.get(script_id)
        return Script.from_dict(row) if row else None

    def list(self, status: Optional[str] = None, search: Optional[str] = None,
             limit: int = 100, offset: int = 0) -> List[Script]:
        rows = ScriptRepo.list(status=status, search=search,
                               limit=limit, offset=offset)
        return [Script.from_dict(r) for r in rows]

    def update(self, script: Script) -> Optional[Script]:
        row = ScriptRepo.update(
            script.id.value,
            name=script.name,
            file_path=script.file_path,
            framework=script.framework.value,
            description=script.description,
            locators=script.locators,
            total_runs=script.total_runs,
            success_runs=script.success_runs,
            fail_runs=script.fail_runs,
            last_run_at=script.last_run_at,
            last_status=script.last_status,
            health_score=script.health_score,
            status=script.status.value,
        )
        return Script.from_dict(row) if row else None

    def delete(self, script_id: str) -> bool:
        return ScriptRepo.delete(script_id)

    def record_execution(self, script_id: str, success: bool, duration: float,
                         error_type: str, error_message: str,
                         locator_failures: Optional[list]) -> dict:
        return ScriptRepo.record_execution(
            script_id=script_id, success=success, duration=duration,
            error_type=error_type, error_message=error_message,
            locator_failures=locator_failures,
        )

    def list_executions(self, script_id: str, limit: int = 20) -> list:
        return ScriptRepo.list_executions(script_id, limit=limit)

    def stats(self) -> dict:
        return ScriptRepo.stats()

    def evaluate_selector(self, strategy: str, selector: str) -> dict:
        return ScriptRepo.evaluate_selector(strategy, selector)

    def recommend_strategy(self, selector: str, strategy: str) -> dict:
        return ScriptRepo.recommend_strategy(selector, strategy)

    def auto_repair(self, script_id: str, locator_name: str) -> dict:
        return ScriptRepo.auto_repair(script_id, locator_name)


__all__ = ["ScriptRepoAdapter"]
