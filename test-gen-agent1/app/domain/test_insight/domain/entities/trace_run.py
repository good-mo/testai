"""TestInsight 聚合根 TraceRun（一次测试执行追溯）。

一次"测试执行追溯"是对某被测文件一次执行的完整审计证据，用于回答
"当时测过、当时是否通过、为何没拦住回归"。执行追溯属于**追加式审计**
记录：每行代表一次独立执行（对应 test_runs 表），记录即入账、不可改写，
天然满足"自证清白"的可信性要求。

聚合内包含：
  - 被测文件 file_path / source_hash
  - 执行结果 TestResult 与通过/失败/报错计数
  - 覆盖率 Coverage
  - 异常归因 Attribution 与环境快照 env
  - 审计字段 created_at / created_by

聚合根守护的领域不变量：
  1. file_path 非空；
  2. 各执行计数为非负整数；
  3. 结果与计数自洽（failed/error 结果需有失败/报错计数支撑）；
  4. coverage 落在 [0,100]（由 Coverage 值对象守卫）。
"""
from __future__ import annotations

import time
import uuid
from typing import Dict, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.test_insight.domain.events import TraceRunRecorded
from app.domain.test_insight.domain.value_objects.attribution import (
    Attribution,
)
from app.domain.test_insight.domain.value_objects.coverage import Coverage
from app.domain.test_insight.domain.value_objects.test_result import (
    TestResult,
    TestResultEnum,
)


class TraceRun(AggregateRoot):
    """测试执行追溯聚合根（追加式审计记录）。"""

    def __init__(
        self,
        *,
        trace_id: str,
        file_path: str,
        source_hash: str = "",
        result: str = TestResultEnum.UNKNOWN.value,
        passed_count: int = 0,
        failed_count: int = 0,
        error_count: int = 0,
        coverage: float = 0.0,
        env_info: Optional[Dict] = None,
        attribution: str = "",
        note: str = "",
        created_at: Optional[float] = None,
        created_by: str = "manual",
    ):
        fp = (file_path or "").strip()
        if not fp:
            raise DomainValidationError("执行追溯的文件路径不能为空")
        for name, val in (("passed_count", passed_count), ("failed_count", failed_count),
                          ("error_count", error_count)):
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                raise DomainValidationError(f"{name} 必须为非负整数")
        result_vo = TestResult(result)
        if result_vo.is_defective and (int(passed_count) + int(failed_count) + int(error_count)) == 0:
            raise DomainValidationError(
                f"结果 '{result_vo.value}' 必须有失败或报错计数支撑"
            )
        self.id = Identifier.of(trace_id)
        self._file_path = fp
        self._source_hash = source_hash or ""
        self._result = result_vo
        self._passed_count = int(passed_count)
        self._failed_count = int(failed_count)
        self._error_count = int(error_count)
        self._coverage = Coverage(coverage)
        self._env_info = dict(env_info or {})
        self._attribution = Attribution(attribution) if attribution else None
        self._note = note or ""
        self._created_by = created_by or "manual"
        self._created_at = created_at if created_at is not None else time.time()
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def source_hash(self) -> str:
        return self._source_hash

    @property
    def result(self) -> TestResult:
        return self._result

    @property
    def passed_count(self) -> int:
        return self._passed_count

    @property
    def failed_count(self) -> int:
        return self._failed_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def coverage(self) -> Coverage:
        return self._coverage

    @property
    def env_info(self) -> Dict:
        return dict(self._env_info)

    @property
    def attribution(self) -> Optional[Attribution]:
        return self._attribution

    @property
    def note(self) -> str:
        return self._note

    @property
    def created_by(self) -> str:
        return self._created_by

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def total_cases(self) -> int:
        """本次执行的总用例数（通过+失败+报错）。"""
        return self._passed_count + self._failed_count + self._error_count

    @property
    def is_passed(self) -> bool:
        return self._result.is_passed

    @property
    def is_defective(self) -> bool:
        """本次执行是否存在缺陷（失败或报错）。"""
        return self._result.is_defective

    # ── 业务命令（守护不变量）────────────────────────
    def record(self, operator: str = "system") -> None:
        """入账本次执行：校验已通过构造器完成，发布 TraceRunRecorded 事件。"""
        self.record_event(TraceRunRecorded(self.id.value, self._file_path, operator))

    # ── 快照 / 持久化 ───────────────────────────────
    def to_dict(self) -> dict:
        import json as _json
        return {
            "id": self.id.value,
            "file_path": self._file_path,
            "source_hash": self._source_hash,
            "result": self._result.value,
            "passed_count": self._passed_count,
            "failed_count": self._failed_count,
            "error_count": self._error_count,
            "coverage": self._coverage.value,
            "env_info": _json.dumps(self._env_info, ensure_ascii=False),
            "attribution": self._attribution.value if self._attribution else "",
            "note": self._note,
            "created_at": self._created_at,
            "created_by": self._created_by,
        }

    @staticmethod
    def from_dict(data: dict) -> "TraceRun":
        import json as _json
        env = data.get("env_info") or {}
        if isinstance(env, str):
            try:
                env = _json.loads(env or "{}")
            except Exception:
                env = {}
        return TraceRun(
            trace_id=str(data.get("id") or data.get("trace_id") or ""),
            file_path=data.get("file_path", ""),
            source_hash=data.get("source_hash", ""),
            result=data.get("result") or TestResultEnum.UNKNOWN.value,
            passed_count=data.get("passed_count") or 0,
            failed_count=data.get("failed_count") or 0,
            error_count=data.get("error_count") or 0,
            coverage=data.get("coverage") or 0.0,
            env_info=env,
            attribution=data.get("attribution", ""),
            note=data.get("note", ""),
            created_at=data.get("created_at"),
            created_by=data.get("created_by", "manual"),
        )

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:12]
