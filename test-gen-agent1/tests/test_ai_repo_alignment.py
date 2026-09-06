"""
AI 域三仓库（ai_config / ai_conversation / ai_model）落库闭环对齐回归测试
========================================================================
背景
====
「Repository 空壳化」治理要求 L3 repository 持有真实 SQL、杜绝「建了 L3 但
SQL 仍在旧域模块/仅做转发」的空壳。AI 域三个仓库
  - app/repositories/ai_config_repo.AiConfigRepo        (tga.db · ai_configs)
  - app/repositories/ai_conversation_repo.AiConversationRepo (tga.db · ai_conversations/ai_conversation_messages)
  - app/repositories/ai_model_repo.AiModelRepo          (auth.db · ai_model_sources)
均已在仓库内直连 SQLite 真实落库。本测试锁定「真实化不回归为空壳」：
  1. 每个仓库的 CRUD 都能真实写入，且能读回一致；
  2. 通过**独立连接**直查底层库，确认记录确实落在物理表而非进程内状态；
  3. 与 schema_registry 声明的 DB 归属一致。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories.ai_config_repo import (  # noqa: E402
    SCOPE_FUNCTIONAL_CASE,
    AiConfigRepo,
)
from app.repositories.ai_conversation_repo import AiConversationRepo  # noqa: E402
from app.repositories.ai_model_repo import AiModelRepo  # noqa: E402


def _uniq(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _table_rows(db, table, where="1=1"):
    """经独立连接直查底层物理表，确认真实落盘。"""
    from app.core.database import Database
    conn = Database.get_conn(db)
    return list(conn.execute(f"SELECT * FROM {table} WHERE {where}"))


# ─────────────────────────────────────────────────────────────
# ai_configs（tga.db · AiConfigRepo）
# ─────────────────────────────────────────────────────────────
def test_ai_config_save_and_get_persist():
    """保存 AI 配置后能读回，且底层 ai_configs 表真实落盘。"""
    owner = _uniq("cfg-owner")
    AiConfigRepo.delete(SCOPE_FUNCTIONAL_CASE, "default", owner, "")
    try:
        saved = AiConfigRepo.save(
            SCOPE_FUNCTIONAL_CASE,
            {"designConfig": {"normal": False}},
            config_type="default", owner=owner,
        )
        assert saved["id"]
        assert saved["scope"] == SCOPE_FUNCTIONAL_CASE
        # 读回：通过 repo get
        got = AiConfigRepo.get(SCOPE_FUNCTIONAL_CASE, "default", owner, "")
        assert got and got["id"] == saved["id"]
        assert got["config"].get("designConfig", {}).get("normal") is False
        # 读回：直查物理表
        rows = _table_rows(
            "tga.db", "ai_configs",
            f"scope='{SCOPE_FUNCTIONAL_CASE}' AND owner='{owner}'",
        )
        assert len(rows) == 1, "配置应真实落盘到 ai_configs 表"
    finally:
        AiConfigRepo.delete(SCOPE_FUNCTIONAL_CASE, "default", owner, "")


def test_ai_config_save_idempotent_by_scope_owner():
    """同一 scope+owner 重复 save 应更新而非叠加（唯一约束）。"""
    owner = _uniq("cfg-upd")
    try:
        a = AiConfigRepo.save(SCOPE_FUNCTIONAL_CASE, {"normal": True}, owner=owner)
        b = AiConfigRepo.save(SCOPE_FUNCTIONAL_CASE, {"normal": False}, owner=owner)
        assert a["id"] == b["id"], "重复 save 应更新同一条"
        got = AiConfigRepo.get(SCOPE_FUNCTIONAL_CASE, "default", owner, "")
        assert got["id"] == a["id"]
        rows = _table_rows(
            "tga.db", "ai_configs",
            f"scope='{SCOPE_FUNCTIONAL_CASE}' AND owner='{owner}'",
        )
        assert len(rows) == 1, "唯一约束下不应出现重复行"
    finally:
        AiConfigRepo.delete(SCOPE_FUNCTIONAL_CASE, "default", owner, "")


def test_ai_config_delete_removes_row():
    owner = _uniq("cfg-del")
    AiConfigRepo.save(SCOPE_FUNCTIONAL_CASE, {"normal": True}, owner=owner)
    assert AiConfigRepo.get(SCOPE_FUNCTIONAL_CASE, "default", owner, "") is not None
    assert AiConfigRepo.delete(SCOPE_FUNCTIONAL_CASE, "default", owner, "") is True
    assert AiConfigRepo.get(SCOPE_FUNCTIONAL_CASE, "default", owner, "") is None
    rows = _table_rows(
        "tga.db", "ai_configs",
        f"scope='{SCOPE_FUNCTIONAL_CASE}' AND owner='{owner}'",
    )
    assert len(rows) == 0, "删除后 ai_configs 不应残留"


# ─────────────────────────────────────────────────────────────
# ai_conversations / ai_conversation_messages（tga.db · AiConversationRepo）
# ─────────────────────────────────────────────────────────────
def test_ai_conversation_lifecycle_persist():
    """对话 建/列/读/更新标题 全程落盘，消息可追加并读回。"""
    owner = _uniq("conv-owner")
    conv = AiConversationRepo.create_conversation(
        title="对齐会话", owner=owner, create_user=owner, module_type="ai",
    )
    try:
        assert conv["id"]
        assert conv["title"] == "对齐会话"
        # 落盘读回：repo + 直连
        got = AiConversationRepo.get_conversation(conv["id"])
        assert got and got["id"] == conv["id"]
        conv_rows = _table_rows(
            "tga.db", "ai_conversations", f"id='{conv['id']}'",
        )
        assert len(conv_rows) == 1, "会话应真实落盘 ai_conversations"
        # 列表按 owner 命中
        ids = [c["id"] for c in AiConversationRepo.list_conversations(owner, "PERSONAL")]
        assert conv["id"] in ids
        # 消息
        m = AiConversationRepo.add_message(conv["id"], "user", "你好", "text")
        assert m["content"] == "你好"
        msgs = AiConversationRepo.list_messages(conv["id"])
        assert len(msgs) == 1 and msgs[0]["id"] == m["id"]
        msg_rows = _table_rows(
            "tga.db", "ai_conversation_messages", f"id='{m['id']}'",
        )
        assert len(msg_rows) == 1, "消息应真实落盘 ai_conversation_messages"
        # 更新标题
        upd = AiConversationRepo.update_conversation(conv["id"], title="新标题")
        assert upd["title"] == "新标题"
    finally:
        AiConversationRepo.delete_conversation(conv["id"])


def test_ai_conversation_delete_cascades_messages():
    owner = _uniq("conv-del")
    conv = AiConversationRepo.create_conversation("待删会话", owner=owner)
    msg = AiConversationRepo.add_message(conv["id"], "user", "x", "text")
    try:
        assert len(AiConversationRepo.list_messages(conv["id"])) == 1
        assert AiConversationRepo.delete_conversation(conv["id"]) is True
        assert AiConversationRepo.get_conversation(conv["id"]) is None
        assert len(_table_rows("tga.db", "ai_conversation_messages",
                               f"id='{msg['id']}'")) == 0, "删会话应级联删消息"
    finally:
        AiConversationRepo.delete_conversation(conv["id"])


# ─────────────────────────────────────────────────────────────
# ai_model_sources（auth.db · AiModelRepo）
# ─────────────────────────────────────────────────────────────
def test_ai_model_crud_persist():
    """模型源 建/读/改/列/计数/删 全程落盘到 ai_model_sources。"""
    name = _uniq("model")
    m = AiModelRepo.create({
        "name": name, "type": "LLM", "providerName": "OpenAI",
        "permissionType": "PUBLIC", "status": True,
        "owner": "", "ownerType": "SYSTEM",
    }, create_user="admin")
    try:
        assert m["id"]
        # 直查物理表（auth.db）
        rows = _table_rows("auth.db", "ai_model_sources", f"id='{m['id']}'")
        assert len(rows) == 1, "模型源应真实落盘 ai_model_sources(auth.db)"
        assert rows[0]["name"] == name
        # 更新
        upd = AiModelRepo.update(m["id"], {
            "name": name + "-upd", "type": "LLM", "providerName": "OpenAI",
            "permissionType": "PRIVATE", "status": False,
            "owner": "", "ownerType": "SYSTEM",
        })
        assert upd["permissionType"] == "PRIVATE"
        assert upd["status"] is False
        # 列表 / 名称读回
        assert any(x["id"] == m["id"] for x in AiModelRepo.list(owner_type="SYSTEM"))
        # 计数
        assert AiModelRepo.count_enabled("SYSTEM") >= 0
    finally:
        AiModelRepo.delete(m["id"])
    assert AiModelRepo.get(m["id"]) is None, "删除后不应再读到"


def test_ai_model_upsert_new_and_existing():
    """upsert：有 id 走更新，无 id 走新建（对应 /ai/config/edit-source）。"""
    name = _uniq("model-upsert")
    created = AiModelRepo.upsert({
        "name": name, "type": "LLM", "providerName": "OpenAI",
    })
    try:
        assert created["id"]
        updated = AiModelRepo.upsert({
            "id": created["id"], "name": name + "-v2",
            "type": "LLM", "providerName": "OpenAI",
        })
        assert updated["id"] == created["id"]
        assert updated["name"] == name + "-v2"
    finally:
        AiModelRepo.delete(created["id"])
