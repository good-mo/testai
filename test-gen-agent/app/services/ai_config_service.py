"""AI 用例生成配置 & AI 对话业务逻辑层（ai_config 域 DDD 接入 · 阶段 C 薄门面）。

本层涵盖两个子域：
  - ai_config      — 功能用例 / 接口用例的 AI 生成配置（save / get / 默认合并）
  - ai_conversation— AI 对话会话与消息的持久化管理

其中 **ai_config 子域** 的数据访问已收敛到 `app/domain/ai_config/` DDD 应用
服务 `ai_config_app_service`，本 Service 对该子域的 4 个方法（save/get × 2 scope）
收敛为**薄委托门面**，默认兜底合并逻辑与对外 camelCase 契约保持不变。

**ai_conversation 子域** 尚无对应 DDD 域，继续直连 `AiConversationRepo`（属既有
独立子域，非本接线范围）。

路由不再直接 import repo，统一经本 Service 访问数据。
"""
from typing import Any, Dict, List, Optional

from app.domain.ai_config.application.ai_config_app_service import ai_config_app_service as _ddd
from app.domain.ai_config.application.dto import (
    GetAiConfigCommand,
    SaveAiConfigCommand,
)
from app.repositories.ai_config_repo import (
    SCOPE_API_CASE,
    SCOPE_FUNCTIONAL_CASE,
    merge_api_ai_config,
    merge_case_ai_config,
)
from app.repositories.ai_conversation_repo import AiConversationRepo


def _saved_row(config_value: Dict[str, Any]) -> Dict[str, Any]:
    """把合并兜底所需的结构转成 merge 函数可消费的形态。"""
    return {"config": config_value or {}}


class AiConfigService:
    """AI 配置与对话服务：router 层唯一业务入口。"""

    # ═══════════════════════════════════════════════════════
    # ai_config 子域 —— 功能用例 AI 配置（DDD 薄门面）
    # ═══════════════════════════════════════════════════════

    def save_functional_case_config(
        self, config_value: Dict[str, Any],
        owner: str = "", project_id: str = "",
        create_user: str = "admin",
    ) -> Dict[str, Any]:
        """保存功能用例 AI 配置（经 DDD 应用门面）。"""
        saved = _ddd.save(SaveAiConfigCommand(
            scope=SCOPE_FUNCTIONAL_CASE,
            config_value=config_value or {},
            owner=owner, project_id=project_id, create_user=create_user,
        ))
        return saved or {}

    def get_functional_case_config(
        self, owner: str = "", project_id: str = "",
    ) -> Dict[str, Any]:
        """获取功能用例 AI 配置（带默认兜底）。"""
        saved = _ddd.get(GetAiConfigCommand(
            scope=SCOPE_FUNCTIONAL_CASE, owner=owner, project_id=project_id,
        ))
        cfg = saved.get("config_value") if saved else None
        return merge_case_ai_config(_saved_row(cfg) if cfg is not None else None)

    # ═══════════════════════════════════════════════════════
    # ai_config 子域 —— 接口用例 AI 配置（DDD 薄门面）
    # ═══════════════════════════════════════════════════════

    def save_api_case_config(
        self, config_value: Dict[str, Any],
        owner: str = "", project_id: str = "",
        create_user: str = "admin",
    ) -> Dict[str, Any]:
        """保存接口用例 AI 配置（经 DDD 应用门面）。"""
        saved = _ddd.save(SaveAiConfigCommand(
            scope=SCOPE_API_CASE,
            config_value=config_value or {},
            owner=owner, project_id=project_id, create_user=create_user,
        ))
        return saved or {}

    def get_api_case_config(
        self, owner: str = "", project_id: str = "",
    ) -> Dict[str, Any]:
        """获取接口用例 AI 配置（带默认兜底）。"""
        saved = _ddd.get(GetAiConfigCommand(
            scope=SCOPE_API_CASE, owner=owner, project_id=project_id,
        ))
        cfg = saved.get("config_value") if saved else None
        return merge_api_ai_config(_saved_row(cfg) if cfg is not None else None)

    # ═══════════════════════════════════════════════════════
    # ai_conversation 子域 —— AI 对话会话（无 DDD 域，维持原直连）
    # ═══════════════════════════════════════════════════════

    def list_conversations(self, owner: str = "",
                           owner_type: str = "PERSONAL",
                           module_type: str = "") -> List[Dict[str, Any]]:
        """列出当前用户会话。"""
        return AiConversationRepo.list_conversations(
            owner=owner, owner_type=owner_type, module_type=module_type,
        )

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取会话详情。"""
        return AiConversationRepo.get_conversation(conversation_id)

    def create_conversation(self, title: str = "新对话",
                            owner: str = "", create_user: str = "admin",
                            project_id: str = "", module_type: str = "ai",
                            extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建会话。"""
        return AiConversationRepo.create_conversation(
            title=title, owner=owner, create_user=create_user,
            project_id=project_id, module_type=module_type, extra=extra,
        )

    def update_conversation(self, conversation_id: str,
                            title: Optional[str] = None,
                            extra: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """更新会话标题或 meta。"""
        return AiConversationRepo.update_conversation(
            conversation_id=conversation_id, title=title, extra=extra,
        )

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话（级联删消息）。"""
        return AiConversationRepo.delete_conversation(conversation_id)

    # ═══════════════════════════════════════════════════════
    # ai_conversation 子域 —— AI 对话消息（无 DDD 域，维持原直连）
    # ═══════════════════════════════════════════════════════

    def add_message(self, conversation_id: str, role: str = "user",
                    content: str = "", msg_type: str = "text",
                    extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """向会话追加消息。"""
        return AiConversationRepo.add_message(
            conversation_id=conversation_id, role=role,
            content=content, msg_type=msg_type, extra=extra,
        )

    def list_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取会话消息列表。"""
        return AiConversationRepo.list_messages(conversation_id)

    # ── 便捷编排：确保会话存在 ─────────────────────────────
    def ensure_conversation(
        self, conversation_id: str, owner: str = "",
        title: str = "新对话", create_user: str = "admin",
    ) -> Dict[str, Any]:
        """确保会话存在；不存在则按 owner 创建并返回新会话。"""
        if conversation_id:
            existing = AiConversationRepo.get_conversation(conversation_id)
            if existing:
                return existing
        return AiConversationRepo.create_conversation(
            title=title, owner=owner, create_user=create_user,
        )

    # ── 便捷编排：对话 + 写首条消息 ────────────────────────
    def chat(self, conversation_id: str, prompt: str = "",
             owner: str = "", create_user: str = "",
             title: str = "") -> Dict[str, Any]:
        """AI 对话编排：定位/创建会话并写入用户消息。"""
        if not create_user:
            create_user = owner or "admin"
        conv = self.ensure_conversation(
            conversation_id=conversation_id, owner=owner,
            title=title or "新对话", create_user=create_user,
        )
        cid = conv["id"]
        if prompt:
            AiConversationRepo.add_message(
                conversation_id=cid, role="user",
                content=prompt, msg_type="text",
            )
        return conv


# 模块级单例（与其它 service 风格一致）
ai_config_service = AiConfigService()


__all__ = ["ai_config_service", "AiConfigService"]
