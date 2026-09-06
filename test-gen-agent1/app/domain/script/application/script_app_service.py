"""脚本应用服务（Application Service / Use Case 门面）。"""
from __future__ import annotations

import uuid
from typing import Optional

from app.domain.common.domain_events import event_bus
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
from app.domain.script.domain.entities.script import Script
from app.domain.script.domain.exceptions import ScriptNotFound
from app.domain.script.infrastructure.script_repository_impl import ScriptRepoAdapter


class ScriptAppService:
    """脚本用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or ScriptRepoAdapter()

    def register(self, cmd: RegisterCommand) -> dict:
        script = Script(
            script_id=uuid.uuid4().hex[:12],
            name=cmd.name,
            file_path=cmd.file_path,
            framework=cmd.framework,
            description=cmd.description,
            locators=cmd.locators,
            _registered=True,
        )
        saved = self._repo.register(script)
        self._publish(script)
        return saved.to_dict()

    def get(self, cmd: GetCommand) -> Optional[dict]:
        s = self._repo.get(cmd.script_id)
        if s is None:
            raise ScriptNotFound(f"脚本 {cmd.script_id} 不存在")
        return s.to_dict()

    def list(self, query: ScriptQuery) -> list:
        scripts = self._repo.list(
            status=query.status, search=query.search,
            limit=query.limit, offset=query.offset,
        )
        return [s.to_dict() for s in scripts]

    def update(self, cmd: UpdateCommand) -> Optional[dict]:
        script = self._repo.get(cmd.script_id)
        if not script:
            raise ScriptNotFound(f"脚本 {cmd.script_id} 不存在")
        kwargs = {}
        if cmd.name is not None:
            kwargs["name"] = cmd.name
        if cmd.file_path is not None:
            kwargs["file_path"] = cmd.file_path
        if cmd.framework is not None:
            kwargs["framework"] = cmd.framework
        if cmd.description is not None:
            kwargs["description"] = cmd.description
        if cmd.locators is not None:
            kwargs["locators"] = cmd.locators
        script.update_meta(**kwargs)
        saved = self._repo.update(script)
        self._publish(script)
        return saved.to_dict() if saved else None

    def delete(self, cmd: DeleteCommand) -> bool:
        script = self._repo.get(cmd.script_id)
        if script:
            script.mark_deleted()
            self._publish(script)
        return self._repo.delete(cmd.script_id)

    def record_execution(self, cmd: RecordExecutionCommand) -> dict:
        script = self._repo.get(cmd.script_id)
        if not script:
            raise ScriptNotFound(f"脚本 {cmd.script_id} 不存在")
        script.record_execution(
            success=cmd.success, duration=cmd.duration,
            error_type=cmd.error_type, error_message=cmd.error_message,
            locator_failures=cmd.locator_failures,
        )
        self._repo.update(script)
        result = self._repo.record_execution(
            script_id=cmd.script_id, success=cmd.success,
            duration=cmd.duration, error_type=cmd.error_type,
            error_message=cmd.error_message,
            locator_failures=cmd.locator_failures,
        )
        self._publish(script)
        return result

    def auto_repair(self, cmd: AutoRepairCommand) -> dict:
        return self._repo.auto_repair(cmd.script_id, cmd.locator_name)

    def list_executions(self, cmd: ListExecutionsCommand) -> list:
        return self._repo.list_executions(cmd.script_id, limit=cmd.limit)

    def evaluate_selector(self, cmd: EvaluateSelectorCommand) -> dict:
        return self._repo.evaluate_selector(cmd.strategy, cmd.selector)

    def recommend_strategy(self, cmd: RecommendStrategyCommand) -> dict:
        return self._repo.recommend_strategy(cmd.selector, cmd.strategy)

    def get_stats(self) -> dict:
        return self._repo.stats()

    @staticmethod
    def _publish(script: Script) -> None:
        for ev in script.pull_domain_events():
            event_bus.dispatch(ev)


# 单例门面
script_app_service = ScriptAppService()

__all__ = ["ScriptAppService", "script_app_service"]
