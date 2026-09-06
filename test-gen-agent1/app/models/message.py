# app/models/message.py
"""消息通知 / 消息管理 Pydantic 请求体模型。"""
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class RobotSaveBody(BaseModel):
    """创建/更新项目消息机器人。

    同时收录蛇形与驼峰两种命名（前端与历史后端调用均可能携带），
    经 `model_dump(exclude_unset=True)` 导出后交由 message_repo
    create_robot / update_robot 统一按「驼峰优先、蛇形兜底」双读，
    保证不丢任何实际使用到的字段。
    """

    id: Optional[str] = Field(None, description="机器人 ID（更新时必填）")
    robotId: Optional[str] = Field(None, description="机器人 ID（前端驼峰，更新时兜底）")
    project_id: Optional[str] = Field(None, description="项目 ID")
    projectId: Optional[str] = Field(None, description="项目 ID（前端驼峰）")
    name: str = Field("", description="机器人名称")
    platform: str = Field("CUSTOM", description="平台：WE_COM/DING_TALK/LARK/CUSTOM")
    type: Optional[str] = Field("CUSTOM", description="钉钉类型：CUSTOM/ENTERPRISE")
    webhook: str = Field("", description="webhook 地址")
    app_key: Optional[str] = Field("", description="钉钉 appKey")
    appKey: Optional[str] = Field("", description="钉钉 appKey（前端驼峰）")
    app_secret: Optional[str] = Field("", description="钉钉 appSecret")
    appSecret: Optional[str] = Field("", description="钉钉 appSecret（前端驼峰）")
    enable: Optional[bool] = Field(True, description="是否启用")
    description: Optional[str] = Field("", description="描述")
    create_user: Optional[str] = Field("admin", description="创建人")
    createUser: Optional[str] = Field("admin", description="创建人（前端驼峰）")
    update_user: Optional[str] = Field("admin", description="更新人")
    updateUser: Optional[str] = Field("admin", description="更新人（前端驼峰）")

    model_config = {"extra": "allow"}


class RobotIdBody(BaseModel):
    """机器人 ID（删除 / 启停等按 ID 操作）。"""

    id: str = Field("", description="机器人 ID")
    robotId: str = Field("", description="机器人 ID（前端驼峰别名）")
    enable: Optional[bool] = Field(None, description="是否启用（启停切换时可选）")

    model_config = {"extra": "allow"}


class MessageTaskSaveBody(BaseModel):
    """保存消息设置（接收人 / 模板 / 启用）。

    字段同时收录驼峰与下划线两种命名（前端与历史后端调用均可能携带），
    经 `model_dump(exclude_unset=True)` 导出后交由 message_repo.upsert_task
    统一按「驼峰优先、下划线兜底」读取，保证不丢任何实际使用字段。
    """

    project_id: Optional[str] = Field("", description="项目 ID")
    projectId: Optional[str] = Field("", description="项目 ID（前端驼峰）")
    task_type: Optional[str] = Field("", description="任务类型")
    taskType: Optional[str] = Field("", description="任务类型（前端驼峰）")
    event: str = Field("", description="通知事件")
    robot_id: Optional[str] = Field("", description="机器人 ID")
    robotId: Optional[str] = Field("", description="机器人 ID（前端驼峰）")
    receiver_ids: Optional[List[str]] = Field([], description="接收人 ID 集合")
    receiverIds: Optional[List[str]] = Field([], description="接收人 ID 集合（前端驼峰）")
    subject: Optional[str] = Field("", description="邮件/标题")
    defaultSubject: Optional[str] = Field("", description="默认标题（保存时携带，空 subject 时兜底）")
    template: Optional[str] = Field("", description="模板内容")
    defaultTemplate: Optional[str] = Field("", description="默认模板（保存时携带，空 template 时兜底）")
    use_default_subject: Optional[bool] = Field(True, description="是否使用默认标题")
    useDefaultSubject: Optional[bool] = Field(True, description="是否使用默认标题（前端驼峰）")
    use_default_template: Optional[bool] = Field(True, description="是否使用默认模板")
    useDefaultTemplate: Optional[bool] = Field(True, description="是否使用默认模板（前端驼峰）")
    enable: Optional[bool] = Field(False, description="是否启用")

    model_config = {"extra": "allow"}


class NotificationPageQuery(BaseModel):
    """通知中心分页查询。"""

    receiver: Optional[str] = Field("", description="接收人")
    status: Optional[str] = Field("", description="UNREAD/READ")
    type: Optional[str] = Field("", description="通知类型")
    resource_type: Optional[str] = Field("", description="资源类型")
    resourceType: Optional[str] = Field("", description="资源类型（前端驼峰）")
    keyword: Optional[str] = Field("", description="关键字")
    project_id: Optional[str] = Field("", description="项目 ID")
    projectId: Optional[str] = Field("", description="项目 ID（前端驼峰）")
    current: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(10, ge=1, le=500, description="每页条数")
    page: Optional[int] = Field(None, ge=1, description="页码（旧别名，兼容历史调用）")
    page_size: Optional[int] = Field(None, description="每页条数（旧别名，兼容历史调用）")

    model_config = {"extra": "allow"}


class NotificationReadBody(BaseModel):
    """标记消息已读 / 全部已读。"""

    # 通知主键在库内以字符串十六进制存储，前端声明为 number；
    # 兼容两者，路由侧统一 str(mid) 后落库。
    ids: Optional[List[Union[int, str]]] = Field([], description="消息 ID 列表")
    resource_type: Optional[str] = Field("", description="资源类型")
    resourceType: Optional[str] = Field("", description="资源类型（前端驼峰）")
    receiver: Optional[str] = Field("", description="接收人")

    model_config = {"extra": "allow"}
