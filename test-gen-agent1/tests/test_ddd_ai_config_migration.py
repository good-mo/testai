"""DDD ai_config 域（config 子域）阶段 C 薄门面接线回归测试。

背景
----
`app/domain/ai_config/` DDD 层就绪后，`app/services/ai_config_service.py`
对 **ai_config 子域**（功能/接口用例 AI 配置 save/get）收敛为对
`ai_config_app_service` 的薄委托门面；ai_conversation 子域（无 DDD 域）
维持原直连 AiConversationRepo，不在本接线范围。

验证：
  1. 修复 DDD 仓储 round-trip 缺陷：读聚合后 config_value 不丢；
  2. service 的 4 个 config 方法确实委托 DDD 门面；
  3. 默认兜底合并契约不回归（前端直接读 config 完整结构）；
  4. 保存→读回→删除 闭环。
"""
import uuid

from app.domain.ai_config.application.ai_config_app_service import ai_config_app_service as ddd
from app.repositories.ai_config_repo import (
    SCOPE_API_CASE,
    SCOPE_FUNCTIONAL_CASE,
    AiConfigRepo,
)
from app.services.ai_config_service import ai_config_service as svc


def _owner():
    return f"ai-cfg-ddd-{uuid.uuid4().hex[:8]}"


def _cleanup(scope, owner):
    try:
        AiConfigRepo.delete(scope, "default", owner, "")
    except Exception:
        pass


def test_ddd_repo_roundtrip_preserves_config_value():
    """DDD ai_config 仓储读回不丢 config_value（修复 round-trip 缺陷）。"""
    owner = _owner()
    AiConfigRepo.save(SCOPE_FUNCTIONAL_CASE,
                      {"designConfig": {"normal": False}}, owner=owner)
    from app.domain.ai_config.infrastructure.ai_config_repository_impl import (
        AiConfigRepoAdapter,
    )
    try:
        ent = AiConfigRepoAdapter().get(SCOPE_FUNCTIONAL_CASE, owner=owner)
        assert ent is not None
        assert ent.to_dict()["config_value"] == {"designConfig": {"normal": False}}
    finally:
        _cleanup(SCOPE_FUNCTIONAL_CASE, owner)


def test_config_save_delegates_to_ddd(monkeypatch):
    """save_*_config 委托 DDD save。"""
    owner = _owner()
    called = []
    real = ddd.save

    def fake_save(cmd):
        called.append((cmd.scope, cmd.owner))
        return real(cmd)

    monkeypatch.setattr(ddd, "save", fake_save)
    try:
        svc.save_functional_case_config(
            {"designConfig": {"aiEngine": "deepseek"}}, owner=owner)
        assert called and called[0][0] == SCOPE_FUNCTIONAL_CASE
    finally:
        _cleanup(SCOPE_FUNCTIONAL_CASE, owner)


def test_config_get_delegates_to_ddd(monkeypatch):
    """get_*_config 委托 DDD get。"""
    owner = _owner()
    svc.save_functional_case_config(
        {"designConfig": {"normal": False}}, owner=owner)
    called = []
    real = ddd.get

    def fake_get(cmd):
        called.append((cmd.scope, cmd.owner))
        return real(cmd)

    monkeypatch.setattr(ddd, "get", fake_get)
    try:
        cfg = svc.get_functional_case_config(owner=owner)
        assert called and called[0][0] == SCOPE_FUNCTIONAL_CASE
        assert cfg["designConfig"]["normal"] is False
    finally:
        _cleanup(SCOPE_FUNCTIONAL_CASE, owner)


def test_save_get_roundtrip_with_default_merge():
    """功能用例配置：保存→默认兜底合并读回。"""
    owner = _owner()
    try:
        svc.save_functional_case_config(
            {"designConfig": {"normal": False, "aiEngine": "deepseek"}},
            owner=owner)
        cfg = svc.get_functional_case_config(owner=owner)
        assert cfg["designConfig"]["normal"] is False
        assert cfg["designConfig"]["aiEngine"] == "deepseek"
        # 默认兜底字段完整
        assert "templateConfig" in cfg
        assert "designConfig" in cfg
    finally:
        _cleanup(SCOPE_FUNCTIONAL_CASE, owner)


def test_api_config_roundtrip():
    """接口用例配置：保存→默认兜底合并读回。"""
    owner = _owner()
    try:
        # 用默认结构内的布尔键保存（前端实发字段）
        default = {
            "normal": True, "abnormal": True,
            "requestParams": True, "preScript": True,
            "assertion": False,
        }
        svc.save_api_case_config(default, owner=owner)
        cfg = svc.get_api_case_config(owner=owner)
        assert cfg["normal"] is True and cfg["assertion"] is False
        for k in ("caseName", "postScript"):
            assert k in cfg, f"缺默认兜底键 {k}"
    finally:
        _cleanup(SCOPE_API_CASE, owner)
