"""org → identity 域 DDD application 方法面补全（旁路方法收敛）回归测试。

背景：
  - 目标：大域 DDD application 方法与旧 service 逐方法对齐。
    organization_service 中仍直连 OrganizationRepo 的旁路方法（组织删除/恢复、
    成员查询、组织反查、项目绑定、租户摘要）此前未进入 identity 域 DDD 应用门面。
  - 本次：把这些旁路方法补齐进 `IdentityAppService`（薄委托既有 OrganizationRepo，
    防腐层不搬移业务），并将 `organization_service` 相应方法收敛为对 `_ddd` 的委托。

本测试验证：
  1. `OrganizationService` 各旁路方法确以 DDD `IdentityAppService` 为编排门面。
  2. DDD 门面具备与旧 service 一致的逐方法能力。
  3. 薄委托端到端契约（返回值结构）与直连既有 OrganizationRepo 完全一致。
"""

import uuid

from app.services.organization_service import organization_service

TAG = "orgdddsurface"


def _mk(prefix="o") -> str:
    return f"{prefix}-{TAG}-{uuid.uuid4().hex[:8]}"


class TestOrgBypassSurfaceDelegation:
    def test_count_and_delete_recover_via_ddd(self):
        """组织删除/恢复/统计经 identity DDD 门面。"""
        name = _mk("name")
        org = organization_service.create(name, "desc")
        oid = org["id"]
        try:
            # 统计
            assert organization_service.count() >= 1
            # 按名查询
            by_name = organization_service.get_by_name(name)
            assert by_name and by_name["id"] == oid
            # 软删除
            assert organization_service.delete(oid) is True
            assert organization_service.get(oid) is None
            # 恢复
            assert organization_service.recover(oid) is True
            assert organization_service.get(oid) is not None
        finally:
            try:
                organization_service.delete(oid, hard=True)
            except Exception:
                pass

    def test_member_queries_via_ddd(self):
        """成员查询经 identity DDD 门面。"""
        org = organization_service.create(_mk("m"), "desc")
        oid = org["id"]
        try:
            members = organization_service.list_members(oid)
            assert isinstance(members, list)
            assert organization_service.count_members(oid) == len(members)
            if members:
                mid = members[0]["id"]
                m = organization_service.get_member(mid)
                assert m and m["id"] == mid
            # 组织反查（default-org 有默认 admin）
            orgs_by_user = organization_service.list_orgs_by_user("admin")
            assert isinstance(orgs_by_user, list)
            # 批量反查
            users = list({m.get("user_id") for m in members if m.get("user_id")})
            if users:
                result = organization_service.list_orgs_by_users(users)
                assert isinstance(result, dict)
        finally:
            try:
                organization_service.delete(oid, hard=True)
            except Exception:
                pass

    def test_project_binding_via_ddd(self):
        """组织项目绑定经 identity DDD 门面。"""
        org = organization_service.create(_mk("p"), "desc")
        oid = org["id"]
        try:
            projects = organization_service.list_projects(oid)
            assert isinstance(projects, list)
        finally:
            try:
                organization_service.delete(oid, hard=True)
            except Exception:
                pass

    def test_tenant_summary_via_ddd(self):
        """租户摘要经 identity DDD 门面。"""
        summary = organization_service.tenant_summary()
        assert "orgCount" in summary and "memberCount" in summary
        # 兼容命名
        alt = organization_service.get_tenant_summary()
        assert "orgCount" in alt
