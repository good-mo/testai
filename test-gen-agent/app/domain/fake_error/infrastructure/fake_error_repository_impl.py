"""误报规则聚合仓储实现。

将既有 `app.repositories.fake_error_repo`（fake_error_rules 表唯一权威读写）
封装为面向 `FakeErrorRule` 聚合的仓储，供 `fake_error_app_service` 消费。
落库列语义与聚合字段一一对应，保证「聚合 -> DB -> 聚合」round-trip 无漂移。
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.fake_error.domain.entities.error_rule import FakeErrorRule
from app.repositories import fake_error_repo


class FakeErrorRepoAdapter:
    """将既有 fake_error_repo 封装为面向 FakeErrorRule 的仓储。"""

    def next_id(self) -> str:
        return str(uuid.uuid4())

    def save(self, rule: FakeErrorRule) -> FakeErrorRule:
        """按聚合根 id 落库（INSERT OR REPLACE，兼作新增与整体更新）。"""
        data = [{
            "id": rule.id.value,
            "name": rule.name,
            "type": rule.tag_type,
            "enable": rule.enable,
            "respType": rule.resp_type,
            "relation": rule.relation,
            "expression": rule.expression,
            "ruleResult": rule.rule_result,
            "createUser": rule.create_user,
            "projectId": rule.project_id,
        }]
        fake_error_repo.add_rules(data, project_id=rule.project_id)
        return rule

    def get(self, rule_id: str) -> Optional[FakeErrorRule]:
        for r in self.list():
            if r.id.value == rule_id:
                return r
        return None

    def list(self, project_id: str = "") -> List[FakeErrorRule]:
        rows = fake_error_repo.list_rules(project_id)
        return [FakeErrorRule.from_dict(r) for r in rows]

    def delete(self, rule_id: str) -> bool:
        fake_error_repo.delete_rules([rule_id])
        return True

    def update_enable(self, rule_ids: List[str], enable: bool) -> None:
        fake_error_repo.update_enable(rule_ids, enable)

    def get_enabled_count(self, project_id: str = "") -> int:
        return fake_error_repo.get_enabled_count(project_id)


fake_error_repo_adapter = FakeErrorRepoAdapter()

__all__ = ["FakeErrorRepoAdapter", "fake_error_repo_adapter"]
