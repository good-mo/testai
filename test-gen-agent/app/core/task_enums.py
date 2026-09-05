# app/core/task_enums.py
"""任务/报告输出枚举 —— 前后端共享的「权威单一事实源」。

背景
====
此前 Report / TaskCenter 兼容层把同一字段塞进多套互不相认的值域：
  - 报告条目的 ``status`` 被填成执行结果（SUCCESS/ERROR），
    而前端 ``executeStatusMap`` 期望执行状态（PENDING/RUNNING/...）；
  - 真实任务（app/tasks/manager.py）内部用小写生命周期状态
    （pending/running/success/failed/cancelled）直接暴露，前端查不到大写 key；
  - ``triggerMode`` 在任务中心列表缺失，前端拿到 undefined。

本模块把对外输出统一收敛到大写权威值域，并在序列化边界提供归一化函数，
让「前端查不到 key」这类问题在数据源头消失，而不再依赖前端一层层 fallback。
值域与 frontend/src/enums/taskCenter.ts / views/taskCenter/component/config.ts 对齐。
"""

from __future__ import annotations

from typing import Any, Dict

# ── 执行状态（生命周期）：对应前端 ExecuteStatusEnum / executeStatusMap ──
EXEC_STATUS_PENDING = "PENDING"          # 待执行
EXEC_STATUS_RUNNING = "RUNNING"          # 执行中
EXEC_STATUS_COMPLETED = "COMPLETED"      # 执行完成
EXEC_STATUS_RERUNNING = "RERUNNING"      # 失败重跑
EXEC_STATUS_STOPPED = "STOPPED"          # 执行中止

# ── 执行结果：对应前端 ExecuteResultEnum / executeResultMap ──
EXEC_RESULT_SUCCESS = "SUCCESS"
EXEC_RESULT_ERROR = "ERROR"
EXEC_RESULT_FAKE_ERROR = "FAKE_ERROR"

# ── 触发方式：对应前端 ExecuteTriggerMode / executeMethodMap ──
TRIGGER_MODE_MANUAL = "MANUAL"   # 手动执行
TRIGGER_MODE_BATCH = "BATCH"     # 批量执行
TRIGGER_MODE_API = "API"         # 接口调用
TRIGGER_MODE_SCHEDULE = "SCHEDULE"  # 定时任务

# 合法值集合（供契约断言使用）
EXEC_STATUS_SET = frozenset({
    EXEC_STATUS_PENDING,
    EXEC_STATUS_RUNNING,
    EXEC_STATUS_COMPLETED,
    EXEC_STATUS_RERUNNING,
    EXEC_STATUS_STOPPED,
})
EXEC_RESULT_SET = frozenset({
    EXEC_RESULT_SUCCESS,
    EXEC_RESULT_ERROR,
    EXEC_RESULT_FAKE_ERROR,
})
TRIGGER_MODE_SET = frozenset({
    TRIGGER_MODE_MANUAL,
    TRIGGER_MODE_BATCH,
    TRIGGER_MODE_API,
    TRIGGER_MODE_SCHEDULE,
})

# app/tasks/manager.py 内部生命周期小写状态 → 权威大写执行状态
# （failed/cancelled 已执行结束，生命周期上视为 COMPLETED/STOPPED；
#   真正的成败/取消由 result / 其它字段表达，不污染 status 的执行状态语义）
_INTERNAL_STATUS_TO_EXEC_STATUS: Dict[str, str] = {
    "pending": EXEC_STATUS_PENDING,
    "running": EXEC_STATUS_RUNNING,
    "success": EXEC_STATUS_COMPLETED,
    "completed": EXEC_STATUS_COMPLETED,
    "failed": EXEC_STATUS_COMPLETED,
    "error": EXEC_STATUS_COMPLETED,
    "cancelled": EXEC_STATUS_STOPPED,
    "stopped": EXEC_STATUS_STOPPED,
    "rerunning": EXEC_STATUS_RERUNNING,
}

# 缺省值：未知状态收敛到 PENDING，未知触发方式收敛到 MANUAL（保持前向兼容）
_DEFAULT_STATUS = EXEC_STATUS_PENDING
_DEFAULT_TRIGGER_MODE = TRIGGER_MODE_MANUAL


def normalize_status(status: Any) -> str:
    """把任意来源的 status 值归一为权威执行状态枚举。

    兼容：
      - 已是大写执行状态（原样返回，但会校验拼写，非法统一 PENDING）
      - manager 内部小写生命周期（pending/running/success/failed/cancelled...）
      - 历史遗留的执行结果（SUCCESS/ERROR）按已执行结束映射为 COMPLETED
      - None / 空 / 未知 → PENDING
    """
    if isinstance(status, str):
        key = status.strip().lower()
        if key in EXEC_STATUS_SET_LOOKUP_LOWER:
            return EXEC_STATUS_SET_LOOKUP_LOWER[key]
        mapped = _INTERNAL_STATUS_TO_EXEC_STATUS.get(key)
        if mapped:
            return mapped
        # 历史遗留把执行结果塞进 status：视为执行已完成
        if key in _EXEC_RESULT_LOOKUP_LOWER:
            return EXEC_STATUS_COMPLETED
    return _DEFAULT_STATUS


def normalize_exec_result(result: Any) -> str:
    """把任意来源的结果值归一为权威执行结果枚举。

    兼容小写 success/error/fake_error / failed/cancelled（失败语义归 ERROR）。
    """
    if isinstance(result, str):
        key = result.strip().lower()
        if key in _EXEC_RESULT_LOOKUP_LOWER:
            return _EXEC_RESULT_LOOKUP_LOWER[key]
        if key in {"failed", "cancelled", "stop", "stopped"}:
            return EXEC_RESULT_ERROR
    return EXEC_RESULT_SUCCESS


def normalize_trigger_mode(trigger: Any) -> str:
    """把任意来源的触发方式值归一为权威触发方式枚举。

    兼容：
      - 大写权威值（MANUAL/BATCH/API/SCHEDULE）
      - 缺失/未知 → MANUAL
    """
    if isinstance(trigger, str):
        key = trigger.strip().upper()
        if key in TRIGGER_MODE_SET:
            return key
    return _DEFAULT_TRIGGER_MODE


def is_exec_status(value: Any) -> bool:
    """判断 value 是否为权威执行状态枚举成员（契约断言用）。"""
    return isinstance(value, str) and value in EXEC_STATUS_SET


def is_exec_result(value: Any) -> bool:
    """判断 value 是否为权威执行结果枚举成员（契约断言用）。"""
    return isinstance(value, str) and value in EXEC_RESULT_SET


def is_trigger_mode(value: Any) -> bool:
    """判断 value 是否为权威触发方式枚举成员（契约断言用）。"""
    return isinstance(value, str) and value in TRIGGER_MODE_SET


# 小写查表（模块加载期构建，避免每次 strip 后逐项遍历）
EXEC_STATUS_SET_LOOKUP_LOWER: Dict[str, str] = {v.lower(): v for v in EXEC_STATUS_SET}
_EXEC_RESULT_LOOKUP_LOWER: Dict[str, str] = {v.lower(): v for v in EXEC_RESULT_SET}
TRIGGER_MODE_LOOKUP_LOWER: Dict[str, str] = {v.lower(): v for v in TRIGGER_MODE_SET}


# ════════════════════════════════════════════════════════════════════════════
# 报告步骤 / 后台定时任务类型 —— 前端渲染值域（契约用）
#
# 背景
# ====
# 前端的报告步骤渲染依赖各自本地字典：
#   - stepStatus.vue / statusMap：报告步骤状态
#   - conditionStatus.vue / scenarioStepMap：场景报告步骤类型
#   - systemTaskTable.vue / scheduleTaskTypeMap：后台定时任务类型
# 若后端在这些字段上输出字典之外的值，前端会直接 undefined.label 崩溃，
# 或渲染出 undefined 文本。下面统一收敛到前端可识别的大写值域。
# 值域与 frontend/src/enums/apiEnum.ts 的 ScenarioStepType、
# frontend/src/views/api-test/report/component/step/stepStatus.vue、
# frontend/src/views/taskCenter/component/config.ts 对齐。
# ────────────────────────────────────────────────────────────────────────────

# ── 报告步骤状态：前端 statusMap 可识别（执行结果 + 执行生命周期）──
REPORT_STEP_STATUS_SET = frozenset({
    EXEC_STATUS_PENDING,      # PENDING
    EXEC_STATUS_RUNNING,      # RUNNING
    EXEC_STATUS_COMPLETED,    # COMPLETED
    EXEC_STATUS_RERUNNING,    # RERUNNING
    EXEC_STATUS_STOPPED,      # STOPPED
    EXEC_RESULT_SUCCESS,      # SUCCESS
    EXEC_RESULT_ERROR,        # ERROR
    EXEC_RESULT_FAKE_ERROR,   # FAKE_ERROR
})

# 缺省报告步骤状态（未执行）
_DEFAULT_REPORT_STEP_STATUS = EXEC_STATUS_PENDING

# ── 报告步骤类型：前端 scenarioStepMap 可识别（ScenarioStepType 子集）──
REPORT_STEP_TYPE_API = "API"
REPORT_STEP_TYPE_API_CASE = "API_CASE"
REPORT_STEP_TYPE_API_SCENARIO = "API_SCENARIO"
REPORT_STEP_TYPE_CUSTOM_REQUEST = "CUSTOM_REQUEST"
REPORT_STEP_TYPE_SCRIPT = "SCRIPT"
REPORT_STEP_TYPE_LOOP_CONTROLLER = "LOOP_CONTROLLER"
REPORT_STEP_TYPE_IF_CONTROLLER = "IF_CONTROLLER"
REPORT_STEP_TYPE_ONCE_ONLY_CONTROLLER = "ONCE_ONLY_CONTROLLER"
REPORT_STEP_TYPE_CONSTANT_TIMER = "CONSTANT_TIMER"

REPORT_STEP_TYPE_SET = frozenset({
    REPORT_STEP_TYPE_API,
    REPORT_STEP_TYPE_API_CASE,
    REPORT_STEP_TYPE_API_SCENARIO,
    REPORT_STEP_TYPE_CUSTOM_REQUEST,
    REPORT_STEP_TYPE_SCRIPT,
    REPORT_STEP_TYPE_LOOP_CONTROLLER,
    REPORT_STEP_TYPE_IF_CONTROLLER,
    REPORT_STEP_TYPE_ONCE_ONLY_CONTROLLER,
    REPORT_STEP_TYPE_CONSTANT_TIMER,
})

# 缺省报告步骤类型（前端按 API 接口展示）
_DEFAULT_REPORT_STEP_TYPE = REPORT_STEP_TYPE_API

# ── 后台定时任务类型：前端 scheduleTaskTypeMap 可识别 ──
SCHEDULE_RESOURCE_TYPE_SET = frozenset({
    "API_IMPORT",
    "API_SCENARIO",
    "BUG_SYNC",
    "DEMAND_SYNC",
    "TEST_PLAN",
    "TEST_PLAN_GROUP",
})
_DEFAULT_SCHEDULE_RESOURCE_TYPE = "API_IMPORT"


def normalize_report_step_status(status: Any) -> str:
    """把任意来源的报告步骤状态值归一为前端可识别的步骤状态。

    兼容执行结果（SUCCESS/ERROR/FAKE_ERROR）与执行生命周期
    （PENDING/RUNNING/COMPLETED/RERUNNING/STOPPED），未知/空值 → PENDING。
    """
    if isinstance(status, str):
        key = status.strip().upper()
        if key in REPORT_STEP_STATUS_SET:
            return key
        # 小写内部生命周期 → 权威执行状态
        mapped = _INTERNAL_STATUS_TO_EXEC_STATUS.get(status.strip().lower())
        if mapped:
            return mapped
    return _DEFAULT_REPORT_STEP_STATUS


def normalize_report_step_type(step_type: Any) -> str:
    """把任意来源的报告步骤类型归一为前端 scenarioStepMap 可识别的值。

    未知/空值统一回退为 API（前端按「接口」样式展示，避免未映射类型崩溃）。
    """
    if isinstance(step_type, str):
        key = step_type.strip().upper()
        if key in REPORT_STEP_TYPE_SET:
            return key
    return _DEFAULT_REPORT_STEP_TYPE


def is_report_step_status(value: Any) -> bool:
    return isinstance(value, str) and value in REPORT_STEP_STATUS_SET


def is_report_step_type(value: Any) -> bool:
    return isinstance(value, str) and value in REPORT_STEP_TYPE_SET


def is_schedule_resource_type(value: Any) -> bool:
    return isinstance(value, str) and value in SCHEDULE_RESOURCE_TYPE_SET

