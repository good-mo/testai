"""缺陷管理全流程联调测试 - 验证前端所需字段完整性"""
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    c = TestClient(app)
    r = c.post("/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    session = r.json()["data"]
    c.headers.update({
        "X-AUTH-TOKEN": session["sessionId"],
        "CSRF-TOKEN": session["csrfToken"],
    })
    return c


def _data(r):
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    j = r.json()
    assert j.get("code") == 200, f"API error: {j}"
    return j["data"]


class TestFrontendFieldCompleteness:
    """前端页面所需后端字段完整性"""

    def test_bug_detail_has_attachments(self, client):
        """详情API必须返回 attachments 字段(空数组即可), edit.vue 解构该字段"""
        r = client.post("/bug/add", json={"title": f"attachments-test-{uuid.uuid4().hex[:6]}"})
        bug_id = _data(r)["id"]
        try:
            r = client.get(f"/bug/get/{bug_id}")
            detail = _data(r)
            assert "attachments" in detail, "Bug detail must include 'attachments' field for edit.vue handleFile()"
            assert isinstance(detail["attachments"], list), "attachments must be a list"
        finally:
            client.post("/bug/delete", json={"id": bug_id})

    def test_severity_trivial_update(self, client):
        """创建 severity=trivial 的缺陷后, 编辑更新不应报 400"""
        title = f"trivial-sev-{uuid.uuid4().hex[:6]}"
        r = client.post("/bug/add", json={
            "title": title,
            "severity": "trivial",
            "customFields": [{"id": "severity", "value": "trivial"}],
        })
        assert r.status_code == 200
        bug_id = _data(r)["id"]
        try:
            # Update the bug, should succeed
            r = client.post("/bug/update", json={
                "id": bug_id,
                "title": title + "-updated",
                "customFields": [{"id": "severity", "value": "trivial"}],
            })
            assert r.status_code == 200, f"Update with trivial severity failed: {r.text}"
            data = _data(r)
            assert data["status"] == "open"  # Status should be preserved
        finally:
            client.post("/bug/delete", json={"id": bug_id})

    def test_severity_blocker_roundtrip(self, client):
        """blocker 严重程度数据不应在前端被转成 major"""
        title = f"blocker-sev-{uuid.uuid4().hex[:6]}"
        r = client.post("/bug/add", json={
            "title": title,
            "severity": "blocker",
        })
        assert r.status_code == 200
        bug_id = _data(r)["id"]
        try:
            # Get bug detail - severity should be 'blocker' not 'major'
            r = client.get(f"/bug/get/{bug_id}")
            detail = _data(r)
            assert detail["severity"] == "blocker", f"Blocking severity corrupted to: {detail.get('severity')}"
            
            # customFields severity should also be correct
            sev_cf = [cf for cf in detail.get("customFields", []) if cf.get("id") == "severity"]
            assert len(sev_cf) > 0, "Missing severity in customFields"
            assert sev_cf[0]["value"] == "blocker", f"Severity customField wrong: {sev_cf[0]}" 
        finally:
            client.post("/bug/delete", json={"id": bug_id})

    def test_severity_options_include_all_backend_values(self, client):
        """模板严重程度选项必须包含后端 VALID_SEVERITIES 中所有值"""
        r = client.get("/bug/header/custom-field/proj1")
        fields = _data(r)
        sev_field = next((f for f in fields if f.get("fieldId") == "severity"), None)
        assert sev_field, "Missing severity field"
        opts = sev_field.get("options") or []
        opt_values = [o.get("value") for o in opts]
        # All backend valid severities must be selectable in frontend
        for sev in ["blocker", "critical", "major", "minor", "trivial"]:
            assert sev in opt_values, f"Severity '{sev}' not in template options: {opt_values}"

    def test_template_severity_options_match_backend(self, client):
        """模板详情中的严重程度选项也要包含所有后端有效值"""
        r = client.post("/bug/template/detail", json={
            "projectId": "proj1",
            "id": "default-bug-template",
        })
        tmpl = _data(r)
        sev_fields = [f for f in tmpl.get("customFields", []) if f.get("fieldId") == "severity"]
        assert len(sev_fields) > 0
        opts = sev_fields[0].get("options") or []
        opt_values = [o.get("value") for o in opts]
        for sev in ["blocker", "critical", "major", "minor", "trivial"]:
            assert sev in opt_values, f"Severity '{sev}' not in template options: {opt_values}"


class TestBugCRUDEdgeCases:
    """缺陷CRUD边界情况"""

    def test_create_update_with_all_severities(self, client):
        """所有严重程度值都能完成创建+更新"""
        for sev in ["critical", "major", "minor", "trivial"]:
            title = f"sev-{sev}-{uuid.uuid4().hex[:6]}"
            r = client.post("/bug/add", json={"title": title, "severity": sev})
            assert r.status_code == 200, f"Create with {sev} failed: {r.text}"
            bug_id = _data(r)["id"]
            
            try:
                r = client.post("/bug/update", json={
                    "id": bug_id,
                    "title": title + "-upd",
                    "severity": sev,
                })
                assert r.status_code == 200, f"Update with {sev} failed: {r.text}"
            finally:
                client.post("/bug/delete", json={"id": bug_id})
    
    def test_update_severity_from_trivial_to_major(self, client):
        """从 trivial 更新为 major 应成功"""
        r = client.post("/bug/add", json={"title": f"sev-change-{uuid.uuid4().hex[:6]}", "severity": "trivial"})
        bug_id = _data(r)["id"]
        try:
            r = client.post("/bug/update", json={
                "id": bug_id,
                "severity": "major",
                "customFields": [{"id": "severity", "value": "major"}],
            })
            assert r.status_code == 200, f"Severity change from trivial to major failed: {r.text}"
            data = _data(r)
            assert data["severity"] == "major"
        finally:
            client.post("/bug/delete", json={"id": bug_id})

    def test_bug_list_after_delete_excluded(self, client):
        """删除的缺陷不应出现在正常列表"""
        r = client.post("/bug/add", json={"title": f"list-exclude-{uuid.uuid4().hex[:6]}"})
        bug_id = _data(r)["id"]
        
        # Delete the bug
        client.post("/bug/delete", json={"id": bug_id})
        
        # Normal list should NOT include it
        r = client.post("/bug/page", json={"pageSize": 100, "current": 1})
        active_ids = [i["id"] for i in _data(r)["list"]]
        assert bug_id not in active_ids, f"Deleted bug {bug_id} still in active list"
        
        # Trash list SHOULD include it
        r = client.post("/bug/trash/page", json={"pageSize": 100, "current": 1})
        trash_ids = [i["id"] for i in _data(r)["list"]]
        assert bug_id in trash_ids, f"Bug {bug_id} not in trash list"
        
        # Cleanup
        client.get(f"/bug/trash/delete/{bug_id}")


if __name__ == "__main__":
    print("Running...")


class TestSeverityMapping:
    """P0-P3 严重度映射与非法值兜底。"""

    def test_create_with_P1_maps_to_critical(self, client):
        """前端传 P1 应映射为 critical，不存脏数据。"""
        from app.repositories.defect_repo import DefectRepo
        title = f"sev-P1-{uuid.uuid4().hex[:6]}"
        r = client.post("/bug/add", json={"title": title, "severity": "P1"})
        assert r.status_code == 200, r.text
        bug_id = _data(r)["id"]
        try:
            assert _data(r)["severity"] == "critical"
            defect = DefectRepo.get(bug_id)
            assert defect["severity"] == "critical", \
                f"DB severity should be critical, got {defect['severity']}"
        finally:
            DefectRepo.purge(bug_id)

    def test_create_with_P0_maps_to_blocker(self, client):
        """前端传 P0 应映射为 blocker。"""
        from app.repositories.defect_repo import DefectRepo
        title = f"sev-P0-{uuid.uuid4().hex[:6]}"
        r = client.post("/bug/add", json={"title": title, "severity": "P0"})
        assert r.status_code == 200, r.text
        bug_id = _data(r)["id"]
        try:
            assert _data(r)["severity"] == "blocker"
            defect = DefectRepo.get(bug_id)
            assert defect["severity"] == "blocker"
        finally:
            DefectRepo.purge(bug_id)

    def test_create_with_invalid_severity_falls_to_major(self, client):
        """非法严重度不静默写脏，落到默认 major。"""
        from app.repositories.defect_repo import DefectRepo
        title = f"sev-bad-{uuid.uuid4().hex[:6]}"
        r = client.post("/bug/add", json={"title": title, "severity": "not-a-real-severity"})
        assert r.status_code == 200, r.text
        bug_id = _data(r)["id"]
        try:
            assert _data(r)["severity"] == "major"
            defect = DefectRepo.get(bug_id)
            assert defect["severity"] == "major", \
                f"DB severity should be major, got {defect['severity']}"
        finally:
            DefectRepo.purge(bug_id)

    def test_update_with_P3_maps_to_minor(self, client):
        """更新时前端传 P3 应映射为 minor。"""
        from app.repositories.defect_repo import DefectRepo
        title = f"sev-upd-P3-{uuid.uuid4().hex[:6]}"
        r = client.post("/bug/add", json={"title": title, "severity": "minor"})
        bug_id = _data(r)["id"]
        try:
            r = client.post("/bug/update", json={"id": bug_id, "severity": "P3"})
            assert r.status_code == 200, r.text
            assert _data(r)["severity"] == "minor"
            defect = DefectRepo.get(bug_id)
            assert defect["severity"] == "minor"
        finally:
            DefectRepo.purge(bug_id)

    def test_repo_create_invalid_severity_falls_to_major(self):
        """DefectRepo.create 非法 severity 落到 major。"""
        from app.repositories.defect_repo import DefectRepo
        d = DefectRepo.create({"title": f"repo-bad-{uuid.uuid4().hex[:6]}", "severity": "P9"})
        try:
            assert d["severity"] == "major"
        finally:
            DefectRepo.purge(d["id"])
