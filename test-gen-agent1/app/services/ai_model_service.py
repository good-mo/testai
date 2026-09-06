# app/services/ai_model_service.py
"""AI 模型源业务逻辑层（ai_model 域 DDD 接入 · 阶段 C 薄门面）。

数据访问已收敛到 ai_model 域 DDD 应用服务 `ai_model_app_service`
（见 `app/domain/ai_model/`）。本 Service 收敛为对 DDD 应用门面的**薄委托门面**，
仅保留既有方法签名以兼容 `auth/router_system`、`routers/ai_config`、
`routers/other_compat` 等调用方，返回结构与重构前一致（camelCase），
对外 API 零回归、可回滚。

保留在 Service 层的仅剩「基于 env 的系统默认模型源引导」`_ensure_system_default`
（独立于聚合业务的种子逻辑，不属于旁路双写），以及前端依赖的 `createUserName`
展示字段的补齐（DDD 聚合只输出 createUser，前端创建人列需 createUserName）。
"""
from typing import Dict, List, Optional

from app.config import settings
from app.domain.ai_model.application.ai_model_app_service import ai_model_app_service as _ddd
from app.domain.ai_model.application.dto import (
    DeleteModelCommand,
    GetModelCommand,
    ListModelsCommand,
)
from app.domain.ai_model.domain.entities.ai_model import (
    MODEL_TYPE_LLM,
    OWNER_TYPE_PERSONAL,
    OWNER_TYPE_SYSTEM,
    PERMISSION_PUBLIC,
)
from app.repositories.ai_model_repo import ai_model_repo


def _with_creator(d: Optional[dict]) -> Optional[dict]:
    """补齐前端展示字段 createUserName（值同 createUser，恒兼容）。"""
    if not d:
        return d
    if "createUserName" not in d:
        d = dict(d)
        d["createUserName"] = d.get("createUser", "admin")
    return d


class AiModelService:
    """AI 模型源服务：router 层唯一业务入口（DDD 薄门面）。"""

    # ── 默认模型名 / 供应商映射 ──────────────────────────
    _DEFAULT_NAME_BY_PROVIDER = {
        "DeepSeek": "DeepSeek 默认模型",
        "Open AI": "OpenAI 默认模型",
        "ZhiPu AI": "智谱 AI 默认模型",
    }

    def _provider_of(self) -> str:
        """由后端配置推断模型供应商展示名。"""
        provider = (settings.llm_provider or "openai").lower()
        if provider == "azure":
            return "Open AI"
        if provider in ("deepseek",):
            return "DeepSeek"
        if provider in ("zhipu", "zhipuai", "glm"):
            return "ZhiPu AI"
        # openai / local（OpenAI 兼容端点）默认归 OpenAI
        return "Open AI"

    def _default_name(self, provider_name: str) -> str:
        return self._DEFAULT_NAME_BY_PROVIDER.get(provider_name, "AI 默认模型")

    # ── 系统内置源种子（env 配置可见即可用）───────────────
    def _ensure_system_default(self) -> Dict[str, object]:
        """确保存在一条基于环境配置的系统模型源。

        若表内已有启用中的系统源则原样返回，否则按 .env/环境变量
        生成一条默认「OpenAI / LLM」系统源，保证模型列表不再为空。
        """
        existing = ai_model_repo.list(owner_type=OWNER_TYPE_SYSTEM)
        if existing:
            return existing[0]
        provider_name = self._provider_of()
        default = ai_model_repo.create({
            "name": self._default_name(provider_name),
            "type": MODEL_TYPE_LLM,
            "providerName": provider_name,
            "permissionType": PERMISSION_PUBLIC,
            "status": True,
            "owner": "",
            "ownerType": OWNER_TYPE_SYSTEM,
            "baseName": settings.llm_model or "gpt-4o",
            "appKey": settings.openai_api_key or settings.azure_api_key or "",
            "apiUrl": settings.openai_api_base or settings.azure_endpoint or "",
            "advSettingDTOList": [],
        }, create_user="admin")
        return default or {}

    # ── 列表 ──────────────────────────────────────────────
    def list(self, owner_type: str = OWNER_TYPE_SYSTEM, owner: str = "",
             keyword: str = "", provider_name: str = "") -> List[Dict]:
        rows = _ddd.list(ListModelsCommand(
            owner_type=owner_type, owner=owner,
            keyword=keyword, provider_name=provider_name,
        ))
        # 系统侧为空时补内置默认源，保证「所有界面都有数据记录」
        if owner_type == OWNER_TYPE_SYSTEM and not rows:
            self._ensure_system_default()
            rows = _ddd.list(ListModelsCommand(
                owner_type=owner_type, owner=owner,
                keyword=keyword, provider_name=provider_name,
            ))
        return [_with_creator(r) for r in rows]

    def list_system(self, keyword: str = "", provider_name: str = "") -> List[Dict]:
        return self.list(owner_type=OWNER_TYPE_SYSTEM, keyword=keyword,
                         provider_name=provider_name)

    def list_personal(self, owner: str, keyword: str = "",
                      provider_name: str = "") -> List[Dict]:
        return self.list(owner_type=OWNER_TYPE_PERSONAL, owner=owner,
                         keyword=keyword, provider_name=provider_name)

    # ── 名称下拉（AI 对话默认模型列表）──────────────────
    def name_options(self, owner_type: str = OWNER_TYPE_SYSTEM,
                     owner: str = "") -> List[Dict]:
        """返回 [{id, name}]，仅启用中源。"""
        rows = self.list(owner_type=owner_type, owner=owner)
        return [
            {"id": r.get("id", ""), "name": r.get("name", "")}
            for r in rows if r.get("status")
        ]

    # ── 详情 ──────────────────────────────────────────────
    def get(self, model_id: str) -> Optional[Dict]:
        if not model_id:
            return None
        return _with_creator(_ddd.get(GetModelCommand(model_id=model_id)))

    def get_or_default(self, model_id: str = "") -> Dict:
        """获取模型详情；空 id 时返回默认系统源（兼容 /ai/config/get 无参调用）。"""
        if model_id:
            model = _with_creator(_ddd.get(GetModelCommand(model_id=model_id)))
            if model:
                return model
        return self._ensure_system_default()

    # ── 新建 / 编辑 / 删除 ────────────────────────────────
    def save(self, data: Dict, operator: str = "admin",
             owner_type: str = OWNER_TYPE_SYSTEM,
             owner: str = "") -> Dict:
        """编辑模型源：有 id 走更新，无 id 走新增。"""
        payload = dict(data or {})
        payload.setdefault("ownerType", owner_type)
        if owner_type == OWNER_TYPE_PERSONAL:
            payload.setdefault("owner", owner)
            payload.setdefault("permissionType", PERMISSION_PUBLIC)
        return _with_creator(_ddd.upsert(payload, create_user=operator)) or {}

    def delete(self, model_id: str) -> bool:
        if not model_id:
            return False
        return _ddd.delete(DeleteModelCommand(model_id=model_id))


ai_model_service = AiModelService()


__all__ = ["ai_model_service", "AiModelService"]
