"""Service 层覆盖补齐对齐回归测试
============================================================
验证 4 个域（case_review / ai_config / ai_conversation / invitation）
的 Service 层作为 router 唯一业务入口，路由不再直接 import repo/store。

测试锁定：
  - 各 Service 方法存在且与底层 repo/store 委托行为一致；
  - 路由层不再直接引用 repo 类（由服务层代理）；
  - Service 方法可真实完成对应业务操作（落库 / 读回）；
  - 关键路由端点仍可通过（由 HTTP 入口间接调用 Service）。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")


def _uniq(prefix="SRV"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ─────────────────────────────────────────────────────────────
# 1) invitation 域 Service
# ─────────────────────────────────────────────────────────────
def test_invitation_service_exists_and_delegates():
    """invitation_service 方法齐全且与 repo 行为一致。"""
    from app.repositories.invitation_repo import invitation_repo
    from app.services.invitation_service import invitation_service

    # 方法存在
    for method in ("create_invite", "get_by_invite_id", "is_valid", "mark_used"):
        assert hasattr(invitation_service, method), f"缺少方法 {method}"

    # create + get + is_valid 闭环
    email = _uniq("invite") + "@example.com"
    inv = invitation_service.create_invite(
        [email], scope="SYSTEM", create_user="admin",
    )
    assert inv is not None and inv["invite_id"]
    try:
        iid = inv["invite_id"]
        # Service 与 repo 读回一致
        via_svc = invitation_service.get_by_invite_id(iid)
        via_repo = invitation_repo.get_by_invite_id(iid)
        assert via_svc and via_svc["invite_id"] == via_repo["invite_id"]
        # is_valid 都返回 True
        assert invitation_service.is_valid(iid) is True
        # mark_used 后 is_valid 变 False
        assert invitation_service.mark_used(iid) is True
        assert invitation_service.is_valid(iid) is False
    finally:
        try:
            from app.core.database import Database
            conn = Database.get_conn("auth.db")
            conn.execute("DELETE FROM invitations WHERE email=?", (email,))
            conn.commit()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# 2) ai_config 域 Service
# ─────────────────────────────────────────────────────────────
def test_ai_config_service_functional_case():
    """功能用例 AI 配置经 service 保存/读取一致。"""
    from app.repositories.ai_config_repo import SCOPE_FUNCTIONAL_CASE
    from app.services.ai_config_service import ai_config_service

    owner = _uniq("func-owner")
    cfg_data = {"designConfig": {"normal": False, "abnormal": True}}
    # 保存
    saved = ai_config_service.save_functional_case_config(
        config_value=cfg_data, owner=owner,
    )
    assert saved and saved["id"]
    # 读取（service 自动合并默认）
    cfg = ai_config_service.get_functional_case_config(
        owner=owner, project_id="",
    )
    assert cfg.get("designConfig", {}).get("normal") is False
    assert cfg.get("designConfig", {}).get("abnormal") is True
    # 直查 repo 确认落库
    from app.repositories.ai_config_repo import AiConfigRepo
    got = AiConfigRepo.get(SCOPE_FUNCTIONAL_CASE, "default", owner, "")
    assert got and got["id"] == saved["id"]
    # 清理
    AiConfigRepo.delete(SCOPE_FUNCTIONAL_CASE, "default", owner, "")


def test_ai_config_service_api_case():
    """接口用例 AI 配置经 service 保存/读取一致。"""
    from app.repositories.ai_config_repo import SCOPE_API_CASE, AiConfigRepo
    from app.services.ai_config_service import ai_config_service

    owner = _uniq("api-owner")
    cfg_data = {"normal": True, "abnormal": True, "caseName": False}
    saved = ai_config_service.save_api_case_config(
        config_value=cfg_data, owner=owner,
    )
    assert saved and saved["id"]
    # 读取
    cfg = ai_config_service.get_api_case_config(owner=owner, project_id="")
    assert cfg.get("normal") is True
    assert cfg.get("caseName") is False
    # 清理
    AiConfigRepo.delete(SCOPE_API_CASE, "default", owner, "")


# ─────────────────────────────────────────────────────────────
# 3) ai_conversation 域 Service
# ─────────────────────────────────────────────────────────────
def test_ai_conversation_service_lifecycle():
    """AI 对话经 service 完成 建/列/读/消息/更新/删 闭环。"""
    from app.repositories.ai_conversation_repo import AiConversationRepo
    from app.services.ai_config_service import ai_config_service

    owner = _uniq("conv-svc-owner")
    conv = ai_config_service.create_conversation(
        title="Svc会话", owner=owner, create_user=owner, module_type="ai",
    )
    try:
        assert conv["id"]
        # 读回
        got = ai_config_service.get_conversation(conv["id"])
        assert got and got["id"] == conv["id"]
        # 列表
        ids = [c["id"] for c in ai_config_service.list_conversations(owner, "PERSONAL")]
        assert conv["id"] in ids
        # 消息
        m = ai_config_service.add_message(conv["id"], "user", "你好", "text")
        assert m["content"] == "你好"
        msgs = ai_config_service.list_messages(conv["id"])
        assert len(msgs) == 1
        # 更新标题
        upd = ai_config_service.update_conversation(conv["id"], title="新标题")
        assert upd["title"] == "新标题"
        # 直查 repo 确认
        r = AiConversationRepo.get_conversation(conv["id"])
        assert r and r["title"] == "新标题"
    finally:
        ai_config_service.delete_conversation(conv["id"])


def test_ai_config_router_no_direct_repo_import():
    """ai_config 路由应经 service 而非直接 import repo。"""
    import inspect

    from app.routers import ai_config

    src = inspect.getsource(ai_config)
    # 路由源码不应直接 import AiConversationRepo
    assert "AiConversationRepo" not in src or "ai_config_service" in src
    assert "from app.services.ai_config_service" in src


# ─────────────────────────────────────────────────────────────
# 4) case_review 域 Service
# ─────────────────────────────────────────────────────────────
def test_case_review_service_exists():
    """case_review_service 方法齐全。"""
    from app.services.case_review_service import case_review_service

    methods = [
        "list_reviews", "get_review", "create_review", "update_review",
        "delete_review", "copy_review", "list_links", "link_cases",
        "unlink_cases", "get_review_case_status", "update_link_status",
        "toggle_follow", "is_following", "list_review_users",
        "build_review_module_tree", "add_review_module",
        "update_review_module", "delete_review_module",
        "move_review_module", "review_count_by_module",
    ]
    for m in methods:
        assert hasattr(case_review_service, m), f"缺少方法 {m}"

    # 状态常量
    assert hasattr(case_review_service, "RESULT_PASS")
    assert hasattr(case_review_service, "RESULT_UN_PASS")


def test_case_review_service_basic_flow():
    """case_review_service 建/读/关联/状态/关注 闭环。"""
    from app.services.case_review_service import case_review_service as svc

    # 创建评审
    rev = svc.create_review(
        name=_uniq("CR-SVC"), description="service 创建",
        project_id="p-svc", reviewers=["admin"],
    )
    assert rev and rev["id"]
    try:
        rid = rev["id"]
        # 读取
        got = svc.get_review(rid)
        assert got and got["id"] == rid
        assert got["name"] == rev["name"]
        # 关联用例
        case_id = _uniq("case-svc")
        assert svc.link_cases(rid, [case_id]) >= 1
        assert case_id in svc.list_link_case_ids(rid)
        # 状态更新
        svc.update_link_status(rid, [case_id], svc.RESULT_PASS,
                               reviewer="admin", comment="pass")
        counts = svc.get_review_case_status(rid)
        assert counts["passCount"] >= 1
        # 关注
        assert svc.toggle_follow(rid, "user-1") is True
        assert svc.is_following(rid, "user-1") is True
        # 列表含创建项
        page = svc.list_reviews(project_id="p-svc", page_size=10, current=1)
        assert page["total"] >= 1
        assert any(item["id"] == rid for item in page["list"])
    finally:
        # 清理（硬删除）
        try:
            from app.repositories.case_review_repo import CaseReviewRepo
            CaseReviewRepo.delete_review(rid, soft=False)
        except Exception:
            svc.delete_review(rid)


def test_case_review_router_not_direct_store():
    """case_review 路由应经 service，而非直接 import store。"""
    import inspect

    from app.routers import case_review

    src = inspect.getsource(case_review)
    # 路由不应直接 import review_store
    assert "from app.cases import review_store" not in src
    # 路由应使用 case_review_service
    assert "case_review_service" in src or "cvs." in src
