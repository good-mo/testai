"""工作流状态域补齐：workflow_repo / workflow_service 行为回归测试
====================================================================
目的：工作流状态管理数据访问统一收敛于
  - app.repositories.workflow_repo（数据访问唯一权威，直连 SQLite）
  - app.services.workflow_service（router 唯一业务入口）

原兼容门面 app.projects.workflow_store 已删除，本测试直接 import repo，
锁定 workflow 域「播种 → 列表 → 新增 → 排序 → 流转 → 定义标记 →
更新 → 删除」全链路落库语义，确保 service/repo 输出零回归，
「保存即落库、重启可读回」的持久化保证不被破坏。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.repositories import workflow_repo  # noqa: E402
from app.services.workflow_service import WorkflowService  # noqa: E402

service = WorkflowService()


def _scope():
    """生成唯一 scope，隔离各用例数据。"""
    return f"wf-align-{uuid.uuid4().hex[:8]}"


def _cleanup(scope_type, scope_id, scene):
    """清理本用例播种/新增的状态。"""
    for st in workflow_repo.list_statuses(scope_type, scope_id, scene):
        workflow_repo.delete_status(st["id"])


def test_seed_default_statuses_full_flow():
    """seed 播种默认三态并建立流转链，service 与旧门面一致。"""
    sid = _scope()
    try:
        seeds = service.seed_default_statuses("PROJECT", sid, "FUNCTIONAL")
        assert len(seeds) == 3, f"默认应播种 3 个状态，实际 {len(seeds)}"
        # 初始态/结束态标记
        by_defs = {tuple(s["statusDefinitions"]) for s in seeds}
        assert ("START",) in by_defs and ("END",) in by_defs
        # 流转链通过 list_statuses 读回验证（seed 返回值不含 flows，以重读为准）
        items = service.list_statuses("PROJECT", sid, "FUNCTIONAL")
        assert items[0]["statusFlowTargets"] == [items[1]["id"]]
        assert items[1]["statusFlowTargets"] == [items[2]["id"]]
        assert items[2]["statusFlowTargets"] == []
        # 幂等：重复播种返回既有数据、不重复插入
        again = service.seed_default_statuses("PROJECT", sid, "FUNCTIONAL")
        assert len(again) == 3
        assert {s["id"] for s in again} == {s["id"] for s in seeds}
        # repo 视角一致
        old_items = workflow_repo.list_statuses("PROJECT", sid, "FUNCTIONAL")
        assert len(old_items) == 3
    finally:
        _cleanup("PROJECT", sid, "FUNCTIONAL")


def test_add_update_sort_flows_definitions_roundtrip():
    """新增状态后：排序 / 流转 / 定义标记 / 改名读回均落库。"""
    pid = _scope()
    try:
        seeds = service.seed_default_statuses("PROJECT", pid, "FUNCTIONAL")
        # 新增
        added = service.add_status("评审中", "FUNCTIONAL", pid, "PROJECT", "备注")
        assert added["name"] == "评审中"
        # 排序（新状态排最前）
        ids = [added["id"]] + [s["id"] for s in seeds]
        assert service.sort_statuses(ids) is True
        ordered = service.list_statuses("PROJECT", pid, "FUNCTIONAL")
        assert ordered[0]["id"] == added["id"]
        assert ordered[0]["pos"] == 0
        # 流转：新增 -> 处理中
        assert service.update_flows(added["id"], [seeds[1]["id"]]) is True
        # 定义标记：设新增为 END
        assert service.set_definition(added["id"], "END", True) is True
        # 更新名称
        upd = service.update_status(added["id"], name="评审中X")
        assert upd["name"] == "评审中X"
        # 读回校验
        got = service.list_statuses("PROJECT", pid, "FUNCTIONAL")
        by_id = {s["id"]: s for s in got}
        assert by_id[added["id"]]["name"] == "评审中X"
        assert by_id[added["id"]]["statusFlowTargets"] == [seeds[1]["id"]]
        assert "END" in by_id[added["id"]]["statusDefinitions"]
    finally:
        _cleanup("PROJECT", pid, "FUNCTIONAL")


def test_delete_cleans_flows():
    """删除状态时级联清空其作为来源/目标的流转关系。"""
    oid = _scope()
    try:
        seeds = service.seed_default_statuses("ORGANIZATION", oid, "BUG")
        # 新建一个并挂流转
        extra = service.add_status("暂缓", "BUG", oid, "ORGANIZATION")
        service.update_flows(extra["id"], [seeds[0]["id"]])
        # 让 seeds[0] 也流转到 extra（建立双向引用便于验证级联）
        service.update_flows(seeds[0]["id"], [extra["id"]])
        assert service.delete_status(extra["id"]) is True
        # 删除后：sources 为空，目标里也不应残留 extra
        got = service.list_statuses("ORGANIZATION", oid, "BUG")
        assert all(extra["id"] not in s["statusFlowTargets"] for s in got)
    finally:
        _cleanup("ORGANIZATION", oid, "BUG")

