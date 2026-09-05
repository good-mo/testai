# app/routers/ai_config.py
"""业务域路由：ai_config 兼容路由。

包含：
  - AI 配置源（/ai/config/*）: 已真实化（ai_model_service）
  - AI 对话（/ai/conversation/*）: stub 真实化，落真实表持久化会话与消息

请求体统一收敛到 `app/models/ai_config.py` 中已建档的 Pydantic 模型做字段
归一，不再手写 `_extract_str` 逐个取 key；兼容字段别名与默认值语义均内聚在
模型层（`effective_*` 属性），路由只消费模型的归一结果。
"""

from fastapi import APIRouter, Request

from app.core.response import fail, ok, page_result, read_body
from app.core.helpers import as_model, current_user_name
from app.logging_config import get_logger
from app.models.ai_config import (
    AiConfigIdBody,
    AiConfigSourceListQuery,
    AiConversationAddBody,
    AiConversationChatBody,
    AiConversationIdBody,
    AiConversationUpdateBody,
    AiModelConfigBody,
)

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-ai_config"])


# ════════════════════════════════════════════════════════════
# AI 配置源（真实，已由 ai_model_service 承载）
# ════════════════════════════════════════════════════════════

@router.get("/ai/config/get")
def ai_config_get():
    """获取 AI 配置（默认系统模型源；无参兼容旧调用）。"""
    from app.services.ai_model_service import ai_model_service
    return ok(ai_model_service.get_or_default())


@router.delete("/ai/config/delete")
async def ai_config_delete(request: Request):
    """删除 AI 配置（body/query 携带 id 时真实删除）。"""
    body = await read_body(request)
    model_id = as_model(body, AiConfigIdBody).id
    if model_id:
        from app.services.ai_model_service import ai_model_service
        ai_model_service.delete(model_id)
    return ok()


@router.post("/ai/config/edit-source")
async def ai_config_edit_source(request: Request):
    """编辑 AI 配置源（真实落库：有 id 更新、无 id 新建）。

    整体提交模型源配置，经 `AiModelConfigBody` 校验后透传
    ai_model_service.save（仅保留客户端实发字段，等价旧直接传 body）。
    """
    from app.services.ai_model_service import ai_model_service
    body = await read_body(request)
    if not isinstance(body, dict) or not body:
        return fail("缺少模型配置参数", 400)
    cfg = as_model(body, AiModelConfigBody)
    operator = current_user_name(request)
    saved = ai_model_service.save(
        cfg.model_dump(exclude_unset=True), operator=operator)
    return ok(saved)


@router.delete("/ai/config/delete/{config_id}")
@router.post("/ai/config/delete/{config_id}")
def ai_config_delete_path(config_id: str):
    """删除 AI 配置（带路径参数，真实删除）。"""
    from app.services.ai_model_service import ai_model_service
    ok_flag = ai_model_service.delete(config_id)
    return ok({"id": config_id, "deleted": ok_flag})


@router.get("/ai/config/delete/{config_id}")
def ai_config_delete_get_path(config_id: str):
    """删除 AI 配置（GET 带路径参数，与前端调用一致，真实删除）。"""
    from app.services.ai_model_service import ai_model_service
    ok_flag = ai_model_service.delete(config_id)
    return ok({"id": config_id, "deleted": ok_flag})


@router.get("/ai/config/get/{config_id}")
def ai_config_get_path(config_id: str):
    """获取 AI 配置详情（真实数据）。"""
    from app.services.ai_model_service import ai_model_service
    model = ai_model_service.get(config_id)
    if not model:
        return fail("模型不存在", 404)
    return ok(model)


@router.post("/ai/config/source/list")
async def ai_config_source_list_post(request: Request):
    """系统设置-查看模型集合（POST 分页，getModelConfigList 真实调用）。"""
    from app.services.ai_model_service import ai_model_service
    body = await read_body(request)
    q = as_model(body, AiConfigSourceListQuery)
    owner = q.owner
    provider_name = q.providerName
    keyword = q.keyword
    current = q.current
    page_size = q.pageSize
    owner_type = "PERSONAL" if owner else "SYSTEM"
    items = ai_model_service.list(
        owner_type=owner_type, owner=owner,
        keyword=keyword, provider_name=provider_name,
    )
    return page_result(items, len(items), current=current, page_size=page_size)


# ════════════════════════════════════════════════════════════
# AI 对话（真实持久化）
# ════════════════════════════════════════════════════════════

def _ai_service():
    """延迟导入避免循环依赖。"""
    from app.services.ai_config_service import ai_config_service
    return ai_config_service


def _chat_title(prompt: str) -> str:
    """由 prompt 生成会话标题（首 20 字符 + 省略号，空则「新对话」）。"""
    if not prompt:
        return "新对话"
    return (prompt[:20] + "…") if len(prompt) > 20 else prompt


@router.post("/ai/conversation/add")
async def ai_conversation_add(request: Request):
    """新增 AI 对话（真实落库，返回会话对象）。"""
    body = await read_body(request)
    add = as_model(body, AiConversationAddBody)
    title = add.effective_title.strip() or "新对话"
    prompt = add.effective_prompt
    owner = current_user_name(request)
    project_id = add.effective_project_id
    module_type = add.effective_module_type

    conv = _ai_service().create_conversation(
        title=title,
        owner=owner,
        create_user=owner,
        project_id=project_id,
        module_type=module_type,
        extra={"isNew": False},
    )
    # 首个 prompt 作为首条 user 消息保存
    if prompt:
        _ai_service().add_message(
            conversation_id=conv["id"], role="user",
            content=prompt, msg_type="text",
        )
    return ok(conv)


@router.get("/ai/conversation/list")
def ai_conversation_list(request: Request):
    """获取 AI 对话列表（按当前用户）。"""
    owner = current_user_name(request)
    module_type = request.query_params.get("moduleType", "") if request else ""
    items = _ai_service().list_conversations(
        owner=owner, owner_type="PERSONAL", module_type=module_type,
    )
    return ok(items)


@router.get("/ai/conversation/chat/list/{conversation_id}")
def ai_conversation_chat_list_path(conversation_id: str):
    """获取 AI 对话消息历史（chat/list/{id}）。"""
    conv = _ai_service().get_conversation(conversation_id)
    if not conv:
        return ok([])
    messages = _ai_service().list_messages(conversation_id)
    return ok(messages)


@router.get("/ai/conversation/detail/{conversation_id}")
def ai_conversation_detail(conversation_id: str):
    """获取 AI 对话详情。"""
    conv = _ai_service().get_conversation(conversation_id)
    if not conv:
        return fail("对话不存在", 404)
    messages = _ai_service().list_messages(conversation_id)
    conv["messages"] = messages
    return ok(conv)


@router.get("/ai/conversation/delete/{conversation_id}")
def ai_conversation_delete_path(conversation_id: str):
    """删除 AI 对话（带路径参数，真实删除）。"""
    ok_flag = _ai_service().delete_conversation(conversation_id)
    return ok({"id": conversation_id, "deleted": ok_flag})


@router.post("/ai/conversation/delete")
async def ai_conversation_delete(request: Request):
    """删除 AI 对话（POST 带 body，真实删除）。"""
    body = await read_body(request)
    del_body = as_model(body, AiConversationIdBody)
    conv_id = del_body.effective_conversation_id
    if not conv_id:
        return ok()
    ok_flag = _ai_service().delete_conversation(conv_id)
    return ok({"id": conv_id, "deleted": ok_flag})


@router.post("/ai/conversation/update")
async def ai_conversation_update(request: Request):
    """更新 AI 对话标题（POST 带 body）。"""
    body = await read_body(request)
    up = as_model(body, AiConversationUpdateBody)
    conv_id = up.effective_conversation_id
    title = up.title
    if not conv_id:
        return fail("缺少对话 id", 400)
    updated = _ai_service().update_conversation(
        conversation_id=conv_id, title=title or None,
    )
    if not updated:
        return fail("对话不存在", 404)
    return ok(updated)


@router.post("/ai/conversation/update/title")
async def ai_conversation_update_title(request: Request):
    """更新 AI 对话标题（专用 update/title 端点）。"""
    body = await read_body(request)
    up = as_model(body, AiConversationUpdateBody)
    conv_id = up.effective_conversation_id
    title = up.title
    if not conv_id:
        return fail("缺少对话 id", 400)
    updated = _ai_service().update_conversation(
        conversation_id=conv_id, title=title or None,
    )
    if not updated:
        return fail("对话不存在", 404)
    return ok(updated)


@router.get("/ai/conversation/chat/list")
def ai_conversation_chat_list(request: Request):
    """AI 对话列表（兼容 GET 无参）。"""
    return ai_conversation_list(request)


@router.post("/ai/conversation/chat")
async def ai_conversation_chat(request: Request):
    """AI 对话（写消息 + 空回复占位，真实落库）。

    该端点承载 AI 对话消息发送：读取 body 中的 prompt/message/conversationId，
    将用户消息真实持久化。AI 内容生成由具体业务 chat 端点承载（见
    /functional/case/ai/chat、/api/case/ai/chat），此端点保持兼容返回结构。
    """
    body = await read_body(request)
    chat = as_model(body, AiConversationChatBody)
    prompt = chat.effective_prompt
    conv_id = chat.effective_conversation_id
    # 会话不存在且带 prompt → 尝试新建会话
    if not conv_id:
        conv = _ai_service().create_conversation(
            title=_chat_title(prompt),
            owner=current_user_name(request),
        )
        conv_id = conv["id"]
    else:
        conv = _ai_service().get_conversation(conv_id)
        if not conv:
            conv = _ai_service().create_conversation(
                title=_chat_title(prompt),
                owner=current_user_name(request),
            )
            conv_id = conv["id"]
    if prompt:
        _ai_service().add_message(
            conversation_id=conv_id, role="user", content=prompt, msg_type="text",
        )
    return ok({
        "id": conv_id,
        "content": "",
        "conversationId": conv_id,
    })


@router.post("/ai/conversation")
async def ai_conversation(request: Request):
    """AI 对话（兼容旧调用：写消息并返回 conversationId）。"""
    body = await read_body(request)
    chat = as_model(body, AiConversationChatBody)
    prompt = chat.effective_prompt
    conv_id = chat.effective_conversation_id
    if not conv_id:
        conv = _ai_service().create_conversation(
            title=_chat_title(prompt),
            owner=current_user_name(request),
        )
        conv_id = conv["id"]
    elif not _ai_service().get_conversation(conv_id):
        conv = _ai_service().create_conversation(
            title=_chat_title(prompt),
            owner=current_user_name(request),
        )
        conv_id = conv["id"]
    if prompt:
        _ai_service().add_message(
            conversation_id=conv_id, role="user", content=prompt, msg_type="text",
        )
    return ok({
        "content": "",
        "conversationId": conv_id,
    })


# 工作台路由已迁移至 app/test_plan/router_dashboard_{home,layout,stats,mine}.py


# 测试计划路由已迁移至 app/test_plan/ 模块


# ── 更多场景/调试适配 ───────────────────────────────────
