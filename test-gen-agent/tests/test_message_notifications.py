# -*- coding: utf-8 -*-
"""消息通知 / 消息管理 实现验证测试。

覆盖：
- 项目消息机器人 CRUD / 启停（内置站内信/邮件 + 自建）
- 消息设置配置树 / 保存 / 模板详情 / 字段 / 接收人
- 站内消息中心：通知写入 / 分页 / 已读 / 未读计数
"""
import uuid

import pytest

from app.repositories.message_repo import MessageRepo, message_repo

pytestmark = pytest.mark.usefixtures("auth_client")


@pytest.fixture
def project_id() -> str:
    """任一真实项目 ID。"""
    from app.services.project_service import project_service
    projects = project_service.list(limit=1)
    if projects:
        return projects[0]["id"]
    proj = project_service.create({"name": "message-test-project"})
    return proj["id"]


def _admin_user_id() -> str:
    """返回 admin 用户 id（用于通知接收人）。"""
    from app.auth.store import auth_store
    return auth_store.get_user_by_username("admin")["id"]


def _robot_id(auth_client, project_id: str) -> str:
    r = auth_client.post("/project/robot/add", json={
        "projectId": project_id,
        "name": f"钉钉-{uuid.uuid4().hex[:6]}",
        "platform": "DING_TALK",
        "type": "CUSTOM",
        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=abc",
        "enable": True,
    })
    assert r.status_code == 200 and r.json()["code"] == 200, r.text
    return r.json()["data"]["id"]


class TestProjectRobots:
    """项目消息机器人。"""

    def test_robot_list_contains_builtin(self, auth_client, project_id):
        r = auth_client.get(f"/project/robot/list/{project_id}")
        assert r.status_code == 200
        data = r.json()["data"]
        platforms = {x["platform"] for x in data}
        assert {"IN_SITE", "MAIL"} <= platforms, "应包含系统内置站内信/邮件机器人"

    def test_robot_crud(self, auth_client, project_id):
        rid = _robot_id(auth_client, project_id)

        # 查询详情
        r = auth_client.get(f"/project/robot/get?id={rid}")
        assert r.json()["data"]["id"] == rid

        # 更新（禁用）
        r = auth_client.post("/project/robot/update", json={
            "id": rid, "name": "钉钉改名", "enable": False,
        })
        assert r.json()["code"] == 200
        r = auth_client.get(f"/project/robot/list/{project_id}")
        robot = next(x for x in r.json()["data"] if x["id"] == rid)
        assert robot["enable"] is False

        # 启停切换（GET 带路径）
        r = auth_client.get(f"/project/robot/enable/{rid}")
        assert r.json()["code"] == 200
        r = auth_client.get(f"/project/robot/list/{project_id}")
        robot = next(x for x in r.json()["data"] if x["id"] == rid)
        assert robot["enable"] is True

        # 删除
        r = auth_client.get(f"/project/robot/delete/{rid}")
        assert r.json()["code"] == 200
        r = auth_client.get(f"/project/robot/list/{project_id}")
        assert all(x["id"] != rid for x in r.json()["data"])

    def test_robot_enable_toggle_post(self, auth_client, project_id):
        rid = _robot_id(auth_client, project_id)
        r = auth_client.post("/project/robot/enable", json={"id": rid})
        assert r.json()["code"] == 200
        r = auth_client.get(f"/project/robot/list/{project_id}")
        robot = next(x for x in r.json()["data"] if x["id"] == rid)
        assert robot["enable"] is False


class TestMessageSettings:
    """消息设置（消息管理页）。"""

    def test_get_settings_tree(self, auth_client, project_id):
        r = auth_client.get(f"/notice/message/task/get/{project_id}")
        assert r.status_code == 200 and r.json()["code"] == 200
        modules = r.json()["data"]
        assert isinstance(modules, list) and len(modules) >= 3
        # 每行事件含机器人列配置
        found = False
        for m in modules:
            for tt in m.get("messageTaskTypeDTOList", []):
                for ev in tt.get("messageTaskDetailDTOList", []):
                    assert "projectRobotConfigMap" in ev
                    assert "receivers" in ev
                    found = True
        assert found

    def test_template_fields_and_detail(self, auth_client, project_id):
        rid = _robot_id(auth_client, project_id)
        r = auth_client.get(f"/notice/template/get/fields/{project_id}?taskType=BUG_TASK")
        fields = r.json()["data"]
        assert isinstance(fields.get("fieldList"), list) and fields["fieldList"]

        r = auth_client.get(
            f"/notice/message/template/detail/{project_id}?taskType=BUG_TASK&event=CREATE&robotId={rid}"
        )
        assert r.json()["code"] == 200
        detail = r.json()["data"]
        assert detail["robotId"] == rid
        assert detail["event"] == "CREATE"
        assert detail["defaultTemplate"]
        assert detail["defaultSubject"]

    def test_save_config_roundtrip(self, auth_client, project_id):
        rid = _robot_id(auth_client, project_id)
        r = auth_client.post("/notice/message/task/save", json={
            "projectId": project_id,
            "taskType": "BUG_TASK",
            "event": "CREATE",
            "robotId": rid,
            "receiverIds": ["OPERATOR", "admin"],
            "subject": "标题-自定义",
            "template": "模板-自定义",
            "useDefaultSubject": False,
            "useDefaultTemplate": False,
            "enable": True,
        })
        assert r.status_code == 200 and r.json()["code"] == 200, r.text

        # 配置树中该事件对应机器人列应展示已保存值
        r = auth_client.get(f"/notice/message/task/get/{project_id}")
        found = None
        for m in r.json()["data"]:
            for tt in m.get("messageTaskTypeDTOList", []):
                for ev in tt.get("messageTaskDetailDTOList", []):
                    cfg = ev["projectRobotConfigMap"].get(rid)
                    if cfg and ev["event"] == "CREATE":
                        found = cfg
        assert found and found["enable"] is True
        assert found["subject"] == "标题-自定义"
        assert found["template"] == "模板-自定义"

        # 模板详情带回保存值
        r = auth_client.get(
            f"/notice/message/template/detail/{project_id}?taskType=BUG_TASK&event=CREATE&robotId={rid}"
        )
        detail = r.json()["data"]
        assert detail["subject"] == "标题-自定义"
        assert detail["template"] == "模板-自定义"
        assert detail["receiverIds"] == ["OPERATOR", "admin"]

    def test_receiver_options(self, auth_client, project_id):
        r = auth_client.get(f"/notice/message/task/get/user/{project_id}?keyword=admin")
        assert r.status_code == 200
        data = r.json()["data"]
        ids = {x["id"] for x in data}
        assert "OPERATOR" in ids and "CREATE_USER" in ids


    def test_save_config_update_roundtrip(self, auth_client, project_id):
        """验证同一(project,taskType,event,robotId)重复保存时 UPDATE 路径正常。"""
        rid = _robot_id(auth_client, project_id)
        # 第一次保存（INSERT）
        r = auth_client.post("/notice/message/task/save", json={
            "projectId": project_id,
            "taskType": "BUG_TASK",
            "event": "CREATE",
            "robotId": rid,
            "receiverIds": ["OPERATOR"],
            "subject": "第一次",
            "template": "tpl1",
            "useDefaultSubject": False,
            "useDefaultTemplate": False,
            "enable": True,
        })
        assert r.status_code == 200 and r.json()["code"] == 200, r.text

        # 第二次保存（UPDATE，修复前会因绑定数量不匹配报错）
        r = auth_client.post("/notice/message/task/save", json={
            "projectId": project_id,
            "taskType": "BUG_TASK",
            "event": "CREATE",
            "robotId": rid,
            "receiverIds": ["OPERATOR", "CREATE_USER"],
            "subject": "第二次",
            "template": "tpl2",
            "useDefaultSubject": False,
            "useDefaultTemplate": False,
            "enable": False,
        })
        assert r.status_code == 200 and r.json()["code"] == 200, r.text

        # 验证更新后的值
        r = auth_client.get(
            f"/notice/message/template/detail/{project_id}?taskType=BUG_TASK&event=CREATE&robotId={rid}"
        )
        detail = r.json()["data"]
        assert detail["subject"] == "第二次"
        assert detail["template"] == "tpl2"
        assert detail["receiverIds"] == ["OPERATOR", "CREATE_USER"]
        assert detail["enable"] is False

    def test_get_settings_reflects_saved_receivers(self, auth_client, project_id):
        """验证消息设置树中事件级接收人能正确展示已保存的接收人。"""
        rid = _robot_id(auth_client, project_id)
        # 保存配置时指定接收人
        r = auth_client.post("/notice/message/task/save", json={
            "projectId": project_id,
            "taskType": "BUG_TASK",
            "event": "UPDATE",
            "robotId": rid,
            "receiverIds": ["OPERATOR", "admin"],
            "subject": "",
            "template": "",
            "useDefaultSubject": True,
            "useDefaultTemplate": True,
            "enable": True,
        })
        assert r.status_code == 200 and r.json()["code"] == 200, r.text

        # 获取配置树，应能看到保存的接收人
        r = auth_client.get(f"/notice/message/task/get/{project_id}")
        assert r.status_code == 200 and r.json()["code"] == 200
        found = False
        for m in r.json()["data"]:
            for tt in m.get("messageTaskTypeDTOList", []):
                if tt.get("taskType") != "BUG_TASK":
                    continue
                for ev in tt.get("messageTaskDetailDTOList", []):
                    if ev.get("event") != "UPDATE":
                        continue
                    recv_ids = [x.get("id") for x in ev.get("receivers", [])]
                    assert "OPERATOR" in recv_ids, f"expected OPERATOR, got {recv_ids}"
                    assert "admin" in recv_ids, f"expected admin, got {recv_ids}"
                    found = True
        assert found, "BUG_TASK/UPDATE event not found in settings tree"


class TestNotificationCenter:
    """站内消息中心。"""

    def _seed(self, auth_client, project_id, receiver: str) -> str:
        # 使用真实 admin 用户 id 作为接收人（与 _admin_user_id 一致）
        return _admin_user_id()

    def test_message_center_full_flow(self, auth_client, project_id):
        # 当前登录用户 id
        r = auth_client.get("/notification/un-read")
        assert r.status_code == 200
        # 写入一条通知（receiver 使用 user id）
        from app.repositories.message_repo import message_repo
        receiver = _admin_user_id()
        nid = message_repo.create_notification({
            "type": "message",
            "title": "测试通知",
            "content": "内容",
            "resource_type": "BUG",
            "resource_name": "BUG-001",
            "operation": "UPDATE",
            "receiver": receiver,
            "operator": "admin",
            "project_id": project_id,
        })

        # 通知分页（POST 兼容前端）
        r = auth_client.post("/notification/list/all/page", json={
            "current": 1, "pageSize": 10, "receiver": receiver,
        })
        assert r.json()["code"] == 200
        assert r.json()["data"]["total"] >= 1

        # navbar 消息列表
        r = auth_client.post("/api/message/list")
        assert r.status_code == 200 and r.json()["code"] == 200
        assert isinstance(r.json()["data"], list)

        # 未读数（GET 项目级 / 无项目）
        r = auth_client.get(f"/notification/un-read/{project_id}")
        assert r.status_code == 200

        # 单条已读
        r = auth_client.get(f"/notification/read/{nid}")
        assert r.json()["code"] == 200

        # 已读后未读数不增加（至少不报错）
        r = auth_client.get("/notification/read/all")
        assert r.json()["code"] == 200

    def test_message_count(self, auth_client):
        r = auth_client.get("/notification/count")
        assert r.status_code == 200 and r.json()["code"] == 200
        assert isinstance(r.json()["data"]["count"], int)

