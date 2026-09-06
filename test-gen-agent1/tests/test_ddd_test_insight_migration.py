"""TestInsight 域 DDD 迁移（A→B→C）回归测试。

验证迁移后：
  1. 阶段 B：Web 适配 DTO 桥（web_bridge）把既有接口形态接入 DDD 应用服务；
  2. 阶段 C：Service 已薄化为对 DDD 应用服务的门面，不再直连旧 Repository；
  3. 对外行为（list / record / value / prove）与迁移前一致、可回滚。
"""
import uuid

import pytest

from app.domain.test_insight.application import web_bridge
from app.domain.test_insight.application.test_insight_app_service import (
    test_insight_app_service,
)
from app.services.insight_service import insight_service

TAG = "dddmigrate"


def _mk() -> str:
    return f"/__{TAG}/{uuid.uuid4().hex[:8]}.py"


@pytest.fixture
def trace_file():
    fpath = _mk()
    yield fpath
    # 清理本测试产生的执行记录
    from app.repositories.insight_repo import InsightRepo
    conn = InsightRepo._conn()
    conn.execute("DELETE FROM test_runs WHERE file_path = ?", (fpath,))
    conn.commit()


def test_service_facade_records_via_ddd(trace_file):
    """阶段 C：insight_service 薄门面经 DDD 应用服务记录执行追溯。"""
    rec = insight_service.record_trace(
        file_path=trace_file, result="passed", passed_count=3, coverage=88.0,
        created_by="admin",
    )
    assert rec["id"]
    # 领域层保证的覆盖字段全量回读
    got = test_insight_app_service.get(rec["id"])
    assert got and got["file_path"] == trace_file
    assert got["result"] == "passed"
    assert got["coverage"] == 88.0


def test_web_bridge_list_shape_consistent(trace_file):
    """阶段 B：web_bridge.list_trace 返回与既有 Web 契约一致的 keys。"""
    insight_service.record_trace(file_path=trace_file, result="passed", passed_count=1)
    data = web_bridge.list_trace(file_path=trace_file)
    assert set(("runs", "stats", "total", "attributions")) <= set(data)
    assert data["total"] >= 1
    assert all("file_path" in r for r in data["runs"])
    # 归因字典与领域层一致
    from app.domain.test_insight.domain.value_objects.attribution import (
        ATTRIBUTION_LABELS,
    )
    assert data["attributions"] == dict(ATTRIBUTION_LABELS)


def test_web_bridge_value_aggregated():
    """阶段 B：web_bridge.get_value 聚合 value + incident_avoidance。"""
    data = web_bridge.get_value()
    assert "value" in data
    assert "incident_avoidance" in data


def test_web_bridge_prove_and_skill_path(trace_file):
    """阶段 B：prove_coverage / skill_path 可正常经桥调用。"""
    insight_service.record_trace(file_path=trace_file, result="passed",
                                 passed_count=2, coverage=90.0)
    proof = web_bridge.prove_coverage(trace_file)
    assert proof["file_path"] == trace_file
    assert proof["has_passed_evidence"] is True
    sp = web_bridge.get_skill_path()
    assert isinstance(sp, dict)


def test_defective_without_counts_is_rejected():
    """领域规则下沉：failed 结果必须有失败/报错计数支撑（迁移后生效）。"""
    from app.domain.common.exceptions import DomainValidationError
    with pytest.raises(DomainValidationError):
        insight_service.record_trace(
            file_path=_mk(), result="failed",
            passed_count=0, failed_count=0, error_count=0,
        )
