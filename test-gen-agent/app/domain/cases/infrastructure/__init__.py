"""用例上下文基础设施层：对接现有四层存储实现（CaseRepo）。"""
from app.domain.cases.infrastructure.case_repository_impl import CaseRepoAdapter

__all__ = ["CaseRepoAdapter"]
