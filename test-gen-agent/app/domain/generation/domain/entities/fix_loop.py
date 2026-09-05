"""修复循环实体（FixLoop）。

FixLoop 是 GenerationJob 聚合内的子实体：表达一次"测试失败 → LLM 定向
修复 → 重新验证"的重试轮次，承载 refinement 流程产生的诊断与错误快照，
用于观测与统计（对齐 graph.refinement.refine_history 记录）。

无独立仓储，随聚合一起存取，保证事务一致性。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from app.domain.common.exceptions import DomainValidationError


@dataclass
class FixLoop:
    """单次修复重试记录（聚合内子实体）。"""

    attempt: int = 0                 # 第几次重试（1-based）
    diagnosis: str = ""              # 错误分类诊断文本
    error_snippet: str = ""          # 上一轮错误输出摘录
    status: str = "applied"          # applied / rejected（LLM 修复未被采纳等）
    created_at: Optional[float] = None

    def __post_init__(self) -> None:
        if self.attempt < 0:
            raise DomainValidationError("修复重试轮次不能为负")
        if self.status not in ("applied", "rejected"):
            raise DomainValidationError(f"非法修复结果 '{self.status}'")
        if self.created_at is None:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "attempt": self.attempt,
            "diagnosis": self.diagnosis,
            "error_snippet": self.error_snippet,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FixLoop":
        return cls(
            attempt=int(data.get("attempt") or 0),
            diagnosis=data.get("diagnosis", ""),
            error_snippet=data.get("error_snippet", ""),
            status=data.get("status", "applied"),
            created_at=data.get("created_at"),
        )


__all__ = ["FixLoop"]
