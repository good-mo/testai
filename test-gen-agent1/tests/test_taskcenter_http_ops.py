"""HTTP 层验证：task-center 操作端点不再 500，返回统一三段式信封。

（体量最大的假成功修复回归：各 scope 的 stop/delete/rerun、schedule 启停、
 update-cron、批量操作在传入不存在 id 时也稳定返回 code 且 < 500。）
"""
import pytest

_SCOPES = ["project", "system", "organization"]


def _soft(resp):
    payload = resp.json()
    assert isinstance(payload, dict)
    assert "code" in payload and "message" in payload and "data" in payload
    assert payload["code"] < 500, f"{payload.get('message')}"


@pytest.mark.parametrize("scope", _SCOPES)
def test_exec_batch_stop_delete(auth_client, scope):
    base = f"/{scope}/task-center"
    _soft(auth_client.post(f"{base}/exec-task/batch-stop", json={"selectIds": ["uim-no-task"]}))
    _soft(auth_client.post(f"{base}/exec-task/batch-delete", json={"ids": ["uim-no-task"]}))
    _soft(auth_client.post(f"{base}/exec-task/item/batch-stop", json={"taskId": "uim-no-task"}))


@pytest.mark.parametrize("scope", _SCOPES)
def test_schedule_ops(auth_client, scope):
    base = f"/{scope}/task-center"
    _soft(auth_client.post(f"{base}/schedule/batch-enable", json={"selectIds": ["uim-no-sch"]}))
    _soft(auth_client.post(f"{base}/schedule/batch-disable", json={"ids": ["uim-no-sch"]}))
    _soft(auth_client.post(f"{base}/schedule/update-cron", json={"id": "uim-no-sch", "cron": "0 0 * * *"}))


@pytest.mark.parametrize("scope", _SCOPES)
def test_exec_single_path_ops(auth_client, scope):
    base = f"/{scope}/task-center"
    _soft(auth_client.get(f"{base}/exec-task/stop/uim-no-task"))
    _soft(auth_client.get(f"{base}/exec-task/delete/uim-no-task"))
    _soft(auth_client.get(f"{base}/exec-task/rerun/uim-no-task"))
    _soft(auth_client.get(f"{base}/schedule/switch/uim-no-sch"))
    _soft(auth_client.get(f"{base}/schedule/delete/uim-no-sch"))
