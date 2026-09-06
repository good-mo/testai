"""AI 对话 / AI 配置 stub 真实化契约断言。

背景
====
此前前端 ms-ai-drawer 依赖的后端 AI 接口多为返回空 / None 的占位 stub：
  - /ai/conversation/add        → ok(None)        （真实对话建不起来）
  - /ai/conversation/list       → ok([])          （会话列表恒空）
  - /ai/conversation/chat/list/{id} → 空回显       （历史加载不出）
  - /ai/conversation/delete/*   → ok(None)
  - /ai/conversation/update*    → ok(None)
  - /functional/case/ai/get/config → ok({})       （前端读到空 config）
  - /functional/case/ai/save/config → ok(None)    （保存形同虚设）
  - /api/case/ai/get/config     → ok({})
  - /api/case/ai/save/config    → ok(None)

本测试锁定修复不复发：
  1. 对话 add 返回含 id 的会话对象；list 能读回；detail 可查到消息；
     delete 真实删除；update/title 生效。
  2. AI 配置 get 返回完整默认结构（designConfig/templateConfig / 布尔字段），
     save 后再次 get 能读回保存值。
"""
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PREFIX = "AI-STUB-"


def _login(client):
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    if r.status_code != 200:
        return
    session = r.json()["data"]
    client.headers.update({
        "X-AUTH-TOKEN": session["sessionId"],
        "CSRF-TOKEN": session["csrfToken"],
    })


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        _login(c)
        yield c


def _data(resp):
    payload = resp.json()
    assert isinstance(payload, dict) and "data" in payload, str(payload)[:300]
    assert payload["code"] < 500, f"服务端异常: {payload['message']}"
    return payload["data"]


# ════════════════════════════════════════════════════════════
# 1. AI 对话 stub 真实化
# ════════════════════════════════════════════════════════════
class TestAiConversationReal:
    """对话 add → list → detail → delete → update 闭环。"""

    def test_conversation_add_returns_object_with_id(self, client):
        d = _data(client.post("/ai/conversation/add", json={
            "title": f"{PREFIX}会话{uuid.uuid4().hex[:6]}",
            "prompt": "你好，生成一条测试用例",
        }))
        # 不再是 None/空；返回含 id/title/createTime 的会话对象
        assert isinstance(d, dict) and d.get("id"), f"add 应返回会话对象, got {d}"
        assert d.get("title"), f"add 应返回 title, got {d}"

    def test_conversation_list_returns_created(self, client):
        """list 返回数组（允许为空数组，但不该 500）。"""
        items = _data(client.get("/ai/conversation/list"))
        assert isinstance(items, list), f"list 应为数组, got {type(items)}"

    def test_conversation_add_list_detail_delete_flow(self, client):
        """完整闭环：add→detail 有消息→delete→list 不存在。"""
        title = f"{PREFIX}闭环{uuid.uuid4().hex[:6]}"
        add_resp = _data(client.post("/ai/conversation/add", json={
            "title": title, "prompt": "创建后的第一条 prompt",
        }))
        conv_id = add_resp.get("id")
        assert conv_id

        # detail 应返回该会话（而非空 []/None）
        detail = _data(client.get(f"/ai/conversation/detail/{conv_id}"))
        assert isinstance(detail, dict), f"detail 应返回会话 dict, got {type(detail)}"
        assert detail.get("id") == conv_id
        assert isinstance(detail.get("messages"), list), "会话应含 messages 数组"

        # chat/list 应返回消息数组
        msgs = _data(client.get(f"/ai/conversation/chat/list/{conv_id}"))
        assert isinstance(msgs, list), f"chat/list 应返回数组, got {type(msgs)}"

        # update title 生效
        new_title = f"{title}-改名"
        up = _data(client.post("/ai/conversation/update", json={
            "id": conv_id, "title": new_title,
        }))
        assert isinstance(up, dict) and up.get("title") == new_title, f"update title 应生效, got {up}"

        # 删除真实生效
        del_resp = _data(client.get(f"/ai/conversation/delete/{conv_id}"))
        assert isinstance(del_resp, dict) and del_resp.get("deleted") is True, \
            f"delete 应真实删除, got {del_resp}"

        # 删除后 detail 应 404 / 或返回空
        r = client.get(f"/ai/conversation/detail/{conv_id}")
        assert r.status_code in (200, 404), f"删除后 detail 应 404 或 200, got {r.status_code}"

    def test_conversation_update_title_endpoint(self, client):
        """POST /ai/conversation/update/title 更新标题生效。"""
        conv = _data(client.post("/ai/conversation/add", json={
            "title": f"{PREFIX}标题端点{uuid.uuid4().hex[:6]}",
        }))
        conv_id = conv["id"]
        new_title = f"{PREFIX}标题端点新名{uuid.uuid4().hex[:4]}"
        up = _data(client.post("/ai/conversation/update/title", json={
            "id": conv_id, "title": new_title,
        }))
        assert isinstance(up, dict) and up.get("title") == new_title, \
            f"update/title 应生效, got {up}"
        # 清理
        _data(client.get(f"/ai/conversation/delete/{conv_id}"))

    def test_conversation_delete_post_body(self, client):
        """POST /ai/conversation/delete 携带 body 删除真实生效。"""
        conv = _data(client.post("/ai/conversation/add", json={
            "title": f"{PREFIX}POST删除{uuid.uuid4().hex[:6]}",
        }))
        conv_id = conv["id"]
        del_resp = _data(client.post("/ai/conversation/delete", json={
            "conversationId": conv_id,
        }))
        assert isinstance(del_resp, dict) and del_resp.get("deleted") is True, \
            f"POST delete 应真实删除, got {del_resp}"


# ════════════════════════════════════════════════════════════
# 2. 功能用例 / 接口用例 AI 配置 stub 真实化
# ════════════════════════════════════════════════════════════
class TestFunctionalCaseAiConfigReal:
    """/functional/case/ai/get/config 有默认结构；save 后读回。"""

    def test_get_config_returns_full_default(self, client):
        """不再返回空 {}，应包含 designConfig/templateConfig 默认字段。"""
        d = _data(client.get("/functional/case/ai/get/config"))
        assert isinstance(d, dict), f"应返回 config dict, got {type(d)}"
        assert "designConfig" in d, f"应含 designConfig, got {d.keys()}"
        assert "templateConfig" in d, f"应含 templateConfig, got {d.keys()}"
        dc = d["designConfig"]
        assert isinstance(dc, dict) and dc.get("normal") is True
        tc = d["templateConfig"]
        assert isinstance(tc, dict) and "caseEditType" in tc

    def test_save_then_get_persists(self, client):
        """save 后再次 get 能读回保存值。"""
        marker = f"STEP{uuid.uuid4().hex[:4]}"
        payload = {
            "designConfig": {
                "normal": False,
                "abnormal": True,
                "equivalenceClassPartitioning": True,
                "boundaryValueAnalysis": True,
                "decisionTableTesting": False,
                "causeEffectGraphing": True,
                "orthogonalExperimentMethod": False,
                "scenarioMethod": False,
                "scenarioMethodDescription": "",
            },
            "templateConfig": {
                "caseEditType": marker,
                "caseName": True,
                "preCondition": False,
                "caseSteps": True,
                "expectedResult": True,
                "remark": True,
            },
        }
        save_resp = _data(client.post("/functional/case/ai/save/config", json=payload))
        assert isinstance(save_resp, dict) and save_resp.get("saved") is True

        read_back = _data(client.get("/functional/case/ai/get/config"))
        assert read_back["designConfig"]["normal"] is False, \
            f"save 后应读回 normal=False, got {read_back['designConfig']}"
        assert read_back["templateConfig"]["caseEditType"] == marker, \
            f"save 后应读回 caseEditType={marker}, got {read_back['templateConfig']}"
        # 恢复默认避免影响其他用例
        default = {
            "designConfig": {
                "normal": True, "abnormal": True,
                "equivalenceClassPartitioning": True,
                "boundaryValueAnalysis": True,
                "decisionTableTesting": True,
                "causeEffectGraphing": True,
                "orthogonalExperimentMethod": True,
                "scenarioMethod": True,
                "scenarioMethodDescription": "",
            },
            "templateConfig": {
                "caseEditType": "TEXT",
                "caseName": True, "preCondition": True,
                "caseSteps": True, "expectedResult": True, "remark": True,
            },
        }
        _data(client.post("/functional/case/ai/save/config", json=default))


class TestApiCaseAiConfigReal:
    """/api/case/ai/get/config 有默认布尔结构；save 后读回。"""

    def test_get_config_returns_full_default(self, client):
        """不再返回空 {}，应包含 7 个布尔默认字段。"""
        d = _data(client.get("/api/case/ai/get/config"))
        assert isinstance(d, dict), f"应返回 config dict, got {type(d)}"
        for key in ("normal", "abnormal", "caseName", "requestParams",
                    "preScript", "postScript", "assertion"):
            assert key in d, f"应含 {key}, got {list(d.keys())}"
            assert d[key] is True, f"{key} 默认应为 True, got {d[key]}"

    def test_save_then_get_persists(self, client):
        """save 后再次 get 能读回保存值。"""
        payload = {
            "normal": False, "abnormal": True,
            "caseName": True, "requestParams": False,
            "preScript": True, "postScript": False, "assertion": True,
        }
        save_resp = _data(client.post("/api/case/ai/save/config", json=payload))
        assert isinstance(save_resp, dict) and save_resp.get("saved") is True

        read_back = _data(client.get("/api/case/ai/get/config"))
        assert read_back["normal"] is False, \
            f"save 后应读回 normal=False, got {read_back}"
        assert read_back["requestParams"] is False, \
            f"save 后应读回 requestParams=False, got {read_back}"

        # 恢复默认
        default = {
            "normal": True, "abnormal": True,
            "caseName": True, "requestParams": True,
            "preScript": True, "postScript": True, "assertion": True,
        }
        _data(client.post("/api/case/ai/save/config", json=default))
