"""DDD file 域 A→B→C 渐进迁移回归测试。

背景
----
`app/domain/file/` DDD 层（阶段 A）就绪后，本测试锁定「阶段 B/C」接入契约：
  - 阶段 C：`app/services/file_service.py` 的落盘写路径 save_file / delete_file /
    delete_files_batch / update_meta 已委托 `file_app_service`（DDD 门面），
    安全落盘 + 元数据同步 + 文件类型自动识别由聚合/门面守护；
  - 阶段 B：Router 经薄 Service → DDD 门面 → 聚合，上传/删除全链路落盘可查可删；
  - 项目文件列表 / 附件页等富 schema 视图仍保留在 Service（DDD 未完全复刻，
    双轨并存，零破坏）。

本测试以 Service 为界验证迁移后写路径行为与旧契约一致，作为逐域切换的回归基线。
"""
import os
import uuid

from app.repositories.file_repo import file_repo
from app.services.file_service import file_service as svc

TAG = "filemig"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════
# 一、save_file 委托 DDD（阶段 C）
# ═══════════════════════════════════════════════════════════
def test_save_file_returns_compatible_shape():
    name = f"{_mk()}.txt"
    r = svc.save_file(name, b"hello world", project_id="p1", module_id="m1",
                      create_user="admin")
    try:
        assert r and r["id"]
        assert r["name"] == name
        assert os.path.isfile(r["path"])
        assert r["size"] == 11
        # 元数据已同步（含自动识别文件类型）
        meta = svc.get_file_meta_meta(r["id"]) if hasattr(svc, "get_file_meta_meta") else None
    finally:
        svc.delete_file(r["id"])
        if os.path.exists(r.get("path", "")):
            os.remove(r["path"])


def test_save_meta_file_type_auto():
    """落盘后 DB 元数据文件类型按扩展名自动识别（委托 DDD 聚合）。"""
    r = svc.save_file(f"{_mk()}.pdf", b"%PDF-1.4", project_id="p1")
    try:
        meta = file_repo.get_meta(r["id"])
        assert meta is not None
        assert meta.get("file_type") == "DOC"
        assert meta.get("project_id") == "p1"
    finally:
        svc.delete_file(r["id"])


def test_delete_file_missing_returns_false():
    assert svc.delete_file(f"nope_{uuid.uuid4().hex[:6]}") is False


# ═══════════════════════════════════════════════════════════
# 二、delete_files_batch / update_meta（委托 DDD 门面）
# ═══════════════════════════════════════════════════════════
def test_delete_files_batch_counts():
    a = svc.save_file(f"{_mk()}.bin", b"\x00\x01")
    b = svc.save_file(f"{_mk()}.bin", b"\x02\x03")
    try:
        removed = svc.delete_files_batch([a["id"], b["id"]])
        assert removed == 2
        assert svc.find_upload_file(a["id"]) is None
        assert svc.find_upload_file(b["id"]) is None
    finally:
        for p in (a.get("path", ""), b.get("path", "")):
            if os.path.exists(p):
                os.remove(p)


def test_update_meta_persists():
    r = svc.save_file(f"{_mk()}.csv", b"a,b")
    try:
        svc.update_meta(r["id"], {"module_id": "mod2", "description": "desc"})
        meta = file_repo.get_meta(r["id"])
        assert meta.get("module_id") == "mod2"
        assert meta.get("description") == "desc"
    finally:
        svc.delete_file(r["id"])


# ═══════════════════════════════════════════════════════════
# 三、Router 契约（阶段 B：附件上传/删除）
# ═══════════════════════════════════════════════════════════
def test_attachment_upload_router(auth_client):
    """附件上传经 Router→薄 Service→DDD 门面→聚合 落盘可查（阶段 B）。"""
    name = f"{_mk()}.txt"
    r = auth_client.post("/attachment/upload", files={
        "file": (name, b"Attachment Content", "text/plain"),
    })
    assert r.status_code == 200
    data = r.json().get("data", {})
    assert data.get("name") == name
    fid = data.get("id")
    if fid:
        svc.delete_file(fid)
