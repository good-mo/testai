"""生成编排上下文基础设施层：对接现有四层存储实现（RunRepo）。"""
from app.domain.generation.infrastructure.generation_repository_impl import (
    GenerationJobRepoAdapter,
    generation_repository,
)

__all__ = ["GenerationJobRepoAdapter", "generation_repository"]
