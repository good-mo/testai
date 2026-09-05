"""DDD 协调域单测：admin_system / frontend_api / functional_export / task_center / export_task。

覆盖各协调域的纯领域逻辑（聚合根实体）与应用服务全链路。
"""

import pytest

from app.domain.common.exceptions import DomainValidationError

# ═══════════════════════════════════════════════════════════
# 一、admin_system 系统管理域
# ═══════════════════════════════════════════════════════════
from app.domain.admin_system.domain.entities.org_admin import (
    OrganizationAdmin,
    ACTION_ENABLE,
    ACTION_DISABLE,
    ACTION_REMOVE_MEMBER,
)


class TestAdminSystemDomain:
    def test_requires_org_id(self):
        with pytest.raises(DomainValidationError):
            OrganizationAdmin(org_id="")

    def test_invalid_action(self):
        with pytest.raises(DomainValidationError):
            OrganizationAdmin(org_id="org1", action="invalid_action")

    def test_enable_organization(self):
        oa = OrganizationAdmin(org_id="org1", action=ACTION_DISABLE)
        oa.enable_organization()
        assert oa.action == ACTION_ENABLE
        events = oa.pull_domain_events()
        assert "AdminOrganizationEnabled" in [type(e).__name__ for e in events]

    def test_disable_organization(self):
        oa = OrganizationAdmin(org_id="org1")
        oa.disable_organization()
        events = oa.pull_domain_events()
        assert "AdminOrganizationDisabled" in [type(e).__name__ for e in events]

    def test_remove_member(self):
        oa = OrganizationAdmin(org_id="org1")
        oa.remove_member("user1")
        assert oa.user_id == "user1"
        assert oa.action == ACTION_REMOVE_MEMBER
        with pytest.raises(DomainValidationError):
            oa.remove_member("")

    def test_roundtrip(self):
        oa = OrganizationAdmin(
            org_id="org1", user_id="u1",
            action=ACTION_DISABLE, operator="admin")
        d = oa.to_dict()
        oa2 = OrganizationAdmin.from_dict(d)
        assert oa2.org_id == "org1"
        assert oa2.user_id == "u1"
        assert oa2.action == ACTION_DISABLE


# ═══════════════════════════════════════════════════════════
# 二、frontend_api 前端兼容域
# ═══════════════════════════════════════════════════════════
from app.domain.frontend_api.domain.entities.api_import import (
    ApiImport,
    SOURCE_POSTMAN,
    SOURCE_SWAGGER,
    SOURCE_AUTO,
)


class TestFrontendApiDomain:
    def test_invalid_source(self):
        with pytest.raises(DomainValidationError):
            ApiImport(source="unknown")

    def test_import_created_event(self):
        ai = ApiImport(source=SOURCE_POSTMAN, _created=True)
        events = ai.pull_domain_events()
        assert "FrontendApiImported" in [type(e).__name__ for e in events]

    def test_mark_completed(self):
        ai = ApiImport(source=SOURCE_SWAGGER)
        ai.mark_completed(imported=10, failed=2)
        assert ai.imported == 10
        assert ai.failed == 2
        assert ai.status == "done"

    def test_mark_failed(self):
        ai = ApiImport()
        ai.mark_failed(error_count=3)
        assert ai.failed == 3
        assert ai.status == "failed"

    def test_auto_generated_id(self):
        ai1 = ApiImport()
        ai2 = ApiImport()
        assert ai1.id.value != ai2.id.value

    def test_roundtrip(self):
        ai = ApiImport(source=SOURCE_POSTMAN, imported=5, failed=1)
        d = ai.to_dict()
        ai2 = ApiImport.from_dict(d)
        assert ai2.source == SOURCE_POSTMAN
        assert ai2.imported == 5
        assert ai2.failed == 1


# ═══════════════════════════════════════════════════════════
# 三、functional_export 功能导出域
# ═══════════════════════════════════════════════════════════
from app.domain.functional_export.domain.entities.case_export import (
    CaseExportJob,
    EXPORT_KIND_EXCEL,
    EXPORT_KIND_XMIND,
)


class TestFunctionalExportDomain:
    def test_invalid_kind(self):
        with pytest.raises(DomainValidationError):
            CaseExportJob(kind="invalid")

    def test_triggered_event(self):
        job = CaseExportJob(kind=EXPORT_KIND_EXCEL, _created=True)
        events = job.pull_domain_events()
        assert "CaseExportTriggered" in [type(e).__name__ for e in events]

    def test_lifecycle(self):
        job = CaseExportJob(kind=EXPORT_KIND_XMIND)
        job.mark_running()
        assert job.status == "running"
        job.mark_completed(file_id="f1", count=42)
        assert job.status == "completed"
        assert job.file_id == "f1"
        assert job.count == 42

    def test_mark_failed(self):
        job = CaseExportJob()
        job.mark_failed()
        assert job.status == "failed"

    def test_body_storage(self):
        body = {"selectAll": True, "moduleIds": ["m1"]}
        job = CaseExportJob(body=body)
        assert job.body == body

    def test_roundtrip(self):
        job = CaseExportJob(
            kind=EXPORT_KIND_EXCEL,
            file_id="f1",
            status="completed",
            count=10,
        )
        d = job.to_dict()
        job2 = CaseExportJob.from_dict(d)
        assert job2.kind == EXPORT_KIND_EXCEL
        assert job2.file_id == "f1"
        assert job2.status == "completed"
        assert job2.count == 10


# ═══════════════════════════════════════════════════════════
# 四、task_center 任务中心域
# ═══════════════════════════════════════════════════════════
from app.domain.task_center.domain.entities.task_command import (
    TaskCommand,
    OP_STOP_TASKS,
    OP_DELETE_TASKS,
    OP_RERUN_TASK,
    OP_SWITCH_SCHEDULES,
    OP_ENABLE_SCHEDULES,
    OP_DELETE_SCHEDULES,
    OP_UPDATE_CRON,
)


class TestTaskCenterDomain:
    def test_invalid_operation(self):
        with pytest.raises(DomainValidationError):
            TaskCommand(operation="invalid")

    def test_all_valid_operations(self):
        for op in (OP_STOP_TASKS, OP_DELETE_TASKS, OP_RERUN_TASK,
                   OP_SWITCH_SCHEDULES, OP_ENABLE_SCHEDULES,
                   OP_DELETE_SCHEDULES, OP_UPDATE_CRON):
            cmd = TaskCommand(operation=op)
            assert cmd.operation == op

    def test_stop_tasks_event(self):
        cmd = TaskCommand(operation=OP_STOP_TASKS, target_ids=["t1", "t2"],
                          _created=True)
        events = cmd.pull_domain_events()
        assert "TaskBatchStopped" in [type(e).__name__ for e in events]

    def test_enable_schedules_event(self):
        cmd = TaskCommand(operation=OP_ENABLE_SCHEDULES,
                          target_ids=["s1"],
                          payload={"enable": False},
                          _created=True)
        events = cmd.pull_domain_events()
        assert "ScheduleEnabledChanged" in [type(e).__name__ for e in events]

    def test_lifecycle(self):
        cmd = TaskCommand(operation=OP_DELETE_TASKS, target_ids=["t1"])
        cmd.mark_running()
        assert cmd.status == "running"
        cmd.mark_completed()
        assert cmd.status == "completed"

    def test_roundtrip(self):
        cmd = TaskCommand(
            operation=OP_UPDATE_CRON,
            target_ids=["s1"],
            payload={"cron": "*/5 * * * *"},
            status="completed",
        )
        d = cmd.to_dict()
        cmd2 = TaskCommand.from_dict(d)
        assert cmd2.operation == OP_UPDATE_CRON
        assert cmd2.target_ids == ["s1"]
        assert cmd2.payload == {"cron": "*/5 * * * *"}


# ═══════════════════════════════════════════════════════════
# 五、export_task 导出任务域（复用已有实体）
# ═══════════════════════════════════════════════════════════
from app.domain.export_task.domain.entities.export_task import ExportTask


class TestExportTaskDomain:
    def test_requires_file_id(self):
        with pytest.raises(DomainValidationError):
            ExportTask(file_id="")

    def test_mark_success(self):
        t = ExportTask(file_id="f1", _created=True)
        assert t.pull_domain_events()  # registered event
        t.mark_success(count=5)
        events = t.pull_domain_events()
        assert "ExportTaskCompleted" in [type(e).__name__ for e in events]
        assert t.count == 5

    def test_roundtrip(self):
        t = ExportTask(file_id="f1", task_id="t1", path="/tmp/f1.csv",
                       filename="f1.csv", count=10, _created=True)
        d = t.to_dict()
        t2 = ExportTask.from_dict(d)
        assert t2.id.value == "f1"
        assert t2.task_id == "t1"
        assert t2.path == "/tmp/f1.csv"
        assert t2.count == 10
