"""运行记录领域策略（RunRecordPolicy）。

无状态领域策略：集中表达"运行记录/报告"跨聚合规则，供聚合与应用层
复用，规则单一出处。

当前守护：
  - 报告名（file_path）非空；
  - 来源合法性（可过滤来源值域，供读模型使用）。
"""
from __future__ import annotations

from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.runs.domain.value_objects.run_source import VALID_SOURCES


class RunRecordPolicy:
    """运行记录/报告领域策略。"""

    @property
    def valid_sources(self) -> Set[str]:
        return set(VALID_SOURCES)

    def ensure_report_name(self, name: str) -> str:
        """报告名非空守卫：归一后返回，空串抛领域异常。"""
        clean = (name or "").strip()
        if not clean:
            raise DomainValidationError("报告名/运行记录 file_path 不能为空")
        return clean

    def is_valid_source(self, source: str) -> bool:
        return str(source or "").lower() in VALID_SOURCES


# 单例（无状态）
run_record_policy = RunRecordPolicy()

__all__ = ["RunRecordPolicy", "run_record_policy"]
