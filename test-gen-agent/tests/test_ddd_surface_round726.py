"""DDD application 方法面补全回归（Issue #726 · 大域旁路方法面收敛）。

覆盖本轮为 5 个域补齐 DDD application 方法面后的**代码级**约束：
  1. environment：launch/stop/health_check/health_check_all 已下沉到
     `environment_app_service`；`environment_service` 仅薄委托（不直连子进程）。
  2. case_review：list_links / is_following 读方法已补到 `case_review_app_service`，
     并接入 Repo 协议/Adapter；service 侧 list/links/follow 经 DDD 门面委托。
  3. project：get_member / update_member 等旁路方法已补到 `project_app_service`
     并接入 Repo 协议/Adapter。
"""
import ast
import inspect
from pathlib import Path

import pytest

from app.domain.case_review.application.case_review_app_service import (
    case_review_app_service,
)
from app.domain.environment.application.environment_app_service import (
    environment_app_service,
)
from app.domain.project.application.project_app_service import (
    project_app_service,
)
from app.services.case_review_service import case_review_service
from app.services.environment_service import environment_service
from app.services.project_service import project_service


def _class_src(cls) -> str:
    """读取类所在文件源码。"""
    path = Path(inspect.getfile(cls))
    return path.read_text(encoding="utf-8")


def _method_src(cls, name: str) -> str:
    """从类源码提取方法源码文本。"""
    src = _class_src(cls)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls.__name__:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == name:
                    return ast.get_source_segment(src, item)
    raise AssertionError(f"方法 {name} 不在 {cls.__name__} 中")


# ═══════════════════════════════════════════════════════════════
# 一、environment：Docker 运维编排已下沉到 DDD 应用服务
# ═══════════════════════════════════════════════════════════════
class TestEnvironmentDockerSinkDown:
    @pytest.mark.parametrize("method", ["launch", "stop", "health_check", "health_check_all"])
    def test_app_service_has_methods(self, method):
        assert hasattr(environment_app_service, method)

    def test_service_delegates_launch_to_ddd(self):
        src = _method_src(environment_service.__class__, "launch")
        assert "_ddd.launch(" in src
        assert "subprocess.run" not in src

    def test_service_delegates_stop_to_ddd(self):
        src = _method_src(environment_service.__class__, "stop")
        assert "_ddd.stop(" in src
        assert "subprocess.run" not in src

    def test_service_delegates_health_check_to_ddd(self):
        src = _method_src(environment_service.__class__, "health_check")
        assert "_ddd.health_check(" in src
        assert "subprocess.run" not in src

    def test_service_delegates_health_check_all_to_ddd(self):
        src = _method_src(environment_service.__class__, "health_check_all")
        assert "_ddd.health_check_all(" in src
        assert "subprocess.run" not in src

    def test_docker_ops_infrastructure_exists(self):
        from app.domain.environment.infrastructure.docker_ops import (
            docker_available,
            launch_container,
            stop_container,
            check_container_running,
            check_http_health,
        )
        assert callable(docker_available)
        assert callable(launch_container)
        assert callable(stop_container)
        assert callable(check_container_running)
        assert callable(check_http_health)

    def test_dto_has_launch_stop_health_commands(self):
        from app.domain.environment.application.dto import (
            HealthCheckCommand,
            LaunchCommand,
            StopCommand,
        )
        assert callable(LaunchCommand)
        assert callable(StopCommand)
        assert callable(HealthCheckCommand)


# ═══════════════════════════════════════════════════════════════
# 二、case_review：聚合读方法补全（list_links / is_following）
# ═══════════════════════════════════════════════════════════════
class TestCaseReviewReadMethods:
    @pytest.mark.parametrize("method", [
        "list_reviews", "get", "get_detail", "list_links",
        "list_link_case_ids", "get_status_counts", "count_by_module",
        "toggle_follow", "is_following",
    ])
    def test_app_service_has_read_methods(self, method):
        assert hasattr(case_review_app_service, method)

    def test_repo_protocol_has_list_links(self):
        from app.domain.case_review.domain.repository import CaseReviewRepository
        # Protocol methods exist via duck typing; verify the adapter exposes it
        from app.domain.case_review.infrastructure.case_review_repository_impl import (
            case_review_repo_adapter,
        )
        assert hasattr(case_review_repo_adapter, "list_links")
        assert callable(case_review_repo_adapter.list_links)

    def test_service_list_links_delegates_to_ddd(self):
        src = _method_src(case_review_service.__class__, "list_links")
        assert "case_review_app_service.list_links" in src
        assert "CaseReviewRepo.list_links" not in src

    def test_service_is_following_delegates_to_ddd(self):
        src = _method_src(case_review_service.__class__, "is_following")
        assert "case_review_app_service.is_following" in src
        assert "CaseReviewRepo.is_following" not in src

    def test_service_toggle_follow_delegates_to_ddd(self):
        src = _method_src(case_review_service.__class__, "toggle_follow")
        assert "case_review_app_service.toggle_follow" in src
        assert "CaseReviewRepo.toggle_follow" not in src

    def test_service_list_reviews_delegates_to_ddd(self):
        src = _method_src(case_review_service.__class__, "list_reviews")
        assert "case_review_app_service.list_reviews" in src
        assert "CaseReviewRepo.list_reviews" not in src

    def test_service_get_review_detail_delegates_to_ddd(self):
        src = _method_src(case_review_service.__class__, "get_review_detail")
        assert "case_review_app_service.get_detail" in src

    def test_service_get_review_delegates_to_ddd(self):
        src = _method_src(case_review_service.__class__, "get_review")
        assert "case_review_app_service.get" in src


# ═══════════════════════════════════════════════════════════════
# 三、project：成员 CRUD 方法面补全
# ═══════════════════════════════════════════════════════════════
class TestProjectMemberMethods:
    @pytest.mark.parametrize("method", [
        "add_member", "get_member", "update_member",
        "list_members", "remove_member", "batch_remove_members",
    ])
    def test_app_service_has_member_methods(self, method):
        assert hasattr(project_app_service, method)

    def test_repo_adapter_has_member_methods(self):
        from app.domain.project.infrastructure.project_repository_impl import (
            ProjectRepoAdapter,
        )
        adapter = ProjectRepoAdapter()
        for m in ("get_member", "update_member", "batch_remove_members"):
            assert hasattr(adapter, m)
            assert callable(getattr(adapter, m))

    def test_dto_has_member_commands(self):
        from app.domain.project.application.dto import (
            GetMemberCommand,
            UpdateMemberCommand,
            BatchRemoveMembersCommand,
        )
        assert callable(GetMemberCommand)
        assert callable(UpdateMemberCommand)
        assert callable(BatchRemoveMembersCommand)

    def test_service_get_member_delegates_to_ddd(self):
        src = _method_src(project_service.__class__, "get_member")
        assert "_ddd_app.get_member" in src

    def test_service_update_member_delegates_to_ddd(self):
        src = _method_src(project_service.__class__, "update_member")
        assert "_ddd_app.update_member" in src
