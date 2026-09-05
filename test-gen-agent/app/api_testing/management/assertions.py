# -*- coding: utf-8 -*-
"""app.api_testing.management.assertions 子模块（断言规则管理，行为不变）。

Repository 下沉说明：
断言规则（assertion_rules 表）的纯数据访问 CRUD SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo，本模块退化为兼容门面。
"""
from typing import List, Optional

from app.repositories.apitest_repo import ApitestRepo


def create_assertion_rule(
    name: str,
    rule_type: str = "text",
    target: str = "",
    expression: str = "",
    expected: str = "",
    description: str = "",
) -> dict:
    return ApitestRepo.create_assertion_rule(
        name=name, rule_type=rule_type, target=target,
        expression=expression, expected=expected, description=description,
    )


def get_assertion_rule(rule_id: str) -> Optional[dict]:
    return ApitestRepo.get_assertion_rule(rule_id)


def list_assertion_rules(limit: int = 100) -> List[dict]:
    return ApitestRepo.list_assertion_rules(limit=limit)


def delete_assertion_rule(rule_id: str) -> bool:
    return ApitestRepo.delete_assertion_rule(rule_id)
