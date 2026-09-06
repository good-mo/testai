"""DDD 支撑域单测：template / script / environment / message / file。

覆盖纯领域逻辑与应用服务全链路（无 DB 存储的域注入替身仓储）。
"""

import pytest

from app.domain.common.exceptions import DomainValidationError

# ═══════════════════════════════════════════════════════════
# 一、Template 模板域
# ═══════════════════════════════════════════════════════════
from app.domain.template.application.dto import (
    ListTemplatesCommand,
)
from app.domain.template.application.template_app_service import TemplateAppService
from app.domain.template.domain.entities.template import Template
from app.domain.template.domain.value_objects.template_scene import TemplateScene


class TestTemplateDomain:
    def test_scene_validation(self):
        assert str(TemplateScene("functional")) == "FUNCTIONAL"
        with pytest.raises(DomainValidationError):
            TemplateScene("INVALID")

    def test_template_requires_name(self):
        with pytest.raises(DomainValidationError):
            Template(template_id="t1", name="")

    def test_template_rename(self):
        t = Template(template_id="t1", name="模板A")
        t.rename("模板B")
        assert t.name == "模板B"
        assert "TemplateUpdated" in [type(e).__name__ for e in t.pull_domain_events()]

    def test_template_from_dict_roundtrip(self):
        t = Template(template_id="t1", name="模板A", scope_type="PROJECT",
                      scope_id="p1", custom_fields=[{"id": "f1", "label": "字段1"}])
        d = t.to_dict()
        t2 = Template.from_dict(d)
        assert t2.name == t.name
        assert t2.custom_fields == t.custom_fields
        assert t2.scope_type.value == "PROJECT"

    def test_app_service_list_seed_default(self):
        """列表空时自动播种默认模板。"""
        class EmptyRepo:
            def list_templates(self, scope_type, scope_id, scene):
                return []
            def seed_default(self, scope_type, scope_id, scene, name):
                return Template(template_id="seed1", name=name, scene=scene,
                               scope_type=scope_type, scope_id=scope_id,
                               internal=True, enable_default=True)
            def get_template(self, template_id):
                return None
            def count_in_scope(self, scope_type, scope_id, scene):
                return 1
            def upsert_template(self, t):
                return t
            def delete_template(self, template_id):
                return True
            def set_default(self, *args):
                return True

        svc = TemplateAppService(repo=EmptyRepo())
        result = svc.list_templates(ListTemplatesCommand(scope_type="PROJECT", scope_id="p1", scene="FUNCTIONAL"))
        assert len(result) == 1
        assert result[0]["name"] == "功能用例默认模板"


# ═══════════════════════════════════════════════════════════
# 二、Script 脚本域
# ═══════════════════════════════════════════════════════════
from app.domain.script.domain.entities.script import Script
from app.domain.script.domain.services.script_policy import calc_health_score, determine_status
from app.domain.script.domain.value_objects.script_status import ScriptStatus


class TestScriptDomain:
    def test_status_validation(self):
        assert str(ScriptStatus("healthy")) == "healthy"
        with pytest.raises(DomainValidationError):
            ScriptStatus("invalid")

    def test_health_score_calc(self):
        score = calc_health_score(10, 9, 1, 100.0, True)
        assert 0 <= score <= 100
        assert score > 85  # 高成功率应健康

    def test_status_determination(self):
        assert determine_status(90) == "healthy"
        assert determine_status(70) == "unstable"
        assert determine_status(50) == "degraded"

    def test_script_entity_requires_name(self):
        with pytest.raises(DomainValidationError):
            Script(script_id="s1", name="")

    def test_script_execution_updates_health(self):
        s = Script(script_id="s1", name="test_ui.py")
        s.record_execution(success=True, duration=1.5)
        assert s.total_runs == 1
        assert s.success_runs == 1
        assert s.health_score > 80
        assert "ScriptExecutionRecorded" in [type(e).__name__ for e in s.pull_domain_events()]

    def test_script_repeated_failure_degrades(self):
        s = Script(script_id="s2", name="test_broken.py")
        for _ in range(5):
            s.record_execution(success=False, duration=1.0)
        assert s.fail_runs == 5
        assert s.health_score < 60
        assert s.status.value == "degraded"


# ═══════════════════════════════════════════════════════════
# 三、Environment 环境域
# ═══════════════════════════════════════════════════════════
from app.domain.environment.domain.entities.environment import Environment
from app.domain.environment.domain.value_objects.env_status import EnvStatus


class TestEnvironmentDomain:
    def test_status_validation(self):
        assert str(EnvStatus("online")) == "online"
        assert str(EnvStatus("OFFLINE")) == "offline"
        with pytest.raises(DomainValidationError):
            EnvStatus("bogus")

    def test_env_requires_name(self):
        with pytest.raises(DomainValidationError):
            Environment(env_id="e1", name="")

    def test_env_status_transitions(self):
        env = Environment(env_id="e1", name="测试环境")
        env.change_status("launching")
        assert env.status.value == "launching"
        env.change_status("online")
        assert env.status.value == "online"
        env.change_status("offline")
        assert env.status.value == "offline"
        env.change_status("online")
        assert env.status.value == "online"
        # 从 online 不能直接到 launching
        with pytest.raises(DomainValidationError):
            env.change_status("launching")

    def test_env_meta_update(self):
        env = Environment(env_id="e1", name="测试环境")
        env.update_meta({"endpoint": "http://localhost:8080", "tags": ["prod", "ci"]})
        assert env.endpoint == "http://localhost:8080"
        assert "prod" in env.tags

    def test_env_events_on_created(self):
        env = Environment(env_id="e1", name="新环境", _created=True)
        events = env.pull_domain_events()
        assert "EnvironmentCreated" in [type(e).__name__ for e in events]


# ═══════════════════════════════════════════════════════════
# 四、Message 消息域
# ═══════════════════════════════════════════════════════════
from app.domain.message.domain.entities.notification import Notification
from app.domain.message.domain.entities.robot import Robot
from app.domain.message.domain.value_objects.notification_status import NotificationStatus


class TestMessageDomain:
    def test_notification_status(self):
        assert str(NotificationStatus("UNREAD")) == "UNREAD"
        assert str(NotificationStatus("read")) == "READ"
        with pytest.raises(DomainValidationError):
            NotificationStatus("invalid")

    def test_notification_mark_read(self):
        n = Notification(notification_id="n1", title="测试", receiver="user1")
        assert not n.is_read
        n.mark_read()
        assert n.is_read
        assert "NotificationRead" in [type(e).__name__ for e in n.pull_domain_events()]

    def test_notification_mark_read_idempotent(self):
        n = Notification(notification_id="n2", title="测试", receiver="user1")
        n.mark_read()
        n.mark_read()  # 幂等
        assert n.is_read
        assert len(n.pull_domain_events()) == 1

    def test_robot_validation(self):
        with pytest.raises(DomainValidationError):
            Robot(robot_id="r1", name="")

    def test_robot_builtin_protection(self):
        r = Robot(robot_id="IN_SITE", name="站内信", platform="IN_SITE", _created=True)
        assert r.is_builtin
        assert "RobotCreated" in [type(e).__name__ for e in r.pull_domain_events()]

    def test_robot_toggle_enable(self):
        r = Robot(robot_id="r2", name="机器人", enable=True)
        r.set_enable(False)
        assert not r.enable
        assert "RobotEnabledChanged" in [type(e).__name__ for e in r.pull_domain_events()]


# ═══════════════════════════════════════════════════════════
# 五、File 文件域
# ═══════════════════════════════════════════════════════════
from app.domain.file.domain.entities.file_item import FileItem
from app.domain.file.domain.value_objects.file_type import FileName, FileType


class TestFileDomain:
    def test_file_type_validation(self):
        assert str(FileType("IMAGE")) == "IMAGE"
        assert str(FileType("image")) == "IMAGE"
        with pytest.raises(DomainValidationError):
            FileType("UNKNOWN")

    def test_filename_sanitization(self):
        f = FileName("../../etc/passwd")
        assert "/" not in f.value
        assert ".." not in f.value
        assert f.value != ""

    def test_file_requires_id(self):
        with pytest.raises(DomainValidationError):
            FileItem(file_id="", name="test.png")

    def test_file_guess_type(self):
        assert FileItem._guess_type("photo.png") == "IMAGE"
        assert FileItem._guess_type("doc.pdf") == "DOC"
        assert FileItem._guess_type("data.json") == "CONFIG"
        assert FileItem._guess_type("app.jar") == "JAR"

    def test_file_move_module(self):
        f = FileItem(file_id="f1", name="test.py", module_id="root")
        f.move_module("module2")
        assert f.module_id == "module2"
        assert "FileMetaUpdated" in [type(e).__name__ for e in f.pull_domain_events()]

    def test_file_roundtrip(self):
        f = FileItem(file_id="f1", name="test.py", project_id="p1",
                      create_user="admin", size=1024)
        d = f.to_dict()
        f2 = FileItem.from_dict(d)
        assert f2.id.value == "f1"
        assert f2.name == "test.py"
        assert f2.project_id == "p1"
        assert f2.size == 1024
