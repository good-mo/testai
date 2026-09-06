# app/services/fake_error_service.py
"""误报规则（错误注入）业务逻辑层（fake_error 域 DDD 接入 · 阶段 C 薄门面）。

误报规则业务已收敛到 fake_error 域 DDD 应用服务 `fake_error_app_service`
（见 `app/domain/fake_error/`，聚合根 `FakeErrorRule`）。本 Service 收敛为对
DDD 应用门面的**薄委托门面**，仅保留既有方法签名以兼容
`app/routers/test_compat.py` / `app/routers/test_resources.py` 等调用方，
返回结构与重构前一致（DDD 门面底层复用既有 `fake_error_repo`，规则 round-trip、
展示文本 ruleResult/typeList/updateTime 语义零变化），对外 API 零回归、可回滚。

> 推荐调用方直接使用 `fake_error_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.domain.fake_error.application.dto import (
    AddRulesCommand,
    DeleteRulesCommand,
    ListRulesCommand,
    SaveRuleItem,
    UpdateEnableCommand,
    UpdateRulesCommand,
)
from app.domain.fake_error.application.fake_error_app_service import (
    fake_error_app_service as _ddd,
)


class FakeErrorService:
    """误报规则（错误注入）管理服务：router 层唯一业务入口（DDD 薄门面）。"""

    # ── 查询 ──────────────────────────────────────────────
    def list_rules(self, project_id: str = "") -> List[Dict[str, Any]]:
        """获取指定项目下的错误注入规则列表。"""
        return _ddd.list(ListRulesCommand(project_id=project_id))

    def get_enabled_count(self, project_id: str = "") -> int:
        """获取启用中的误报规则数量。"""
        return _ddd.get_enabled_count(project_id)

    # ── 变更 ──────────────────────────────────────────────
    def add_rules(self, items: List[Dict[str, Any]], project_id: str = "") -> List[Dict[str, Any]]:
        """新增错误注入规则。"""
        return _ddd.add_rules(AddRulesCommand(
            items=[_to_item(i) for i in items],
            project_id=project_id,
        ))

    def update_rules(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """更新错误注入规则。"""
        return _ddd.update_rules(UpdateRulesCommand(
            items=[_to_item(i) for i in items],
        ))

    def delete_rules(self, ids: List[str]) -> None:
        """删除错误注入规则。"""
        _ddd.delete(DeleteRulesCommand(ids=ids))

    def update_enable(self, ids: List[str], enable: bool) -> None:
        """启用/禁用错误注入规则。"""
        _ddd.update_enable(UpdateEnableCommand(ids=ids, enable=bool(enable)))


def _to_item(raw: Dict[str, Any]) -> SaveRuleItem:
    """将 router/前端传入的 dict 归一为应用层 SaveRuleItem。"""
    return SaveRuleItem(
        id=raw.get("id", "") or "",
        name=raw.get("name", "") or "",
        type=raw.get("type", "") or "",
        enable=raw.get("enable", True) if "enable" in raw else True,
        respType=raw.get("respType", "") or "",
        relation=raw.get("relation", "") or "",
        expression=raw.get("expression", "") or "",
        projectId=raw.get("projectId", "") or "",
    )


# 模块级单例（与其它 service 风格一致）
fake_error_service = FakeErrorService()


__all__ = ["fake_error_service", "FakeErrorService"]
