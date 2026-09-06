"""AI 配置应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GetAiConfigCommand:
    """获取 AI 配置。"""
    scope: str = "functional_case"
    owner: str = ""
    project_id: str = ""
    config_type: str = "default"


@dataclass
class SaveAiConfigCommand:
    """保存 AI 配置。"""
    scope: str = "functional_case"
    config_value: Dict[str, Any] = field(default_factory=dict)
    owner: str = ""
    project_id: str = ""
    config_type: str = "default"
    create_user: str = "admin"


@dataclass
class DeleteAiConfigCommand:
    """删除 AI 配置。"""
    scope: str = "functional_case"
    owner: str = ""
    project_id: str = ""
    config_type: str = "default"


__all__ = ["GetAiConfigCommand", "SaveAiConfigCommand", "DeleteAiConfigCommand"]


# ==============================================================================
# 从 models/ai_config.py 迁移
# ==============================================================================

# app/models/ai_config.py
"""AI 配置与对话（ai_config / ai_conversation）域 Pydantic 请求体模型。

字段自 `app/routers/ai_config.py` 中 `read_body` 实际使用的请求体归纳：
  - AI 模型配置源（/ai/config/*）
  - AI 对话（/ai/conversation/*）

所有模型默认 `extra: allow`，避免遗漏新增字段导致 400。
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field

# ── AI 模型配置源 ─────────────────────────────────────────

MODEL_TYPE_LLM = "LLM"
PERMISSION_PUBLIC = "PUBLIC"


class AiModelAdvItem(BaseModel):
    """AI 模型源高级配置项。"""

    fieldName: str = Field("", description="配置项名")
    value: Any = Field(None, description="配置项值")
    type: str = Field("", description="配置项类型")

    model_config = {"extra": "allow"}


class AiModelConfigBody(BaseModel):
    """编辑 AI 配置源（有 id 更新、无 id 新建）。

    前端 /ai/config/edit-source 整体提交模型源配置，经
    ai_model_service.save 透传到 ai_model_repo.upsert 落库。
    """

    id: Optional[str] = Field(None, description="模型源 ID（更新时）")
    name: str = Field("", description="模型名称")
    type: str = Field(MODEL_TYPE_LLM, description="模型类型：LLM 等")
    providerName: str = Field("", description="供应商：openai/azure/deepseek/zhipu 等")
    permissionType: str = Field(PERMISSION_PUBLIC, description="权限类型")
    status: bool = Field(True, description="是否启用")
    owner: Optional[str] = Field(None, description="属主（个人源）")
    ownerType: Optional[str] = Field(None, description="属主类型：SYSTEM/PERSONAL")
    baseName: str = Field("", description="模型名（如 gpt-4o）")
    appKey: str = Field("", description="应用 Key")
    apiUrl: str = Field("", description="接口地址")
    advSettingDTOList: List[AiModelAdvItem] = Field([], description="高级配置项")
    description: Optional[str] = Field("", description="描述")

    model_config = {"extra": "allow"}


class AiConfigSourceListQuery(BaseModel):
    """系统设置-模型源分页列表。"""

    owner: str = Field("", description="属主（非空即个人源）")
    providerName: str = Field("", description="供应商过滤")
    keyword: str = Field("", description="关键字")
    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, description="每页条数")

    model_config = {"extra": "allow"}


class AiConfigIdBody(BaseModel):
    """按 ID 删除/查询 AI 配置。"""

    id: str = Field("", description="模型源 ID")

    model_config = {"extra": "allow"}


# ── AI 对话 ───────────────────────────────────────────────

class AiConversationAddBody(BaseModel):
    """新增 AI 对话。"""

    title: str = Field("新对话", description="对话标题")
    prompt: str = Field("", description="首条 prompt（作为首条 user 消息）")
    message: str = Field("", description="prompt 别名")
    content: str = Field("", description="prompt 别名")
    projectId: str = Field("", description="项目 ID")
    project_id: str = Field("", description="项目 ID（别名）")
    moduleType: str = Field("", description="模块类型")
    type: str = Field("", description="模块类型（别名）")

    @property
    def effective_title(self) -> str:
        return self.title or "新对话"

    @property
    def effective_prompt(self) -> str:
        return self.prompt or self.message or self.content

    @property
    def effective_project_id(self) -> str:
        return self.projectId or self.project_id

    @property
    def effective_module_type(self) -> str:
        return self.moduleType or self.type or "ai"

    model_config = {"extra": "allow"}


class AiConversationChatBody(BaseModel):
    """AI 对话（写消息）。"""

    prompt: str = Field("", description="用户消息")
    message: str = Field("", description="用户消息（别名）")
    content: str = Field("", description="用户消息（别名）")
    conversationId: str = Field("", description="会话 ID")
    conversation_id: str = Field("", description="会话 ID（别名）")

    @property
    def effective_prompt(self) -> str:
        return self.prompt or self.message or self.content

    @property
    def effective_conversation_id(self) -> str:
        return self.conversationId or self.conversation_id

    model_config = {"extra": "allow"}


class AiConversationUpdateBody(BaseModel):
    """更新 AI 对话标题。"""

    id: str = Field("", description="会话 ID")
    conversationId: str = Field("", description="会话 ID（别名）")
    conversation_id: str = Field("", description="会话 ID（别名）")
    title: str = Field("", description="新标题")

    @property
    def effective_conversation_id(self) -> str:
        return self.id or self.conversationId or self.conversation_id

    model_config = {"extra": "allow"}


class AiConversationIdBody(BaseModel):
    """按 ID 操作 AI 对话（delete 等）。"""

    conversationId: str = Field("", description="会话 ID")
    id: str = Field("", description="会话 ID（别名）")
    conversation_id: str = Field("", description="会话 ID（别名）")

    @property
    def effective_conversation_id(self) -> str:
        return self.conversationId or self.id or self.conversation_id

    model_config = {"extra": "allow"}


__all__ = [
    "MODEL_TYPE_LLM",
    "PERMISSION_PUBLIC",
    "AiModelAdvItem",
    "AiModelConfigBody",
    "AiConfigSourceListQuery",
    "AiConfigIdBody",
    "AiConversationAddBody",
    "AiConversationChatBody",
    "AiConversationUpdateBody",
    "AiConversationIdBody",
]
