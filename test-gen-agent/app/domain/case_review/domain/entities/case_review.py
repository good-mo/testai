"""用例评审聚合根 CaseReview。

聚合边界内的组成：
  - CaseReview（聚合根，评审会话头：名称 / 状态 / 评审人 / 通过规则 / 模块）
  - 若干子值对象：ReviewStatus / ReviewPassRule
  - 关联用例（CaseLink）以列表形式内聚于聚合，随评审一起存取

职责：守护评审会话的完整性与业务不变量。所有变更必须经由聚合根方法，
禁止从外部直接改字段；业务命令（改名 / 改状态 / 关联用例 / 更新评审结果 /
软删除 / 复制）在校验通过后返回领域事件，供应用层落库 + 发布。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.domain.case_review.domain.events import (
    CaseLinkedToReview,
    CaseReviewCopied,
    CaseReviewCreated,
    CaseReviewDeleted,
    CaseReviewResultUpdated,
    CaseReviewStatusChanged,
    CaseReviewUpdated,
    CaseUnlinkedFromReview,
)
from app.domain.case_review.domain.value_objects.case_result import (
    CaseReviewResult,
    CaseReviewResultEnum,
)
from app.domain.case_review.domain.value_objects.pass_rule import (
    ReviewPassRule,
    ReviewPassRuleEnum,
)
from app.domain.case_review.domain.value_objects.review_status import (
    ReviewStatus,
    ReviewStatusEnum,
)
from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError


@dataclass
class ReviewCaseLink:
    """评审会话中单个用例的关联记录（实体子项）。

    是聚合内的一个实体，拥有独立标识但生命周期由 CaseReview 聚合管理。
    不具备独立仓储，随聚合一起保存/加载，保证事务一致性。
    """

    case_id: str
    result: CaseReviewResult = field(default_factory=lambda: CaseReviewResult(
        CaseReviewResultEnum.UN_REVIEWED))
    reviewer: str = ""
    comment: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class ReviewerInfo:
    """评审人信息（值对象，聚合内保持只读）。"""

    user_id: str
    user_name: str = ""


class CaseReview(AggregateRoot):
    """用例评审聚合根。"""

    def __init__(
        self,
        *,
        review_id: str,
        name: str,
        description: str = "",
        status: str = ReviewStatusEnum.UNDERWAY.value,
        module_id: str = "root",
        project_id: str = "",
        review_pass_rule: str = ReviewPassRuleEnum.SINGLE.value,
        reviewers: Optional[List[dict]] = None,
        tags: Optional[List[str]] = None,
        num: int = 1,
        pos: int = 0,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        create_user: str = "admin",
        create_time: Optional[float] = None,
        update_user: str = "admin",
        update_time: Optional[float] = None,
        deleted: bool = False,
        links: Optional[List[dict]] = None,
    ):
        if not (name or "").strip():
            raise DomainValidationError("评审名称不能为空")
        self.id = Identifier.of(review_id)
        self._name = (name or "").strip()
        self._description = description or ""
        self._status = ReviewStatus(status)
        self._module_id = module_id or "root"
        self._project_id = project_id or ""
        self._pass_rule = ReviewPassRule(review_pass_rule)
        self._reviewers: List[ReviewerInfo] = []
        for r in (reviewers or []):
            if isinstance(r, dict):
                uid = str(r.get("userId", "") or r.get("user_id", "") or r.get("id", "") or "")
                uname = str(r.get("userName", "") or r.get("name", "") or uid or "")
                self._reviewers.append(ReviewerInfo(user_id=uid, user_name=uname))
            else:
                s = str(r)
                self._reviewers.append(ReviewerInfo(user_id=s, user_name=s))
        if not self._reviewers:
            self._reviewers.append(ReviewerInfo(user_id="admin", user_name="admin"))
        self._tags = list(tags or [])
        self._num = int(num or 1)
        self._pos = int(pos or 0)
        self._start_time = start_time if start_time is not None else 0
        self._end_time = end_time if end_time is not None else 0
        self._create_user = create_user or "admin"
        self._create_time = create_time if create_time is not None else time.time()
        self._update_user = update_user or "admin"
        self._update_time = update_time if update_time is not None else self._create_time
        self._deleted: bool = bool(deleted)
        self._domain_events = []
        # 内聚关联用例（ReviewCaseLink 列表）
        self._links: List[ReviewCaseLink] = []
        for lk in (links or []):
            if isinstance(lk, ReviewCaseLink):
                self._links.append(lk)
            elif isinstance(lk, dict):
                self._links.append(self._parse_link(lk))

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def status(self) -> ReviewStatus:
        return self._status

    @property
    def module_id(self) -> str:
        return self._module_id

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def pass_rule(self) -> ReviewPassRule:
        return self._pass_rule

    @property
    def reviewers(self) -> List[ReviewerInfo]:
        return list(self._reviewers)

    @property
    def tags(self) -> List[str]:
        return list(self._tags)

    @property
    def num(self) -> int:
        return self._num

    @property
    def pos(self) -> int:
        return self._pos

    @property
    def start_time(self) -> float:
        return self._start_time

    @property
    def end_time(self) -> Optional[float]:
        return self._end_time if self._end_time else None

    @property
    def create_user(self) -> str:
        return self._create_user

    @property
    def create_time(self) -> float:
        return self._create_time

    @property
    def update_user(self) -> str:
        return self._update_user

    @property
    def update_time(self) -> float:
        return self._update_time

    @property
    def deleted(self) -> bool:
        return self._deleted

    @property
    def links(self) -> List[ReviewCaseLink]:
        return list(self._links)

    def _touch(self) -> None:
        self._update_time = time.time()

    # ── 关联用例子项构造 ─────────────────────────────
    @staticmethod
    def _parse_link(raw: dict) -> "ReviewCaseLink":
        result = raw.get("result") or raw.get("status") or \
                 CaseReviewResultEnum.UN_REVIEWED.value
        return ReviewCaseLink(
            case_id=str(raw.get("case_id", "")),
            result=CaseReviewResult(result),
            reviewer=str(raw.get("reviewer", "") or ""),
            comment=str(raw.get("comment", "") or ""),
            created_at=raw.get("create_time") or raw.get("created_at") or time.time(),
            updated_at=raw.get("update_time") or raw.get("updated_at") or time.time(),
        )

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_name: str, operator: str = "system") -> None:
        """修改评审名称。"""
        nn = (new_name or "").strip()
        if not nn:
            raise DomainValidationError("评审名称不能为空")
        if nn == self._name:
            return
        self._name = nn
        self._touch()
        self.record_event(CaseReviewUpdated(self.id.value, operator))

    def change_description(self, text: str, operator: str = "system") -> None:
        self._description = text or ""
        self._touch()
        self.record_event(CaseReviewUpdated(self.id.value, operator))

    def change_module(self, module_id: str, operator: str = "system") -> None:
        """修改归属模块。"""
        mid = module_id or "root"
        if mid == self._module_id:
            return
        self._module_id = mid
        self._touch()
        self.record_event(CaseReviewUpdated(self.id.value, operator))

    def change_project(self, project_id: str, operator: str = "system") -> None:
        if (project_id or "") == self._project_id:
            return
        self._project_id = project_id or ""
        self._touch()
        self.record_event(CaseReviewUpdated(self.id.value, operator))

    def change_pass_rule(self, rule: str, operator: str = "system") -> None:
        """修改通过规则（SINGLE / ALL）。"""
        nr = ReviewPassRule(rule)
        if nr.value is self._pass_rule.value:
            return
        self._pass_rule = nr
        self._touch()
        self.record_event(CaseReviewUpdated(self.id.value, operator))

    def set_reviewers(self, reviewers: list, operator: str = "system") -> None:
        """整体替换评审人列表。"""
        if reviewers is None:
            return
        parsed: List[ReviewerInfo] = []
        for r in reviewers:
            if isinstance(r, dict):
                uid = str(r.get("userId", "") or r.get("user_id", "") or r.get("id", "") or "")
                uname = str(r.get("userName", "") or r.get("name", "") or uid or "")
                parsed.append(ReviewerInfo(user_id=uid, user_name=uname))
            else:
                s = str(r)
                parsed.append(ReviewerInfo(user_id=s, user_name=s))
        if parsed:
            self._reviewers = parsed
            self._touch()
            self.record_event(CaseReviewUpdated(self.id.value, operator))

    def set_tags(self, tags: List[str], operator: str = "system") -> None:
        self._tags = list(tags or [])
        self._touch()
        self.record_event(CaseReviewUpdated(self.id.value, operator))

    def set_time_range(self, start_time: float = 0, end_time: float = 0,
                       operator: str = "system") -> None:
        self._start_time = float(start_time or 0)
        self._end_time = float(end_time or 0)
        self._touch()
        self.record_event(CaseReviewUpdated(self.id.value, operator))

    def change_status(self, target: str, operator: str = "system") -> None:
        """受状态机约束的评审会话状态迁移。"""
        target_status = ReviewStatus(target)
        if target_status.value is self._status.value:
            return
        if not self._status.can_transition_to(target_status):
            from app.domain.case_review.domain.exceptions import InvalidReviewTransition
            raise InvalidReviewTransition(str(self._status), str(target_status))
        old = self._status.value.value
        self._status = target_status
        self._touch()
        self.record_event(CaseReviewStatusChanged(
            self.id.value, old, target_status.value.value, operator))

    def delete(self, operator: str = "system") -> None:
        """软删除评审会话。"""
        if self._deleted:
            raise DomainValidationError("评审已在回收站，不可重复删除")
        self._deleted = True
        self._touch()
        self.record_event(CaseReviewDeleted(self.id.value, operator))

    def link_cases(self, case_ids: List[str], operator: str = "system") -> int:
        """关联用例到本评审（去重）。返回新关联的数量。"""
        if self._deleted:
            raise DomainValidationError("评审已删除，不可关联用例")
        existing = {lk.case_id for lk in self._links}
        added = 0
        now = time.time()
        for cid in (case_ids or []):
            cid = str(cid)
            if not cid or cid in existing:
                continue
            self._links.append(ReviewCaseLink(
                case_id=cid,
                created_at=now,
                updated_at=now,
            ))
            existing.add(cid)
            added += 1
        if added:
            self._touch()
            self.record_event(CaseLinkedToReview(self.id.value, case_ids, operator))
        return added

    def unlink_cases(self, case_ids: List[str], operator: str = "system") -> int:
        """解除与用例的关联。返回实际移除的数量。"""
        ids = {str(cid) for cid in (case_ids or []) if cid}
        before = len(self._links)
        self._links = [lk for lk in self._links if lk.case_id not in ids]
        removed = before - len(self._links)
        if removed:
            self._touch()
            self.record_event(CaseUnlinkedFromReview(self.id.value, case_ids, operator))
        return removed

    def update_link_result(self, case_id: str, result: str, reviewer: str = "",
                           comment: str = "", operator: str = "system") -> bool:
        """更新单个关联用例的评审结论。"""
        target = CaseReviewResult(result)
        now = time.time()
        found = False
        for lk in self._links:
            if lk.case_id == str(case_id):
                lk.result = target
                lk.reviewer = reviewer or ""
                lk.comment = comment or ""
                lk.updated_at = now
                found = True
                break
        if not found:
            raise DomainValidationError(
                f"用例 {case_id} 未关联到评审 {self.id.value}")
        self._touch()
        self.record_event(CaseReviewResultUpdated(
            self.id.value, str(case_id), str(target), reviewer or "", operator))
        return True

    def update_links_result(self, case_ids: List[str], result: str,
                            reviewer: str = "", comment: str = "",
                            operator: str = "system") -> int:
        """批量更新多个关联用例的评审结论。返回实际更新的数量。"""
        target = CaseReviewResult(result)
        ids = {str(cid) for cid in (case_ids or []) if cid}
        updated = 0
        now = time.time()
        for lk in self._links:
            if lk.case_id in ids:
                lk.result = target
                lk.reviewer = reviewer or ""
                lk.comment = comment or ""
                lk.updated_at = now
                updated += 1
        if updated:
            self._touch()
            for cid in ids:
                self.record_event(CaseReviewResultUpdated(
                    self.id.value, cid, str(target), reviewer or "", operator))
        return updated

    # ── 状态统计 ─────────────────────────────────────
    def get_result_counts(self) -> dict:
        """统计当前评审中各用例结论分布。"""
        counts = {
            "passCount": 0,
            "unPassCount": 0,
            "unReviewCount": 0,
            "underReviewedCount": 0,
            "reReviewedCount": 0,
            "reviewedCount": 0,
        }
        for lk in self._links:
            r = lk.result.value.value
            if r == CaseReviewResultEnum.PASS.value:
                counts["passCount"] += 1
                counts["reviewedCount"] += 1
            elif r == CaseReviewResultEnum.UN_PASS.value:
                counts["unPassCount"] += 1
                counts["reviewedCount"] += 1
            elif r == CaseReviewResultEnum.UNDER_REVIEWED.value:
                counts["underReviewedCount"] += 1
                counts["reviewedCount"] += 1
            elif r == CaseReviewResultEnum.RE_REVIEWED.value:
                counts["reReviewedCount"] += 1
                counts["reviewedCount"] += 1
            else:
                counts["unReviewCount"] += 1
        return counts

    def is_completed(self) -> bool:
        """是否所有关联用例均已有结论。"""
        if not self._links:
            return False
        return all(lk.result.is_reviewed for lk in self._links)

    @property
    def case_count(self) -> int:
        return len(self._links)

    # ── 序列化 / 持久化 ─────────────────────────────
    def snapshot(self) -> dict:
        """生成用于版本/审计快照的核心字段。"""
        return {
            "name": self._name,
            "description": self._description,
            "status": self._status.value.value,
            "module_id": self._module_id,
            "project_id": self._project_id,
            "review_pass_rule": self._pass_rule.value.value,
            "reviewers": [
                {"userId": r.user_id, "userName": r.user_name}
                for r in self._reviewers
            ],
            "tags": list(self._tags),
        }

    def to_dict(self) -> dict:
        """导出可落库 / 返回上层视图层的字典。"""
        return {
            "id": self.id.value,
            "name": self._name,
            "num": self._num,
            "module_id": self._module_id,
            "project_id": self._project_id,
            "status": self._status.value.value,
            "review_pass_rule": self._pass_rule.value.value,
            "pos": self._pos,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "tags": list(self._tags),
            "description": self._description,
            "create_time": self._create_time,
            "create_user": self._create_user,
            "update_time": self._update_time,
            "update_user": self._update_user,
            "deleted": 1 if self._deleted else 0,
            "reviewers": [
                {"userId": r.user_id, "userName": r.user_name}
                for r in self._reviewers
            ],
            "case_count": len(self._links),
            "links": [
                {
                    "case_id": lk.case_id,
                    "status": lk.result.value.value,
                    "reviewer": lk.reviewer,
                    "comment": lk.comment,
                    "create_time": lk.created_at,
                    "update_time": lk.updated_at,
                }
                for lk in self._links
            ],
        }

    @staticmethod
    def from_dict(data: dict) -> "CaseReview":
        """从持久化字典 / 仓储返回行重建聚合。"""
        tags = data.get("tags") or []
        if isinstance(tags, str):
            try:
                tags = json.loads(tags or "[]")
            except Exception:
                tags = []
        reviewers = data.get("reviewers") or data.get("reviewers_json") or []
        if isinstance(reviewers, str):
            try:
                reviewers = json.loads(reviewers or "[]")
            except Exception:
                reviewers = []
        return CaseReview(
            review_id=str(data.get("id") or data.get("review_id") or ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=data.get("status", ReviewStatusEnum.UNDERWAY.value),
            module_id=data.get("module_id", "root"),
            project_id=data.get("project_id", ""),
            review_pass_rule=data.get("review_pass_rule", ReviewPassRuleEnum.SINGLE.value),
            reviewers=reviewers,
            tags=tags,
            num=int(data.get("num") or 1),
            pos=int(data.get("pos") or 0),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            create_user=data.get("create_user", "admin"),
            create_time=data.get("create_time"),
            update_user=data.get("update_user", "admin"),
            update_time=data.get("update_time"),
            deleted=bool(data.get("deleted")),
            links=data.get("links") or [],
        )
