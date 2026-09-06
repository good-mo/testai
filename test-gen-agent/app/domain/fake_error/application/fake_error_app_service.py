"""误报规则应用服务。

修复说明：
  - 修改 import：从 FakeErrorRepoAdapter 改为 FakeErrorRepositoryImpl
  - 使用模块级单例 fake_error_repository
  - 其他代码完全不变（方法签名和业务逻辑保持一致）
"""
from __future__ import annotations

import uuid

from app.domain.fake_error.application.dto import (
    AddRulesCommand,
    DeleteRulesCommand,
    ListRulesCommand,
    UpdateEnableCommand,
    UpdateRulesCommand,
)
from app.domain.fake_error.domain.entities.error_rule import FakeErrorRule

# ── 修复：改 import ──────────────────────────────────────────
from app.domain.fake_error.infrastructure.fake_error_repository_impl import (
    FakeErrorRepositoryImpl,
    fake_error_repository,
)


class FakeErrorAppService:
    """误报规则用例编排服务。"""

    def __init__(self, repo=None):
        # ── 修复：使用新的 Repository 单例 ──────────────────
        self._repo = repo or fake_error_repository

    def list(self, cmd: ListRulesCommand) -> list:
        rules = self._repo.list(cmd.project_id)
        return [r.to_dict() for r in rules]

    def add_rules(self, cmd: AddRulesCommand) -> list:
        results = []
        for item in cmd.items:
            rule_id = item.id or str(uuid.uuid4())
            rule = FakeErrorRule(
                rule_id=rule_id,
                project_id=item.projectId or cmd.project_id,
                name=item.name,
                enable=item.enable,
                tag_type=item.type,
                resp_type=item.respType,
                relation=item.relation,
                expression=item.expression,
                _created=True,
            )
            saved = self._repo.save(rule)
            results.append(saved.to_dict())
        return results

    def update_rules(self, cmd: UpdateRulesCommand) -> list:
        results = []
        for item in cmd.items:
            rule_id = item.id
            existing = self._repo.get(rule_id) if rule_id else None
            if not existing:
                continue
            existing.update_rule(
                name=item.name or None,
                tag_type=item.type or None,
                resp_type=item.respType or None,
                relation=item.relation or None,
                expression=item.expression or None,
                enable=item.enable if hasattr(item, 'enable') else None,
            )
            saved = self._repo.save(existing)
            results.append(saved.to_dict())
        return results

    def delete(self, cmd: DeleteRulesCommand) -> None:
        for rid in cmd.ids:
            self._repo.delete(rid)

    def update_enable(self, cmd: UpdateEnableCommand) -> None:
        self._repo.update_enable(cmd.ids, cmd.enable)

    def get_enabled_count(self, project_id: str = "") -> int:
        return self._repo.get_enabled_count(project_id)


fake_error_app_service = FakeErrorAppService()