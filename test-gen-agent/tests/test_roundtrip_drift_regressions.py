"""回归测试：数据完整性 / 契约往返一致性修复。

覆盖 ISSUE #708 的四类缺陷：
  ① to_dict/from_dict 时间单位往返漂移（毫秒当秒回灌放大 1000x；DebugItem 未回灌重置）
  ② GenerationStep.detail 未进 to_dict，落库后恒为 None
  ③ ProjectAppConfig 合法 falsy 值被 or 短路吞掉（False/0/"" 读成 None）
  ④ identity 域守卫接线：组织不能移除唯一 owner（read-only 预检 + DDD 权威裁决）
"""
import uuid

import pytest

from app.domain.ai_model.domain.entities.ai_model import AiModelSource
from app.domain.debug.domain.entities.debug_item import DebugItem
from app.domain.generation.domain.entities.generation_job import GenerationJob
from app.domain.generation.domain.entities.generation_step import GenerationStep
from app.domain.project_app_config.domain.entities.project_config import ProjectAppConfig
from app.domain.project_version.domain.entities.project_version import ProjectVersion
from app.domain.resource_pool.domain.entities.resource_pool import ResourcePool
from app.domain.template.domain.entities.template import Template


def _close(a, b):
    # to_dict 用 int(ms) 截断，容差放宽到 2ms
    return abs(a - b) < 0.002


# ═══════════════════════════════════════════════════════════
# ① 时间单位往返漂移
# ═══════════════════════════════════════════════════════════
class TestTimeRoundTripDrift:
    def test_resource_pool_roundtrip_no_drift(self):
        p = ResourcePool(pool_id="p1", created_at=1000.0, updated_at=2000.0)
        p2 = ResourcePool.from_dict(p.to_dict())
        assert _close(p2._created_at, 1000.0) and _close(p2._updated_at, 2000.0)

    def test_resource_pool_snake_seconds_still_ok(self):
        # DB 原始行 snake_case 秒值不换算
        p = ResourcePool.from_dict(
            {"id": "p1", "name": "x", "created_at": 1000.0, "updated_at": 2000.0})
        assert _close(p._created_at, 1000.0)

    def test_template_roundtrip_no_drift(self):
        t = Template(template_id="t1", name="x", create_time=3000.0, update_time=4000.0)
        t2 = Template.from_dict(t.to_dict())
        assert _close(t2._create_time, 3000.0) and _close(t2._update_time, 4000.0)

    def test_project_version_roundtrip_no_drift(self):
        v = ProjectVersion(
            version_id="v1", name="x",
            create_time=5000.0, update_time=6000.0, publish_time=5500.0)
        v2 = ProjectVersion.from_dict(v.to_dict())
        assert _close(v2._create_time, 5000.0)
        assert _close(v2._publish_time, 5500.0)

    def test_ai_model_roundtrip_no_drift(self):
        m = AiModelSource(model_id="m1", name="x", create_time=7000.0, update_time=8000.0)
        m2 = AiModelSource.from_dict(m.to_dict())
        assert _close(m2._create_time, 7000.0) and _close(m2._update_time, 8000.0)

    def test_ai_model_db_camel_ms_seconds(self):
        # ai_model_repo 经 _row_to_dict 输出 camelCase 毫秒，应换算回秒
        m = AiModelSource.from_dict(
            {"id": "m1", "name": "x", "createTime": 7000000, "updateTime": 8000000})
        assert _close(m._create_time, 7000.0) and _close(m._update_time, 8000.0)

    def test_debug_item_roundtrip_preserves_time(self):
        d = DebugItem(debug_id="d1")
        d2 = DebugItem.from_dict(d.to_dict())
        # 不再被重置为当前时间（未回灌 bug）
        assert _close(d2._create_time, d._create_time)
        assert _close(d2._update_time, d._update_time)
        # 显式回灌的历史时间也应保留
        d3 = DebugItem.from_dict(
            {"id": "d2", "name": "x", "createTime": 1000000, "updateTime": 2000000})
        assert _close(d3._create_time, 1000.0) and _close(d3._update_time, 2000.0)


# ═══════════════════════════════════════════════════════════
# ② GenerationStep.detail 落库往返
# ═══════════════════════════════════════════════════════════
class TestGenerationStepDetail:
    def test_detail_roundtrip_through_job(self):
        j = GenerationJob(
            job_id=uuid.uuid4().hex[:12], file_path="x.py", source_code="def x(): pass")
        j.record_step(node_name="scan_code", detail={"scanned": 42, "diag": "ok"})
        snap = j.to_dict()
        j2 = GenerationJob.from_dict(snap)
        step = next(s for s in j2.steps if s.node_name == "scan_code")
        assert step.detail == {"scanned": 42, "diag": "ok"}

    def test_step_to_dict_includes_detail(self):
        s = GenerationStep(node_name="n", seq=1)
        s.mark_done(detail={"files": 3})
        assert s.to_dict().get("detail") == {"files": 3}


# ═══════════════════════════════════════════════════════════
# ③ ProjectAppConfig falsy 值不被吞
# ═══════════════════════════════════════════════════════════
class TestProjectAppConfigFalsy:
    @pytest.mark.parametrize("val", [False, 0, "", True, "x", 5, None])
    def test_roundtrip_preserves_falsy(self, val):
        c = ProjectAppConfig(
            project_id="p", module="m", config_key="k", config_value=val)
        c2 = ProjectAppConfig.from_dict(c.to_dict())
        assert c2.config_value == val

    def test_camel_configValue_false_not_swallowed(self):
        c = ProjectAppConfig.from_dict(
            {"project_id": "p", "module": "m", "config_key": "k", "configValue": False})
        assert c.config_value is False
        c2 = ProjectAppConfig.from_dict(
            {"project_id": "p", "module": "m", "config_key": "k", "configValue": 0})
        assert c2.config_value == 0


# ═══════════════════════════════════════════════════════════
# ④ identity 域守卫接线
# ═══════════════════════════════════════════════════════════
def _del_org(org_id):
    try:
        from app.core.database import Database
        conn = Database.get_conn("projects.db")
        conn.execute("DELETE FROM organization_members WHERE organization_id=?",
                     (org_id,))
        conn.execute("DELETE FROM organizations WHERE id=?", (org_id,))
        conn.commit()
    except Exception:
        pass


def _del_user(username):
    try:
        from app.core.database import Database
        conn = Database.get_conn("auth.db")
        conn.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
    except Exception:
        pass


class TestIdentityGuardWiring:
    def test_org_cannot_remove_sole_owner(self):
        from app.services.auth_service import auth_service
        from app.services.organization_service import organization_service
        oname = "rg_" + uuid.uuid4().hex[:6]
        org = organization_service.create(oname, "d")
        assert org and org.get("id")
        oid = org["id"]
        u1 = auth_service.create_user("ow_" + uuid.uuid4().hex[:6], "x")
        u2 = auth_service.create_user("mb_" + uuid.uuid4().hex[:6], "x")
        try:
            organization_service.add_member(oid, u1["id"], role="owner")
            organization_service.add_member(oid, u2["id"], role="member")
            # 唯一 owner 不可移除
            assert organization_service.remove_member(oid, u1["id"]) is False
            # 普通成员可移除
            assert organization_service.remove_member(oid, u2["id"]) is True
            # owner 仍保留在组织
            left = [m for m in organization_service.list_members(oid, limit=100)
                    if m["user_id"] == u1["id"]]
            assert left
        finally:
            _del_org(oid)
            _del_user(u1["username"])
            _del_user(u2["username"])
