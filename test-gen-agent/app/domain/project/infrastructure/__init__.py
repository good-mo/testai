"""项目上下文基础设施层：对接现有四层存储实现。

实现领域仓储接口（Adapter），复用既有 ProjectRepo 已验证的存储逻辑。
"""
from __future__ import annotations

from app.domain.project.infrastructure.project_repository_impl import ProjectRepoAdapter

__all__ = ["ProjectRepoAdapter"]
