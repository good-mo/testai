"""运行记录聚合根 RunRecord。

聚合边界内的组成：
  - RunRecord（聚合根，一次测试运行/生成的完整快照）
  - 值对象：RunSource（来源）、TestResult/Coverage/Performance 报告数据

职责：
  - 登记一次测试运行的完整快照（被测文件、源码、生成测试、运行结果、
    覆盖率、性能、重试次数、保存路径、错误、元数据）；
  - 派生 `passed`：以 `test_result.passed` 为唯一口径（与 RunRepo 落库
    判定一致），避免散落多处造成口径漂移；
  - 以 `file_path` 充当"报告名"语义：rename 将报告名更新到 file_path，
    非空守卫杜绝脏名。

本聚合面向通用"运行记录/报告"能力（run_service → RunRepo 所承载），
与 generation 域 `GenerationJob`（带状态机/步骤/修复循环的高阶视图）
属于同一底层存储 run_records 的不同读写视角，互不冲突。
"""
from __future__ import annotations

import time
from typing import Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.runs.domain.value_objects.run_source import RunSource


class RunRecord(AggregateRoot):
    """一次测试运行记录聚合根。"""

    def __init__(
        self,
        *,
        record_id: str,
        file_path: str = "",
        source_code: str = "",
        generated_tests: str = "",
        test_result: Optional[dict] = None,
        coverage_report: Optional[dict] = None,
        performance_report: Optional[dict] = None,
        retry_count: int = 0,
        saved_to: str = "",
        error: str = "",
        source: str = "single",
        metadata: Optional[dict] = None,
        created_at: Optional[float] = None,
        passed: Optional[bool] = None,
    ):
        self.id = Identifier.of(record_id)
        self._file_path = file_path or ""
        self._source_code = source_code or ""
        self._generated_tests = generated_tests or ""
        self._test_result = dict(test_result or {})
        self._coverage_report = dict(coverage_report or {})
        self._performance_report = dict(performance_report or {})
        self._retry_count = int(retry_count or 0)
        self._saved_to = saved_to or ""
        self._error = error or ""
        self._source = RunSource(source)
        self._metadata = dict(metadata or {})
        self._created_at = created_at if created_at is not None else time.time()
        # passed 以 test_result.passed 为准（传入仅供兼容/重建历史脏数据）
        if passed is not None:
            self._passed = bool(passed)
        else:
            self._passed = bool((self._test_result or {}).get("passed"))
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def source_code(self) -> str:
        return self._source_code

    @property
    def generated_tests(self) -> str:
        return self._generated_tests

    @property
    def test_result(self) -> dict:
        return dict(self._test_result)

    @property
    def coverage_report(self) -> dict:
        return dict(self._coverage_report)

    @property
    def performance_report(self) -> dict:
        return dict(self._performance_report)

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def saved_to(self) -> str:
        return self._saved_to

    @property
    def error(self) -> str:
        return self._error

    @property
    def source(self) -> RunSource:
        return self._source

    @property
    def metadata(self) -> dict:
        return dict(self._metadata)

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def passed(self) -> bool:
        return self._passed

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_name: str, operator: str = "system") -> None:
        """重命名记录（file_path 充当报告名）。

        报告名不能为空（空串会污染 file_path 索引与搜索口径）。
        """
        name = (new_name or "").strip()
        if not name:
            raise DomainValidationError("运行记录/报告名不能为空")
        self._file_path = name

    def set_results(
        self,
        *,
        source_code: Optional[str] = None,
        generated_tests: Optional[str] = None,
        test_result: Optional[dict] = None,
        coverage_report: Optional[dict] = None,
        performance_report: Optional[dict] = None,
        retry_count: Optional[int] = None,
        saved_to: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """原位更新运行/报告数据（不换主键）。

        保存路径/错误/元数据可增量并入；passed 始终以 test_result 重新派生。
        """
        if source_code is not None:
            self._source_code = source_code
        if generated_tests is not None:
            self._generated_tests = generated_tests
        if test_result is not None:
            self._test_result = dict(test_result)
            self._passed = bool(self._test_result.get("passed"))
        if coverage_report is not None:
            self._coverage_report = dict(coverage_report)
        if performance_report is not None:
            self._performance_report = dict(performance_report)
        if retry_count is not None:
            self._retry_count = int(retry_count)
        if saved_to is not None:
            self._saved_to = saved_to
        if error is not None:
            self._error = error
        if metadata is not None:
            self._metadata.update(dict(metadata))

    # ── 序列化 / 持久化 ─────────────────────────────
    def to_dict(self) -> dict:
        """导出与 run_records 契约一致的扁平行（含派生 passed 布尔）。"""
        return {
            "id": self.id.value,
            "file_path": self._file_path,
            "source_code": self._source_code,
            "generated_tests": self._generated_tests,
            "test_result": dict(self._test_result),
            "coverage_report": dict(self._coverage_report),
            "performance_report": dict(self._performance_report),
            "retry_count": self._retry_count,
            "passed": self._passed,
            "saved_to": self._saved_to,
            "error": self._error,
            "source": self._source.value,
            "created_at": self._created_at,
            "metadata": dict(self._metadata),
        }

    def to_persist_row(self) -> dict:
        """导出 RunRepo 落库所需的扁平行（passed 归一为 0/1 int）。"""
        d = self.to_dict()
        d["passed"] = 1 if d["passed"] else 0
        return d

    @staticmethod
    def from_dict(data: dict) -> "RunRecord":
        """从运行记录行 / RunRepo 返回行重建聚合。"""
        row = dict(data or {})
        meta = row.get("metadata") or {}
        if isinstance(meta, str):
            import json

            try:
                meta = json.loads(meta or "{}")
            except Exception:
                meta = {}

        def _json_field(field_name: str, default):
            val = row.get(field_name)
            if isinstance(val, str):
                import json

                try:
                    return json.loads(val or "{}")
                except Exception:
                    return default
            return val if val is not None else default

        return RunRecord(
            record_id=str(row.get("id") or row.get("record_id") or ""),
            file_path=row.get("file_path", ""),
            source_code=row.get("source_code", ""),
            generated_tests=row.get("generated_tests", ""),
            test_result=_json_field("test_result", {}),
            coverage_report=_json_field("coverage_report", {}),
            performance_report=_json_field("performance_report", {}),
            retry_count=int(row.get("retry_count") or 0),
            saved_to=row.get("saved_to", ""),
            error=row.get("error", ""),
            source=row.get("source", "single"),
            metadata=meta,
            created_at=row.get("created_at"),
            passed=bool(row.get("passed")) if row.get("passed") is not None else None,
        )


__all__ = ["RunRecord"]
