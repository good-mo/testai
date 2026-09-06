"""apitest 域旁路方法面 DDD 薄门面回归测试（module_tree/execution/followers/operation_logs/schedules）。

背景：
  `apitest_service` 中 module_tree / execution / followers / operation_logs /
  schedules 相关旁路方法已收敛为对 `apitest_app_service`（DDD 门面）的**薄委托**，
  Service 不再直接调用 `ApitestRepo`。

本测试用**代码级断言**锁定委托关系（不依赖运行期数据库），防止后续回退为
直连 Repo；同时对 `apitest_service` 与 `apitest_app_service` 的**签名兼容性**
做快照校验。
"""
import ast
import inspect
from pathlib import Path

import pytest

from app.domain.apitest.application.apitest_app_service import apitest_app_service
from app.services.apitest_service import apitest_service

# 需要校验的旁路方法组
BYPASS_GROUPS = {
    "module_tree": [
        "build_module_tree", "add_module", "update_module", "delete_module",
        "get_module", "list_modules", "move_module", "count_modules",
    ],
    "execution": [
        "run_case", "debug_api_call", "run_scenario",
        "import_content", "get_assert_types",
    ],
    "followers": [
        "list_followers", "follow_resource", "unfollow_resource",
        "toggle_follow", "is_followed",
    ],
    "operation_logs": [
        "list_operation_logs", "count_operation_logs", "clear_operation_logs",
        "list_execution_logs", "count_execution_logs", "clear_execution_logs",
    ],
    "schedules": [
        "list_schedules",
    ],
}

# 展平全部目标方法名
ALL_TARGETS = [m for ms in BYPASS_GROUPS.values() for m in ms]


def _service_src() -> str:
    path = Path(inspect.getfile(apitest_service.__class__))
    return path.read_text(encoding="utf-8")


def _method_src(name: str) -> str:
    """从 ApitestService 源码中提取指定方法的源码文本。"""
    src = _service_src()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ApitestService":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == name:
                    return ast.get_source_segment(src, item)
    raise AssertionError(f"方法 {name} 不在 ApitestService 中")


class TestBypassDelegation:
    """校验旁路方法确实委托 apitest_app_service。"""

    @pytest.mark.parametrize("method_name", ALL_TARGETS)
    def test_method_delegates_to_app_service(self, method_name):
        src = _method_src(method_name)
        assert "apitest_app_service." in src, (
            f"{method_name} 未委托 apitest_app_service"
        )
        assert "ApitestRepo." not in src, (
            f"{method_name} 仍直接调用 ApitestRepo"
        )

    @pytest.mark.parametrize("method_name", ALL_TARGETS)
    def test_method_exists_in_both_service_and_app_service(self, method_name):
        assert hasattr(apitest_service, method_name)
        assert hasattr(apitest_app_service, method_name)


class TestSignatureCompatibility:
    """校验 apitest_service 与 apitest_app_service 的签名兼容。"""

    @pytest.mark.parametrize("method_name", ALL_TARGETS)
    def test_signature_params_compatible(self, method_name):
        svc_params = list(inspect.signature(
            getattr(apitest_service, method_name)).parameters)
        # 去掉 self
        svc_params = [p for p in svc_params if p != "self"]
        app_params = list(inspect.signature(
            getattr(apitest_app_service, method_name)).parameters)
        app_params = [p for p in app_params if p != "self"]

        # Service 的参数是 app_service 参数的超集（含 **kwargs 等兼容扩展）
        missing = [p for p in app_params if p not in svc_params]
        assert not missing, (
            f"{method_name}: app_service 参数 {missing} 在 service 中缺失"
        )


class TestGroupPresence:
    """校验各旁路组的方法都在 service 与 app_service 上存在。"""

    @pytest.mark.parametrize("group,methods", BYPASS_GROUPS.items())
    def test_group_methods_present(self, group, methods):
        for m in methods:
            assert hasattr(apitest_service, m), f"{group}.{m} 缺失于 service"
            assert hasattr(apitest_app_service, m), (
                f"{group}.{m} 缺失于 app_service"
            )
