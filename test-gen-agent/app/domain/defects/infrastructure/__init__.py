"""缺陷上下文基础设施层。"""
from app.domain.defects.infrastructure.defect_repository_impl import DefectRepositoryImpl

DefectRepoAdapter = DefectRepositoryImpl

__all__ = ["DefectRepoAdapter"]
