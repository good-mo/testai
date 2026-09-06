"""缺陷上下文基础设施层：对接现有四层存储实现（DefectRepo）。"""
from app.domain.defects.infrastructure.defect_repository_impl import DefectRepoAdapter

__all__ = ["DefectRepoAdapter"]
