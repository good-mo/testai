# app/models/project.py
"""项目管理 Pydantic 模型。"""
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("")
    repo_url: str = Field("")
    language: str = Field("python")
    path: str = Field("")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    repo_url: Optional[str] = None
    language: Optional[str] = None
    path: Optional[str] = None
    status: Optional[str] = None


class ProjectScanRequest(BaseModel):
    project_path: str = Field("", description="要扫描的项目目录路径")


class ProjectGenerateRequest(BaseModel):
    project_path: str = Field("", description="要批量生成的项目目录路径")
