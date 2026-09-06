# app/models/datafactory.py
"""数据工厂 Pydantic 模型。"""
from typing import List, Optional

from pydantic import BaseModel, Field


class DataTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field("")
    category: str = Field("")
    schema_def: Optional[dict] = Field(None)
    deps: Optional[List[str]] = Field(None)
    tags: Optional[List[str]] = Field(None)


class DataTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    schema_def: Optional[dict] = None
    deps: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class DataGenerateRequest(BaseModel):
    template_id: str = Field("")
    batch_size: int = Field(1, ge=1, le=1000)
    env_key: str = Field("")
