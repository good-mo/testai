"""项目域「自定义函数/自定义字段」旁路方法 DDD 收敛迁移回归测试。

背景
----
`project_service` 的核心生命周期已收敛为 DDD 薄门面；本轮把其**自定义函数
（custom_funcs）** 与**自定义字段（project_custom_fields）** 这两组旁路方法面
也收敛为经 `ProjectAppService` 委托 DDD（应用门面 → ProjectRepoAdapter →
既有 ProjectRepo），Service 层的「前端格式转换」作为 Web 契约桥保留在其上，
对外 schema 与迁移前零变化、可回滚。

覆盖目标：
  1. project_service 自定义函数方法确实经 `project_app_service` 委托 DDD；
  2. 自定义函数 CRUD / 状态 / 列表往返契约不变（前端格式字段齐全）；
  3. 自定义字段 list / get / upsert / delete 往返契约不变（前端格式字段齐全）；
  4. 清理后不污染其他用例。
"""
import uuid

import pytest

from app.domain.project.application.dto import (
    CreateCustomFuncCommand,
    CustomFieldListQuery,
    CustomFuncListQuery,
    UpdateCustomFuncCommand,
    UpdateCustomFuncStatusCommand,
    UpsertCustomFieldCommand,
)
from app.domain.project.application.project_app_service import ProjectAppService

TAG = "dddprjmig2"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _cleanup_func(func_id: str) -> None:
    from app.repositories.project_repo import ProjectRepo
    try:
        ProjectRepo.delete_custom_func(func_id)
    except Exception:
        pass


def _cleanup_field(field_id: str) -> None:
    from app.repositories.project_repo import ProjectRepo
    try:
        ProjectRepo.delete_custom_field(field_id)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 一、DDD 应用门面层（ProjectAppService）自定义函数旁路覆盖
# ═══════════════════════════════════════════════════════════
class TestAppServiceCustomFunc:
    def test_create_and_read_roundtrip(self):
        app = ProjectAppService()
        fid = _mk()
        assert app.create_custom_func(CreateCustomFuncCommand(
            func_id=fid, name="加法", script="return a+b",
            func_type="HTTP", status="ACTIVE", create_user="admin",
        )) is True
        try:
            row = app.get_custom_func(fid)
            assert row is not None
            assert row["id"] == fid
            assert row["name"] == "加法"
            assert row["type"] == "HTTP"
            assert row["status"] == "ACTIVE"
            # list 命中
            lst = app.list_custom_funcs(CustomFuncListQuery(keyword="加法"))
            assert any(r["id"] == fid for r in lst)
            # status 列表含该 id/name/status
            statuses = app.list_custom_func_status()
            assert any(s["id"] == fid and s["name"] == "加法" for s in statuses)
        finally:
            _cleanup_func(fid)

    def test_update_status_delete_roundtrip(self):
        app = ProjectAppService()
        fid = _mk()
        try:
            assert app.create_custom_func(CreateCustomFuncCommand(
                func_id=fid, name="改名", status="DRAFT",
            )) is True
            # 更新名称
            assert app.update_custom_func(
                UpdateCustomFuncCommand(func_id=fid, updates={"name": "改名2"})
            ) is True
            assert app.get_custom_func(fid)["name"] == "改名2"
            # 更新状态
            assert app.update_custom_func_status(
                UpdateCustomFuncStatusCommand(func_id=fid, status="REVIEW")
            ) is True
            assert app.get_custom_func(fid)["status"] == "REVIEW"
            # 删除
            assert app.delete_custom_func(fid) is True
            assert app.get_custom_func(fid) is None
        finally:
            _cleanup_func(fid)


# ═══════════════════════════════════════════════════════════
# 二、DDD 应用门面层（ProjectAppService）自定义字段旁路覆盖
# ═══════════════════════════════════════════════════════════
class TestAppServiceCustomField:
    def test_upsert_and_read_roundtrip(self):
        app = ProjectAppService()
        fid = _mk()
        scope = _mk()
        body = {
            "name": "优先级", "remark": "r", "type": "SELECT",
            "scene": "FUNCTIONAL", "scopeId": scope,
            "options": ["P0", "P1"], "enableOptionKey": True,
        }
        try:
            row = app.upsert_custom_field(UpsertCustomFieldCommand(field_id=fid, body=body))
            assert row is not None and row["id"] == fid
            assert row["name"] == "优先级"
            # list 命中
            lst = app.list_custom_fields(CustomFieldListQuery(scope_id=scope))
            assert any(r["id"] == fid for r in lst)
            # get 单条
            g = app.get_custom_field(fid)
            assert g["type"] == "SELECT"
            # delete
            assert app.delete_custom_field(fid) is True
            assert app.get_custom_field(fid) is None
        finally:
            _cleanup_field(fid)


# ═══════════════════════════════════════════════════════════
# 三、project_service 薄门面经 DDD 委托（对外前端契约不变）
# ═══════════════════════════════════════════════════════════
class TestServiceFacadeBypass:
    """自定义函数/字段在 project_service 中改经 DDD 门面，前端格式契约零变化。"""

    def test_custom_funcs_frontend_shape_via_ddd(self):
        from app.services.project_service import project_service
        fid = _mk()
        try:
            project_service.create_custom_func(
                func_id=fid, name="前端函数", script="return 1",
                func_type="HTTP", status="ACTIVE", project_id="",
                tags=["t1", "t2"], params="[]", result="0", create_user="admin",
            )
            item = project_service.get_custom_func(fid)
            # 前端格式字段齐全
            assert item["id"] == fid
            assert item["name"] == "前端函数"
            assert item["tags"] == ["t1", "t2"]
            assert item["type"] == "HTTP"
            assert item["status"] == "ACTIVE"
            assert isinstance(item["internal"], bool)
            assert isinstance(item["createTime"], int)
            # list 命中 & 前端格式一致
            lst = project_service.list_custom_funcs(keyword="前端函数")
            assert any(x["id"] == fid and x["tags"] == ["t1", "t2"] for x in lst)
            # 状态列表
            statuses = project_service.list_custom_func_status()
            assert any(s["id"] == fid for s in statuses)
            # 更新状态（DDD 门面路径生效）
            assert project_service.update_custom_func_status(fid, "REVIEW") is True
            assert project_service.get_custom_func(fid)["status"] == "REVIEW"
            # 更新（含 tags JSON 序列化仍由 Service 契约层处理）
            assert project_service.update_custom_func(
                fid, {"name": "改名后", "tags": ["x"]}
            ) is True
            item2 = project_service.get_custom_func(fid)
            assert item2["name"] == "改名后"
            assert item2["tags"] == ["x"]
            # 删除
            assert project_service.delete_custom_func(fid) is True
            assert project_service.get_custom_func(fid) is None
        finally:
            _cleanup_func(fid)

    def test_custom_fields_frontend_shape_via_ddd(self):
        from app.services.project_service import project_service
        fid = _mk()
        scope = _mk()
        try:
            created = project_service.upsert_custom_field(fid, {
                "name": "用例类型", "type": "INPUT", "scene": "FUNCTIONAL",
                "scopeId": scope, "options": [],
            })
            assert created["id"] == fid
            assert created["name"] == "用例类型"
            assert created["scopeType"] == "PROJECT"
            assert isinstance(created["internal"], bool)
            # list 命中
            lst = project_service.list_custom_fields(scope)
            assert any(x["id"] == fid for x in lst)
            # get 单条
            g = project_service.get_custom_field(fid)
            assert g["name"] == "用例类型"
            # 删除
            assert project_service.delete_custom_field(fid) is True
            assert project_service.get_custom_field(fid) is None
        finally:
            _cleanup_field(fid)
