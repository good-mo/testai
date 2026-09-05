"""DDD message 域 A→B→C 渐进迁移回归测试。

背景
----
`app/domain/message/` DDD 层（阶段 A）就绪后，本测试锁定「阶段 B/C」接入契约：
  - 阶段 C：`app/services/message_service.py` 的机器人 CRUD/启停与站内通知
    （list/unread/set_read/set_read_all）已委托 `message_app_service`；
  - 阶段 B：Router 经薄 Service → DDD 门面 → 聚合完成机器人/通知读写；
  - 消息设置树/接收人/模板详情等富 schema 视图仍保留在 Service（双轨并存零破坏）。

本测试以 Service 为界验证迁移后行为与旧契约一致，作为逐域切换的回归基线。
"""
import uuid

from app.repositories.message_repo import MessageRepo
from app.services.message_service import message_service as svc

TAG = "msgmig"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _cleanup_robot(rid: str) -> None:
    try:
        MessageRepo.delete_robot(rid)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 一、机器人 CRUD/启停 委托 DDD（阶段 C）
# ═══════════════════════════════════════════════════════════
def test_robot_crud_delegates():
    r = svc.create_robot({"name": _mk(), "platform": "WECHAT", "type": "CUSTOM",
                          "webhook": "http://hook", "create_user": "admin"})
    rid = r["id"]
    try:
        assert rid and r["platform"] == "WECHAT"
        got = svc.get_robot(rid)
        assert got is not None and got["id"] == rid
        # 内置机器人生成守卫由 DDD 守护
        assert svc.get_robot("IN_SITE") is not None
        assert svc.update_robot(rid, {"name": "renamed"}) is True
        assert svc.set_robot_enable(rid, False) is True
        assert svc.delete_robot(rid) is True
    finally:
        _cleanup_robot(rid)


def test_builtin_robot_cannot_create():
    import pytest
    with pytest.raises(ValueError):
        svc.create_robot({"name": "x", "platform": "IN_SITE"})


def test_list_robots_shape():
    rows = svc.list_robots("")
    assert isinstance(rows, list)
    assert all({"id", "name", "platform", "enable"} <= set(r) for r in rows)


# ═══════════════════════════════════════════════════════════
# 二、站内通知 委托 DDD 门面
# ═══════════════════════════════════════════════════════════
def test_notification_read_paths():
    lst = svc.list_notifications(receiver="admin", current=1, page_size=5)
    assert "list" in lst and "total" in lst
    assert isinstance(lst["list"], list)
    assert isinstance(svc.unread_count(receiver="admin"), int)


def test_notification_set_read_idempotent():
    """对不存在的通知 set_read 返回 False（委托 DDD 不抛异常）。"""
    assert svc.set_read(f"nope_{uuid.uuid4().hex[:6]}") is False


# ═══════════════════════════════════════════════════════════
# 三、富 schema 视图仍可用（双轨并存）
# ═══════════════════════════════════════════════════════════
def test_settings_tree_and_template_detail():
    pid = f"proj_{uuid.uuid4().hex[:6]}"
    tree = svc.get_message_settings(pid)
    assert isinstance(tree, list) and tree
    td = svc.get_template_detail(pid, "FUNCTIONAL_CASE_TASK", "CASE_CREATE", "IN_SITE")
    assert td.get("robotId") == "IN_SITE"


# ═══════════════════════════════════════════════════════════
# 四、Router 契约（阶段 B）
# ═══════════════════════════════════════════════════════════
def test_router_notification_count(auth_client):
    """未读数 Router 契约（阶段 B：经薄 Service→DDD 门面）。"""
    r = auth_client.get("/notification/count")
    assert r.status_code == 200
    data = r.json().get("data", {})
    assert "count" in data


def test_router_settings_tree(auth_client):
    """消息设置树 Router 契约（双轨并存视图仍可用）。"""
    pid = f"p_{uuid.uuid4().hex[:6]}"
    r = auth_client.get(f"/notice/message/task/get/{pid}")
    assert r.status_code == 200
    assert isinstance(r.json().get("data"), list)
