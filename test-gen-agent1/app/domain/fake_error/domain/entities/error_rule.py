"""误报规则聚合根 FakeErrorRule（错误注入规则）。"""
from __future__ import annotations

import time
from typing import Optional, Sequence, Union

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.time_utils import MS_PER_SECOND, time_from_row
from app.domain.fake_error.domain.events import (
    FakeErrorCreated,
    FakeErrorUpdated,
)

# 支持的响应类型
RESP_TYPE_HEADERS = "RESPONSE_HEADERS"
RESP_TYPE_DATA = "RESPONSE_DATA"
RESP_TYPE_CODE = "RESPONSE_CODE"

# 匹配类型枚举
RELATION_CONTAINS = "CONTAINS"
RELATION_NOT_CONTAINS = "NOT_CONTAINS"
RELATION_EQUALS = "EQUALS"
RELATION_START_WITH = "START_WITH"
RELATION_END_WITH = "END_WITH"

# 展示标签（域内枚举 → 展示文案），供 to_dict / ruleResult 派生使用。
RESP_TYPE_LABEL = {
    RESP_TYPE_HEADERS: "Response Headers",
    RESP_TYPE_DATA: "Response Data",
    RESP_TYPE_CODE: "Response Code",
}
RELATION_LABEL = {
    RELATION_CONTAINS: "包含",
    RELATION_NOT_CONTAINS: "不包含",
    RELATION_EQUALS: "等于",
    RELATION_START_WITH: "开始于",
    RELATION_END_WITH: "结束于",
}


def _norm_tag_type(tag_type) -> str:
    """将标签字段归一为逗号分隔字符串（list -> 逗号串）。"""
    if isinstance(tag_type, (list, tuple)):
        return ",".join(str(t) for t in tag_type if t is not None)
    return str(tag_type or "")


def build_rule_result(resp_type: str, relation: str, expression: str) -> str:
    """依据响应类型 / 匹配关系 / 表达式派生前端展示文本（与既有契约一致）。"""
    hdr = RESP_TYPE_LABEL.get(resp_type, resp_type or "")
    rel = RELATION_LABEL.get(relation, relation or "")
    return " ".join(p for p in (hdr, rel, expression) if p)


class FakeErrorRule(AggregateRoot):
    """误报规则聚合根。

    不变量：名称非空；rule_result 若未显式提供则按 resp_type/relation/expression
    派生，保证落库展示文本与领域枚举一致。
    """

    def __init__(
        self,
        *,
        rule_id: str,
        project_id: str = "",
        name: str = "",
        enable: bool = True,
        tag_type: Union[str, Sequence[str]] = "",
        resp_type: str = "",
        relation: str = "",
        expression: str = "",
        rule_result: str = "",
        create_user: str = "",
        create_time: Optional[float] = None,
        update_time: Optional[float] = None,
        _created: bool = False,
    ):
        if not rule_id:
            raise DomainValidationError("规则 ID 不能为空")
        if not (name or "").strip():
            raise DomainValidationError("规则名称不能为空")
        self.id = Identifier.of(rule_id)
        self._project_id = project_id or ""
        self._name = (name or "").strip()
        self._enable = bool(enable)
        self._tag_type = _norm_tag_type(tag_type)
        self._resp_type = resp_type or ""
        self._relation = relation or ""
        self._expression = expression or ""
        self._rule_result = rule_result or build_rule_result(
            self._resp_type, self._relation, self._expression
        )
        self._create_user = create_user or "admin"
        now = time.time()
        self._create_time = create_time if create_time is not None else now
        self._update_time = update_time if update_time is not None else now
        self._domain_events = []
        self.version = 0
        if _created:
            self.record_event(FakeErrorCreated(self.id.value, self._name))

    # ── 只读属性 ──────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name
    @property
    def project_id(self) -> str:
        return self._project_id
    @property
    def enable(self) -> bool:
        return self._enable
    @property
    def tag_type(self) -> str:
        return self._tag_type
    @property
    def resp_type(self) -> str:
        return self._resp_type
    @property
    def relation(self) -> str:
        return self._relation
    @property
    def expression(self) -> str:
        return self._expression
    @property
    def create_user(self) -> str:
        return self._create_user
    @property
    def create_time(self) -> float:
        return self._create_time
    @property
    def update_time(self) -> float:
        return self._update_time
    @property
    def rule_result(self) -> str:
        return self._rule_result

    # ── 行为 ──────────────────────────────────────────
    def enable_rule(self) -> None:
        self._enable = True
        self._touch()

    def disable_rule(self) -> None:
        self._enable = False
        self._touch()

    def update_rule(
        self,
        *,
        name: Optional[str] = None,
        tag_type: Optional[Union[str, Sequence[str]]] = None,
        resp_type: Optional[str] = None,
        relation: Optional[str] = None,
        expression: Optional[str] = None,
        rule_result: Optional[str] = None,
        enable: Optional[bool] = None,
        create_user: Optional[str] = None,
    ) -> None:
        changed = False
        if name is not None:
            if not (name or "").strip():
                raise DomainValidationError("规则名称不能为空")
            self._name = (name or "").strip()
            changed = True
        if tag_type is not None:
            self._tag_type = _norm_tag_type(tag_type)
            changed = True
        if resp_type is not None:
            self._resp_type = resp_type
            changed = True
        if relation is not None:
            self._relation = relation
            changed = True
        if expression is not None:
            self._expression = expression
            changed = True
        if rule_result is not None:
            self._rule_result = rule_result
        elif resp_type is not None or relation is not None or expression is not None:
            # 显式携带展示文本时沿用；否则按新枚举重新派生，避免展示文本与字段漂移
            self._rule_result = build_rule_result(
                self._resp_type, self._relation, self._expression
            )
            changed = True
        if enable is not None:
            self._enable = bool(enable)
            changed = True
        if create_user is not None:
            self._create_user = create_user
            changed = True
        if changed:
            self.record_event(FakeErrorUpdated(self.id.value))
        self._touch()

    def _touch(self) -> None:
        self._update_time = time.time()

    # ── 序列化 ────────────────────────────────────────
    def to_dict(self) -> dict:
        """导出为与既有 router 消费契约一致的前端项结构。

        字段含 id/projectId/name/enable/type/typeList/respType/relation/
        expression/ruleResult/createUser/updateTime（毫秒）。与旧
        `fake_error_repo._row_to_item` 对齐，保证门面接线后行为零回归。
        """
        return {
            "id": self.id.value,
            "projectId": self._project_id,
            "name": self._name,
            "enable": self._enable,
            "type": self._tag_type,
            "typeList": self._tag_type.split(",") if self._tag_type else [],
            "respType": self._resp_type,
            "relation": self._relation,
            "expression": self._expression,
            "ruleResult": self._rule_result,
            "createUser": self._create_user,
            "updateTime": int((self._update_time or 0) * MS_PER_SECOND),
        }

    @staticmethod
    def from_dict(data: dict) -> "FakeErrorRule":
        """从既有 DB 行（snake_case）或前端项（camelCase）重建聚合。"""
        tag_type = (
            data.get("type", "")
            or data.get("label", "")
            or data.get("tag_type", "")
            or ""
        )
        # DB 行内若已带 typeList 数组则取之（保持多标签）
        type_list = data.get("typeList") or []
        if type_list and not (tag_type or "").strip():
            tag_type = ",".join(str(t) for t in type_list if t is not None)
        resp_type = data.get("respType", "") or data.get("resp_type", "") or ""
        relation = data.get("relation", "") or ""
        expression = data.get("expression", "") or data.get("rule", "") or ""
        rule_result = (
            data.get("ruleResult", "")
            or data.get("rule_result", "")
            or ""
        )
        return FakeErrorRule(
            rule_id=str(data.get("id") or ""),
            project_id=data.get("projectId", "") or data.get("project_id", "") or "",
            name=data.get("name", ""),
            enable=bool(data.get("enable", True)),
            tag_type=tag_type,
            resp_type=resp_type,
            relation=relation,
            expression=expression,
            rule_result=rule_result,
            create_user=data.get("createUser", "") or data.get("create_user", "") or "admin",
            create_time=time_from_row(
                data, "create_time", "createTime",
                default=time_from_row(data, "created_at", "createAt"),
            ),
            update_time=time_from_row(
                data, "update_time", "updateTime",
                default=time_from_row(data, "updated_at", "updateAt"),
            ),
        )


__all__ = [
    "FakeErrorRule",
    "RESP_TYPE_HEADERS",
    "RESP_TYPE_DATA",
    "RESP_TYPE_CODE",
    "RESP_TYPE_LABEL",
    "RELATION_LABEL",
    "build_rule_result",
]
