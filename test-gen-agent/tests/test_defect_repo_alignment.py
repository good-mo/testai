"""
缺陷 Repository / Service 层一致性回归测试
================================================
目的：`app.repositories.defect_repo.DefectRepo` 是缺陷表唯一 DB 访问入口，
`app.services.defect_service` 是其唯一业务封装。原兼容门面
`app.defects.tracker` 已删除，本测试直接锁定 repo 与 service 两层在
CRUD / 回收站 / 评论 / 统计 / 自动创建上的行为一致与分层语义
（repo 不透传删除态，service 负责对调用方隐藏回收站记录）。

一旦某层输出与另一层不一致，此处会立即暴露，避免把脏差异带到 router 层。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.core.exceptions import ValidationError  # noqa: E402
from app.repositories.defect_repo import DefectRepo  # noqa: E402
from app.services.defect_service import DefectService  # noqa: E402

service = DefectService()


def _uniq(prefix="DEF-ALIGN"):
    """生成唯一标题，避免与库中既有缺陷冲突。"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _sample(**over):
    """构造一条完整缺陷数据（非时间字段全部固定）。"""
    data = {
        "title": _uniq(),
        "description": "repo-alignment 描述",
        "severity": "minor",
        "file_path": "tests/repo_align_defect.py",
        "test_case_id": "case-1",
        "error_snippet": "AssertionError: boom",
        "assignee": "admin",
    }
    data.update(over)
    return data


# ── 创建 / 读取一致性 ────────────────────────────────────────
def test_repo_and_service_create_output_consistent():
    """同一份数据经 Repo 与 service 创建后，非时间字段应一致。"""
    nd = DefectRepo.create(_sample())
    sd = service.create(_sample())
    try:
        for f in ("title", "description", "severity", "status",
                  "file_path", "test_case_id", "error_snippet", "assignee"):
            assert nd.get(f) == sd.get(f), f"创建字段 {f} 不一致 repo={nd.get(f)!r} svc={sd.get(f)!r}"
        # 新建缺陷默认 open 状态
        assert nd["status"] == sd["status"] == "open"
    finally:
        DefectRepo.purge(nd["id"])
        DefectRepo.purge(sd["id"])


def test_repo_get_matches_service_get_on_active():
    """活跃缺陷经 Repo.get 与 service.get 读回字段一致。"""
    d = DefectRepo.create(_sample())
    try:
        n = DefectRepo.get(d["id"])
        s = service.get(d["id"])
        assert n is not None and s is not None
        assert set(n.keys()) == set(s.keys()), "返回字段集合不一致"
        for f in ("title", "description", "severity", "status"):
            assert n[f] == s[f], f"get 字段 {f} 不一致"
    finally:
        DefectRepo.purge(d["id"])


def test_update_output_consistent():
    """repo.update 与 service.update 对相同更新返回一致字段。"""
    d1 = DefectRepo.create(_sample())
    d2 = DefectRepo.create(_sample())
    try:
        upd = {"title": "updated-title", "status": "fixed",
               "description": "updated-desc", "severity": "critical"}
        r2 = DefectRepo.update(d1["id"], dict(upd))
        s2 = service.update(d2["id"], dict(upd))
        for f in ("title", "description", "severity", "status"):
            assert r2.get(f) == s2.get(f), f"更新后字段 {f} 不一致"
        assert r2.get("title") == upd["title"]
    finally:
        DefectRepo.purge(d1["id"])
        DefectRepo.purge(d2["id"])


def test_invalid_status_severity_raise():
    """非法 status/severity：repo 抛 ValueError，service 转 400 风格 ValidationError。"""
    d = DefectRepo.create(_sample())
    try:
        for bad in ({"status": "bogus"}, {"severity": "weird"}):
            try:
                DefectRepo.update(d["id"], dict(bad))
                raise AssertionError(f"Repo 未对 {bad} 抛 ValueError")
            except ValueError:
                pass
            try:
                service.update(d["id"], dict(bad))
                raise AssertionError(f"service 未对 {bad} 抛 ValidationError")
            except ValidationError:
                pass
    finally:
        DefectRepo.purge(d["id"])


# ── 查询 / 统计一致性 ────────────────────────────────────────
def test_list_count_stats_consistent():
    """repo.list/count/get_stats 与 service 同源一致。"""
    rows, total = service.list(limit=20)
    assert len(rows) == total
    assert len(DefectRepo.list(limit=20)) == len(rows)
    assert DefectRepo.count() == total
    for st in ("open", "fixed", "critical"):
        assert len(DefectRepo.list(status=st)) == DefectRepo.count(status=st)

    base = DefectRepo.get_stats()
    svc_stats = service.get_stats()
    assert svc_stats["total"] == base["total"]
    assert svc_stats["trash"] == base["trash"]
    assert svc_stats["by_status"] == base["by_status"]


def test_include_deleted_filter():
    """include_deleted 让 repo.list 可读回收站，service.list 则默认隐藏。"""
    total_all = DefectRepo.count(include_deleted=True)
    assert total_all >= DefectRepo.count()
    assert len(DefectRepo.list(include_deleted=True, limit=1000)) == total_all


# ── 回收站 / 软删除分层语义 ──────────────────────────────────
def test_soft_delete_layer_semantics():
    """软删除后：service.get 隐藏（返回 None），repo.get 保留 deleted 记录。"""
    d = DefectRepo.create(_sample())
    try:
        # 回收站前活跃可见
        assert service.get(d["id"]) is not None
        assert DefectRepo.get_checked(d["id"]) is not None

        # 软删除（repo 幂等返回 True）
        assert DefectRepo.soft_delete(d["id"]) is True
        # service 对调用方隐藏：get 返回 None
        assert service.get(d["id"]) is None
        # repo 层仍可见 raw 记录且 deleted=1
        raw = DefectRepo.get(d["id"])
        assert raw is not None and raw["deleted"] == 1
        # 回收站列表可见
        trash_ids = [t["id"] for t in DefectRepo.list_trash(limit=200)]
        assert d["id"] in trash_ids

        # 恢复后 service 重新可见
        assert DefectRepo.restore(d["id"]) is True
        assert service.get(d["id"]) is not None
    finally:
        DefectRepo.purge(d["id"])


def test_service_trash_restore_purge_flow():
    """service.trash/restore 与 repo 回收站状态联动。"""
    d = DefectRepo.create(_sample())
    try:
        service.trash(d["id"])
        assert service.get(d["id"]) is None
        assert DefectRepo.count_trash() >= 1
        service.restore(d["id"])
        assert service.get(d["id"]) is not None
    finally:
        # repo 兜底彻底清理
        DefectRepo.purge(d["id"])


# ── 评论一致性 ───────────────────────────────────────────────
def test_comment_crud_consistent():
    """评论在 repo 与 service 间共享同一份数据，输出一致。"""
    bug = DefectRepo.create(_sample())
    try:
        nc = DefectRepo.create_comment(bug["id"], content="repo-评论", create_user="admin")
        sc = service.create_comment(bug["id"], content="svc-评论", create_user="admin")
        try:
            assert set(nc.keys()) == set(sc.keys()), "评论字段集合不一致"
            assert nc["bug_id"] == sc["bug_id"] == bug["id"]
            assert nc["create_user"] == sc["create_user"] == "admin"
            # 互见（同一张表）
            assert DefectRepo.get_comment(nc["id"]) is not None
            assert service.list_comments(bug["id"]) is not None
            assert len(service.list_comments(bug["id"])) == 2
            # 更新
            un = DefectRepo.update_comment(nc["id"], "updated")
            assert un["content"] == "updated"
            # 删除
            assert DefectRepo.delete_comment(sc["id"]) is True
            assert DefectRepo.get_comment(sc["id"]) is None
        finally:
            DefectRepo.delete_comment(nc["id"])
    finally:
        DefectRepo.purge(bug["id"])


# ── 自动创建一致性 ───────────────────────────────────────────
def test_auto_create_repo_and_service_consistent():
    """测试失败自动建缺陷：repo 与 service 判定与输出一致。"""
    # passed → None
    assert DefectRepo.auto_create_from_result("f.py", {"passed": True}) is None
    assert service.auto_create_from_result("f.py", {"passed": True}) is None

    cases = [
        ("ERROR: boom", "critical", "测试失败"),
        ("Traceback: x", "critical", "测试失败"),
        ("AssertionError: assert 1", "critical", "断言失败"),
        ("ImportError: no module", "critical", "导入错误"),
        ("ModuleNotFoundError: x", "critical", "导入错误"),
        ("TypeError: arg", "critical", "类型错误"),
        ("SyntaxError: bad", "critical", "语法错误"),
        ("Exception: fatal", "blocker", "测试失败"),
        ("some regular text", "major", "测试失败"),
    ]
    created = []
    try:
        for stderr, sev, prefix in cases:
            res = {"passed": False, "stderr": stderr, "stdout": ""}
            nd = DefectRepo.auto_create_from_result("tests/auto_fail.py", res)
            sd = service.auto_create_from_result("tests/auto_fail.py", res)
            assert nd is not None and sd is not None
            created += [nd["id"], sd["id"]]
            assert nd["severity"] == sd["severity"] == sev, \
                f"stderr={stderr!r} 严重级别不一致 repo={nd['severity']} svc={sd['severity']}"
            assert nd["title"] == sd["title"], "自动创建标题不一致"
            assert prefix in nd["title"], f"标题 {nd['title']} 缺前缀 {prefix}"
            assert nd["error_snippet"] == sd["error_snippet"]
    finally:
        for did in created:
            DefectRepo.purge(did)
