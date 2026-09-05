"""用例聚合根 TestCase。

聚合边界内的组成：
  - TestCase（聚合根）
  - 若干子值对象：Priority / CaseStatus / TestType / CaseReview[]（评审历史）

聚合职责：守护用例的完整性与业务不变量。所有变更必须经由聚合根方法，
禁止从外部直接改字段；业务命令（改名 / 迁移状态 / 提交评审 / 软删除 /
恢复）在校验通过后返回领域事件，供应用层落库+发布，从而与审计、版本
快照、通知等副作用解耦。
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.cases.domain.events import (
    CaseRestored,
    CaseReviewed,
    CaseRolledBack,
    CaseSoftDeleted,
    CaseStatusChanged,
    CaseTitleChanged,
    CaseVersionCreated,
)
from app.domain.cases.domain.value_objects.case_status import CaseStatus, CaseStatusEnum
from app.domain.cases.domain.value_objects.priority import Priority
from app.domain.cases.domain.value_objects.review import CaseReview, ReviewOutcome
from app.domain.cases.domain.value_objects.test_type import TestType
from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError


def _is_valid_test_type(value) -> bool:
    """判断字符串是否为 DDD 合法测试类型（用于持久化重建容错）。"""
    if not value:
        return False
    try:
        TestType(value)
        return True
    except Exception:
        return False


# 合法状态/优先级全集（供 from_dict 容错回退）
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}


class TestCase(AggregateRoot):
    """测试用例聚合根。"""

    def __init__(
        self,
        *,
        case_id: str,
        title: str,
        description: str = "",
        source_code: str = "",
        test_code: str = "",
        file_path: str = "",
        tags: Optional[List[str]] = None,
        status: str = CaseStatusEnum.DRAFT.value,
        priority: str = "P2",
        requirement_ref: str = "",
        test_type: str = TestType("functional").value,
        structured_cases: Optional[list] = None,
        metadata: Optional[dict] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        reviews: Optional[List[dict]] = None,
        version: int = 0,
        last_result: Optional[object] = None,
    ):
        self.id = Identifier.of(case_id)
        self._title = (title or "").strip()
        self._description = description or ""
        self._source_code = source_code or ""
        self._test_code = test_code or ""
        self._file_path = file_path or ""
        self._tags = list(tags or [])
        self._status = CaseStatus(status)
        self._priority = Priority(priority)
        self._requirement_ref = requirement_ref or ""
        self._test_type = TestType(test_type)
        self._structured_cases = list(structured_cases or [])
        self._metadata = dict(metadata or {})
        # 同步 test_type 进 metadata（持久化 schema 依赖 metadata.test_type）
        self._metadata["test_type"] = TestType(test_type).value.value
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._reviews: List[CaseReview] = []
        for r in (reviews or []):
            self._reviews.append(CaseReview(**r) if isinstance(r, dict) else r)
        self._domain_events = []
        self._deleted: bool = False
        self.version = int(version)
        self._last_result = last_result or ""

    # ── 只读属性 ─────────────────────────────────────
    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def source_code(self) -> str:
        return self._source_code

    @property
    def test_code(self) -> str:
        return self._test_code

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def tags(self) -> List[str]:
        return list(self._tags)

    @property
    def status(self) -> CaseStatus:
        return self._status

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def requirement_ref(self) -> str:
        return self._requirement_ref

    @property
    def test_type(self) -> TestType:
        return self._test_type

    @property
    def structured_cases(self) -> list:
        return list(self._structured_cases)

    @property
    def metadata(self) -> dict:
        return dict(self._metadata)

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def reviews(self) -> List[CaseReview]:
        return list(self._reviews)

    @property
    def deleted(self) -> bool:
        return self._deleted or self._status.is_deprecated

    @property
    def last_result(self):
        return self._last_result

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_title: str, operator: str = "system") -> None:
        """修改用例标题。"""
        nt = (new_title or "").strip()
        if not nt:
            raise DomainValidationError("用例标题不能为空")
        if nt == self._title:
            return
        old = self._title
        self._title = nt
        self._touch()
        self.record_event(CaseTitleChanged(self.id.value, old, nt, operator))

    def change_description(self, text: str, operator: str = "system") -> None:
        self._description = text or ""
        self._touch()
        self.record_event(CaseTitleChanged(self.id.value, self._title, self._title, operator))

    def change_priority(self, priority: str) -> None:
        """变更优先级（自动去重、归一）。"""
        self._priority = Priority(priority)
        self._touch()

    def change_test_type(self, test_type: str) -> None:
        self._test_type = TestType(test_type)
        # 同步 metadata.test_type（CaseRepo 依赖 metadata 反查类型字段）
        self._metadata["test_type"] = self._test_type.value.value
        self._touch()

    def set_content(self, *, source_code: str = None, test_code: str = None,
                    file_path: str = None, tags=None, structured_cases=None,
                    requirement_ref: str = None, metadata: dict = None,
                    operator: str = "system") -> None:
        """整体更新用例正文内容（聚合内部原子更新）。"""
        if source_code is not None:
            self._source_code = source_code
        if test_code is not None:
            self._test_code = test_code
        if file_path is not None:
            self._file_path = file_path
        if tags is not None:
            self._tags = list(tags)
        if structured_cases is not None:
            self._structured_cases = list(structured_cases)
        if requirement_ref is not None:
            self._requirement_ref = requirement_ref
        if metadata is not None:
            self._metadata.update(metadata)
        self._touch()

    def change_status(self, target: str, operator: str = "system") -> None:
        """受状态机约束的状态迁移。"""
        target_status = CaseStatus(target)
        if target_status.is_deprecated:
            raise DomainValidationError("请使用 delete() 软删除")
        from app.domain.cases.domain.services.case_policy import CaseStatePolicy
        CaseStatePolicy().ensure_transition_allowed(self._status, target_status)
        if self._status.value is target_status.value:
            return
        old = self._status.value.value
        self._status = target_status
        self._touch()
        self.record_event(CaseStatusChanged(self.id.value, old, target_status.value.value, operator))

    def delete(self, operator: str = "system", reason: str = "") -> None:
        """软删除：仅草稿/评审中/已批准状态允许，置为废弃并进回收站。"""
        if self.deleted:
            raise DomainValidationError("用例已在回收站，不可重复删除")
        if self._status.value is CaseStatusEnum.DEPRECATED:
            raise DomainValidationError("用例已在回收站")
        old = self._status.value.value
        self._status = CaseStatus(CaseStatusEnum.DEPRECATED)
        self._deleted = True
        self._touch()
        self.record_event(CaseSoftDeleted(self.id.value, operator, reason))
        self.record_event(CaseStatusChanged(self.id.value, old, CaseStatusEnum.DEPRECATED.value, operator))

    def restore(self, operator: str = "system") -> None:
        """从回收站恢复为草稿。"""
        if not self.deleted:
            raise DomainValidationError("用例不在回收站，无需恢复")
        old = self._status.value.value
        self._status = CaseStatus(CaseStatusEnum.DRAFT)
        self._deleted = False
        self._touch()
        self.record_event(CaseRestored(self.id.value, operator))
        self.record_event(CaseStatusChanged(self.id.value, old, CaseStatusEnum.DRAFT.value, operator))

    def submit_for_review(self, reviewer: str = "", operator: str = "system") -> None:
        """提交评审：草稿 -> 评审中。"""
        self.change_status(CaseStatusEnum.REVIEW.value, operator)
        self._reviews.append(
            CaseReview(reviewer=reviewer, outcome=ReviewOutcome.PENDING)
        )

    def review(self, *, outcome: str, reviewer: str = "", comment: str = "") -> None:
        """处理一次评审结论：通过/驳回/需修改。"""
        try:
            oc = ReviewOutcome(outcome)
        except ValueError:
            raise DomainValidationError(f"非法评审结果 '{outcome}'")
        if oc is ReviewOutcome.APPROVED:
            from app.domain.cases.domain.services.case_policy import CaseStatePolicy
            target = CaseStatus(CaseStatePolicy().review_approves_case(self._status))
            if self._status.value is not target.value:
                old = self._status.value.value
                self._status = target
                self.record_event(CaseStatusChanged(self.id.value, old, target.value.value, reviewer))
        elif oc is ReviewOutcome.REJECTED or oc is ReviewOutcome.NEED_REVISE:
            # 驳回/需修改 -> 回草稿
            if self._status.value is not CaseStatusEnum.DRAFT:
                old = self._status.value.value
                self._status = CaseStatus(CaseStatusEnum.DRAFT)
                self.record_event(CaseStatusChanged(self.id.value, old, CaseStatusEnum.DRAFT.value, reviewer))
        self._reviews.append(CaseReview(reviewer=reviewer, comment=comment,
                                        outcome=oc, reviewed_at=time.time(),
                                        review_seq=len(self._reviews) + 1))
        self._touch()
        self.record_event(CaseReviewed(self.id.value, oc.value, reviewer))

    def bump_version(self, operator: str = "system", change_desc: str = "") -> int:
        """递增版本号并发出快照事件（由应用层决定是否落版本表）。"""
        self.version += 1
        ev = CaseVersionCreated(self.id.value, self.version, operator, change_desc)
        self.record_event(ev)
        return self.version

    def mark_rolled_back(self, version: int, operator: str = "") -> None:
        self.record_event(CaseRolledBack(self.id.value, version, operator))

    # ── 快照 / 持久化 ───────────────────────────────
    def snapshot(self) -> dict:
        """生成用于版本表快照的核心字段字典。"""
        return {
            "title": self._title,
            "description": self._description,
            "source_code": self._source_code,
            "test_code": self._test_code,
            "file_path": self._file_path,
            "tags": list(self._tags),
            "status": self._status.value.value,
            "priority": self._priority.value,
            "requirement_ref": self._requirement_ref,
            "test_type": self._test_type.value.value,
            "structured_cases": list(self._structured_cases),
        }

    def to_dict(self) -> dict:
        """导出可落库/可返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "title": self._title,
            "description": self._description,
            "source_code": self._source_code,
            "test_code": self._test_code,
            "file_path": self._file_path,
            "tags": list(self._tags),
            "status": self._status.value.value,
            "priority": self._priority.value,
            "requirement_ref": self._requirement_ref,
            "test_type": self._test_type.value.value,
            "structured_cases": list(self._structured_cases),
            "metadata": dict(self._metadata),
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "version": self.version,
            "reviews": [vars(r) for r in self._reviews],
            "last_result": self._last_result,
        }

    @staticmethod
    def from_dict(data: dict) -> "TestCase":
        """从持久化字典/仓储返回行重建聚合。"""
        meta = data.get("metadata") or {}
        if isinstance(meta, str):
            import json
            try:
                meta = json.loads(meta or "{}")
            except Exception:
                meta = {}
        # 兼容旧数据：test_type/module_id 存于 metadata JSON
        test_type = data.get("test_type") or meta.get("test_type") or "functional"
        # ── 防腐层容错 ──
        # 从既有四层持久化数据重建聚合时，历史数据可能含非法/未标准化的
        # test_type（如导入脑图把节点 id 写进 test_type）、status、priority。
        # 这里对未知值回退默认，保证 DDD 读路径可安全承载既有真实库，
        # 避免在脏数据上抛 DomainValidationError 崩掉读/列表接口。
        if not _is_valid_test_type(test_type):
            test_type = "functional"
        status = data.get("status", "draft") or "draft"
        if status not in {e.value for e in CaseStatusEnum}:
            status = "draft"
        priority = str(data.get("priority") or "P2")
        if priority not in VALID_PRIORITIES:
            priority = "P2"
        return TestCase(
            case_id=str(data.get("id") or data.get("case_id") or ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            source_code=data.get("source_code", ""),
            test_code=data.get("test_code", ""),
            file_path=data.get("file_path", ""),
            tags=data.get("tags") or [],
            status=status,
            priority=priority,
            requirement_ref=data.get("requirement_ref", ""),
            test_type=test_type,
            structured_cases=data.get("structured_cases") or [],
            metadata=meta,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            reviews=data.get("reviews") or [],
            version=int(data.get("version") or 0),
            last_result=data.get("last_result"),
        )
