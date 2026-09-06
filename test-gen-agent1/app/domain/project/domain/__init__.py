"""项目管理领域层（domain layer）。

仅表达业务概念与规则（Project 聚合、生命周期与成员不变量），
不依赖 FastAPI / sqlite / 具体存储实现。
"""
from __future__ import annotations

from app.domain.project.domain.entities.project import Project
from app.domain.project.domain.exceptions import (
    AggregateNotFound,
    DomainException,
    DomainValidationError,
    InvariantViolation,
)

__all__ = [
    "Project",
    "DomainException",
    "DomainValidationError",
    "InvariantViolation",
    "AggregateNotFound",
]
