# app/services/run_service.py
"""运行记录业务逻辑层（runs 域 DDD 接入 · 薄门面）。

业务规则已下沉到 runs 域领域层（`app/domain/runs/`：来源合法性、
报告名非空、passed 派生等），本四层 Service 收敛为对 DDD 应用服务
`run_record_app_service` 的**薄委托门面**，仅保留历史方法签名与
返回形状（passed 仍归一为 0/1，兼容既有 /api/runs 与报告兼容层契约）
以兼容既有调用方 / 便于回滚。

> 推荐调用方直接使用 `run_record_app_service`；本类仅作过渡兼容层保留。
"""
from typing import Optional

from app.domain.runs.application.dto import (
    ClearRunRecordsCommand,
    RenameRunRecordCommand,
    RunRecordListQuery,
    SaveRunRecordCommand,
)
from app.domain.runs.application.run_record_app_service import (
    run_record_app_service as _ddd_service,
)


class RunService:
    """运行记录服务（runs 域 DDD 薄门面）。"""

    @staticmethod
    def _row(rec: dict) -> dict:
        """把聚合视图归一为既有 DB 扁平行契约（passed 0/1 int）。"""
        if rec is None:
            return {}
        out = dict(rec)
        out["passed"] = 1 if out.get("passed") else 0
        return out

    @staticmethod
    def _rows(records: list) -> list:
        return [RunService._row(r) for r in records]

    def list(self, file_path: Optional[str] = None, source: Optional[str] = None,
             passed: Optional[bool] = None, search: Optional[str] = None,
             limit: int = 50, offset: int = 0) -> list:
        result = _ddd_service.list(RunRecordListQuery(
            file_path=file_path or "",
            source=source or "",
            passed=passed,
            search=search or "",
            limit=limit,
            offset=offset,
        ))
        return self._rows(result.get("list", []))

    def count(self, file_path: Optional[str] = None, source: Optional[str] = None,
              passed: Optional[bool] = None, search: Optional[str] = None) -> int:
        return _ddd_service.count(RunRecordListQuery(
            file_path=file_path or "",
            source=source or "",
            passed=passed,
            search=search or "",
        ))

    def get(self, record_id: str) -> Optional[dict]:
        rec = _ddd_service.get(record_id)
        return self._row(rec) if rec else None

    def get_stats(self) -> dict:
        return _ddd_service.stats()

    def save(self, file_path: str = "", source_code: str = "",
             generated_tests: str = "", test_result: dict = None,
             coverage_report: dict = None, performance_report: dict = None,
             retry_count: int = 0, saved_to: str = "", error: str = "",
             source: str = "", metadata: dict = None) -> dict:
        rec = _ddd_service.save(SaveRunRecordCommand(
            file_path=file_path,
            source_code=source_code,
            generated_tests=generated_tests,
            test_result=test_result or {},
            coverage_report=coverage_report or {},
            performance_report=performance_report or {},
            retry_count=retry_count,
            saved_to=saved_to,
            error=error,
            source=source,
            metadata=metadata or {},
        ))
        return self._row(rec) if rec else {}

    def clear(self, source: Optional[str] = None) -> int:
        return _ddd_service.clear(ClearRunRecordsCommand(source=source or ""))

    # ── 报告（run 记录别名）操作 ───────────────────────
    def rename_report(self, record_id: str, new_name: str) -> bool:
        """将运行记录重命名（file_path 充当报告名）。"""
        try:
            return _ddd_service.rename(RenameRunRecordCommand(
                record_id=record_id, new_name=new_name,
            ))
        except Exception:
            return False

    def delete_report(self, record_id: str) -> bool:
        """删除单条报告（运行记录）。"""
        return _ddd_service.delete(record_id)

    def delete_reports(self, record_ids: list) -> int:
        """批量删除报告（运行记录）。"""
        return _ddd_service.delete_batch(record_ids)


run_service = RunService()
