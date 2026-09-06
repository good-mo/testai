# TestPilot v3.x Backend 接口逐字段深挖报告

> 分析对象：`https://github.com/metersphere/metersphere/tree/v3.x/backend`
> 分析范围：全部 6 大业务模块、108 个 Controller、1007 个接口方法
> 每个接口均包含：请求路径、请求方式、逐字段入参详解、返回值类型

> 生成时间：2026-09-01 20:28:34

## 模块概览

| 模块 | Controller 数 | 接口方法数 | DTO 类数 |
|------|:---:|:---:|:---:|
| **api-test** | 20 | 237 | 193 |
| **case-management** | 15 | 127 | 42 |
| **bug-management** | 6 | 50 | 34 |
| **test-plan** | 13 | 143 | 113 |
| **project-management** | 22 | 173 | 87 |
| **system-setting** | 32 | 277 | 155 |

## api-test 模块

共 20 个 Controller，237 个接口


### ApiExecuteResourceController
**业务标签**: 接口测试-执行-资源

#### **`PostMapping /api/execute/resource/script`** — 获取执行脚本

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `GetRunScriptRequest` | Body |

**返回值**: `GetRunScriptResult`

#### **`PostMapping /api/execute/resource/file`** — 下载执行所需的文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskItemId` | `String` | Query |
| `fileRequest` | `FileRequest` | Body |
| `response` | `HttpServletResponse` | 参数 |

**返回值**: `void`


### ApiReportShareController
**业务标签**: 接口测试-接口报告-分享

#### **`PostMapping /api/report/share/gen`** — 接口测试-接口报告-生成分享链接

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiReportShareRequest` | Body |

**ApiReportShareRequest 字段明细**:
  - `shareType`: `String` 分享类型 资源的类型 Single, Batch, API_SHARE_REPORT, TEST_PLAN_SHARE_REPORT
  - `lang`: `String` 语言
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{share_info.project_id.length_range}", groups = {Created.class, Updated.class});*
  - `reportId`: `String` **[必填]** 分享扩展数据 资源的id

**返回值**: `ShareInfoDTO`

#### **`GetMapping /api/report/share/get/{id}`** — 接口测试-接口报告-获取分享链接

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiReportShareDTO`

#### **`GetMapping /api/report/share/get-share-time/{id}`** — 接口测试-接口报告-获取分享链接的有效时间

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `String`


### ApiTaskCenterController
**业务标签**: 任务中心-实时任务-接口用例/场景

#### **`PostMapping /task/center/api/project/real-time/page`** — 项目-任务中心-接口用例/场景-实时任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterPageRequest` | Body |

**返回值**: `Pager<List<TaskCenterDTO>>`

#### **`PostMapping /task/center/api/org/real-time/page`** — 组织-任务中心-接口用例/场景-实时任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterPageRequest` | Body |

**返回值**: `Pager<List<TaskCenterDTO>>`

#### **`PostMapping /task/center/api/system/real-time/page`** — 系统-任务中心-接口用例/场景-实时任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterPageRequest` | Body |

**返回值**: `Pager<List<TaskCenterDTO>>`

#### **`PostMapping /task/center/api/system/stop`** — 系统-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/api/org/stop`** — 组织-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/api/project/stop`** — 项目-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterBatchRequest` | Body |

**返回值**: `void`

#### **`GetMapping /task/center/api/project/stop/{moduleType}/{id}`** — 项目-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /task/center/api/org/stop/{moduleType}/{id}`** — 组织-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /task/center/api/system/stop/{moduleType}/{id}`** — 系统-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`


### ApiTestController
**业务标签**: 接口测试

#### **`GetMapping /api/test/protocol/{organizationId}`** — 获取协议插件的的协议列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `List<ProtocolDTO>`

#### **`PostMapping /api/test/mock`** — 获取mock数据

| 参数 | 类型 | 来源 |
|------|------|------|
| `key` | `TextNode` | Body |

**返回值**: `String`

#### **`PostMapping /api/test/custom/func/run`** — 项目管理-公共脚本-脚本测试

| 参数 | 类型 | 来源 |
|------|------|------|
| `runRequest` | `CustomFunctionRunRequest` | Body |

**CustomFunctionRunRequest 字段明细**:
  - `type`: `String` **[必填]** 脚本语言类型 *约束: @Size(max = 50);*
  - `reportId`: `String` **[必填]** 报告ID *约束: @Size(max = 50);*
  - `params`: `List<KeyValueParam>` 参数列表
  - `script`: `String` **[必填]** 函数体
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(max = 50);*

**返回值**: `TaskRequestDTO`

#### **`GetMapping /api/test/plugin/script/{pluginId}`** — 获取协议插件的的协议列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `pluginId` | `String` | 路径 |

**返回值**: `Object`

#### **`PostMapping /api/test/plugin/form/option`** — 接口测试-获取插件表单选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestPluginOptionRequest` | Body |

**ApiTestPluginOptionRequest 字段明细**:
  - `orgId`: `String` **[必填]** *约束: @Size(max = 50);*
  - `pluginId`: `String` **[必填]** *约束: @Size(max = 50);*
  - `optionMethod`: `String` **[必填]** *约束: @Size(max = 100);*
  - `queryParam`: `Object`

**返回值**: `List<ApiPluginSelectOption>`

#### **`GetMapping /api/test/env-list/{projectId}`** — 接口测试-环境列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<Environment>`

#### **`GetMapping /api/test/environment/{environmentId}`** — 接口测试-获取环境中数据源等参数

| 参数 | 类型 | 来源 |
|------|------|------|
| `environmentId` | `String` | 路径 |

**返回值**: `EnvironmentConfig`

#### **`GetMapping /api/test/pool-option/{projectId}`** — 接口测试-获取资源池

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<TestResourcePool>`

#### **`GetMapping /api/test/get-pool/{projectId}`** — 接口测试-获取资源池

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `String`

#### **`PostMapping /api/test/download`** — 执行结果附件下载

| 参数 | 类型 | 来源 |
|------|------|------|
| `path` | `TextNode` | Body |
| `response` | `HttpServletResponse` | 参数 |

**返回值**: `void`

#### **`GetMapping /api/test/common-script/{scriptId}`** — 获取最新的公共脚本信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `scriptId` | `String` | 路径 |

**返回值**: `CommonScriptInfo`


### ApiDebugController
**业务标签**: 接口调试

#### **`GetMapping /api/debug/list/{protocol}`** — 获取接口调试列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `protocol` | `String` | 路径 |

**返回值**: `List<ApiDebugSimpleDTO>`

#### **`GetMapping /api/debug/get/{id}`** — 获取接口调试详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiDebugDTO`

#### **`PostMapping /api/debug/add`** — 创建接口调试

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDebugAddRequest` | Body |

**ApiDebugAddRequest 字段明细**:
  - `name`: `String` **[必填]** 接口名称 *约束: @Size(min = 1, max = 255, message = "{api_debug.name.length_range}");*
  - `protocol`: `String` **[必填]** 接口协议 *约束: @Size(min = 1, max = 20, message = "{api_debug.protocol.length_range}");*
  - `method`: `String` http协议类型post/get/其它协议则是协议名(mqtt) *约束: @Size(min = 1, max = 20, message = "{api_debug.method.length_range}");*
  - `path`: `String` http协议url/其它协议则为空 *约束: @Size(max = 500, message = "{api_debug.path.length_range}");*
  - `projectId`: `String` **[必填]** 项目fk *约束: @Size(min = 1, max = 50, message = "{api_debug.project_id.length_range}");*
  - `moduleId`: `String` **[必填]** 模块fk *约束: @Size(min = 1, max = 50, message = "{api_debug.module_id.length_range}");*
  - `request`: `Object` **[必填]** 请求内容
  - `uploadFileIds`: `List<String>` 新上传的文件ID
  - `linkFileIds`: `List<String>` 关联文件ID

**返回值**: `ApiDebug`

#### **`PostMapping /api/debug/upload/temp/file`** — 上传接口调试所需的文件资源，并返回文件ID

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`PostMapping /api/debug/update`** — 更新接口调试

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDebugUpdateRequest` | Body |

**ApiDebugUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 接口pk *约束: @Size(max = 50, message = "{api_debug.id.length_range}");*
  - `name`: `String` 接口名称 *约束: @Size(min = 1, max = 255, message = "{api_debug.name.length_range}");*
  - `method`: `String` http协议类型post/get/其它协议则是协议名(mqtt) *约束: @Size(min = 1, max = 20, message = "{api_debug.method.length_range}");*
  - `path`: `String` http协议路径/其它协议则为空 *约束: @Size(max = 500, message = "{api_debug.path.length_range}");*
  - `moduleId`: `String` 模块fk *约束: @Size(min = 1, max = 50, message = "{api_debug.module_id.length_range}");*
  - `request`: `Object` 请求内容
  - `uploadFileIds`: `List<String>` 新上传的文件ID
  - `linkFileIds`: `List<String>` 关联文件ID
  - `deleteFileIds`: `List<String>` 删除的文件ID
  - `unLinkFileIds`: `List<String>` 取消关联文件ID

**返回值**: `ApiDebug`

#### **`GetMapping /api/debug/delete/{id}`** — 删除接口调试

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/debug/debug`** — 运行接口调试

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDebugRunRequest` | Body |

**ApiDebugRunRequest 字段明细**:
  - `id`: `String` **[必填]** 接口ID
  - `reportId`: `String` 报告ID，传了可以实时获取结果，不传则不支持实时获取
  - `uploadFileIds`: `List<String>` 新上传的文件ID
  - `linkFileIds`: `List<String>` 关联文件ID
  - `request`: `Object` **[必填]** 请求内容
  - `projectId`: `String` 项目ID

**返回值**: `TaskRequestDTO`

#### **`PostMapping /api/debug/edit/pos`** — 接口调试-拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiEditPosRequest` | Body |

**ApiEditPosRequest 字段明细**:
  > **继承**: `PosRequest`
  - `moduleId`: `String` 模块id  模块树列表拖拽的时候 这个字段必传 ,其他情况不传

**返回值**: `void`

#### **`PostMapping /api/debug/transfer`** — 接口测试-接口调试-附件-文件转存

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTransferRequest` | Body |

**ApiTransferRequest 字段明细**:
  > **继承**: `ApiFileRequest`
  - `moduleId`: `String` **[必填]** 转存的模块id
  - `originalName`: `String` **[必填]** 原始文件名

**返回值**: `String`

#### **`GetMapping /api/debug/transfer/options/{projectId}`** — 接口测试-接口调试-附件-转存目录下拉框

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/debug/import-curl`** — 接口测试-接口调试-导入curl

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiImportCurlRequest` | Body |

**ApiImportCurlRequest 字段明细**:
  - `curl`: `String` curl字符串

**返回值**: `CurlEntity`

#### **`PostMapping /api/debug/file/copy`** — 接口测试-接口调试-另存时, 复制文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiFileCopyRequest` | Body |

**ApiFileCopyRequest 字段明细**:
  - `resourceId`: `String` **[必填]** 资源id
  - `fileIds`: `List<String>` **[必填]** 文件数组

**返回值**: `Map<String, String>`


### ApiDebugModuleController
**业务标签**: 接口测试-接口调试-模块

#### **`GetMapping /api/debug/module/tree`** — 接口测试-接口调试-模块-查找模块

**无入参**

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/debug/module/add`** — 接口测试-接口调试-模块-添加模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ModuleCreateRequest` | Body |

**ModuleCreateRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_debug.project_id.length_range}");*
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{api_debug_module.name.length_range}");*

**返回值**: `String`

#### **`PostMapping /api/debug/module/update`** — 接口测试-接口调试-模块-修改模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ModuleUpdateRequest` | Body |

**ModuleUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 模块ID *约束: @Size(min = 1, max = 50, message = "{api_debug_module.id.length_range}");*
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{api_debug_module.name.length_range}");*

**返回值**: `boolean`

#### **`GetMapping /api/debug/module/delete/{deleteId}`** — 接口测试-接口调试-模块-删除模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `deleteId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/debug/module/move`** — 接口测试-接口调试-模块-移动模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `NodeMoveRequest` | Body |

**NodeMoveRequest 字段明细**:
  - `dragNodeId`: `String` **[必填]** 被拖拽的节点
  - `dropNodeId`: `String` **[必填]** 放入的节点
  - `dropPosition`: `int` 放入的位置（取值：-1，,1。  -1：dropNodeId节点之前。 1：dropNodeId节点后）

**返回值**: `void`

#### **`PostMapping /api/debug/module/count`** — 接口测试-接口调试-模块-统计模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDebugRequest` | Body |

**ApiDebugRequest 字段明细**:
  - `keyword`: `String` 关键字

**返回值**: `Map<String, Long>`


### ApiDefinitionController
**业务标签**: 接口测试-接口管理-接口定义

#### **`GetMapping /api/definition/rage/{projectId}`** — 接口测试-接口管理-接口列表(deleted 状态为 1 时为回收站数据)

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `ApiCoverageDTO`

#### **`PostMapping /api/definition/add`** — 接口测试-接口管理-添加接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionAddRequest` | Body |

**ApiDefinitionAddRequest 字段明细**:
  - `name`: `String` **[必填]** 接口名称 *约束: @Size(min = 1, max = 255, message = "{api_definition.name.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `method`: `String` http协议类型post/get/其它协议则是协议名(mqtt) *约束: @Size(max = 20, message = "{api_debug.method.length_range}");*
  - `path`: `String` http协议路径/其它协议则为空 *约束: @Size(max = 500, message = "{api_debug.path.length_range}");*
  - `status`: `String` **[必填]** 接口状态/进行中/已完成 *约束: @Size(min = 1, max = 50, message = "{api_definition.status.length_range}"); @EnumValue(enumClass = ApiDefinitionStatus.class);*
  - `moduleId`: `String` **[必填]** 模块fk *约束: @Size(min = 1, max = 50, message = "{api_definition.module_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `description`: `String` 描述 *约束: @Size(max = 1000, message = "{api_definition.description.length_range}");*
  - `request`: `Object` **[必填]** 请求内容
  - `response`: `List<HttpResponse>` **[必填]** 响应内容 *约束: @Valid;*
  - `uploadFileIds`: `List<String>` 新上传的文件ID
  - `linkFileIds`: `List<String>` 关联文件ID
  - `customFields`: `List<ApiDefinitionCustomField>` 自定义字段集合

**返回值**: `ApiDefinition`

#### **`PostMapping /api/definition/update`** — 接口测试-接口管理-更新接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionUpdateRequest` | Body |

**ApiDefinitionUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 接口pk *约束: @Size(min = 1, max = 50, message = "{api_definition.id.length_range}");*
  - `name`: `String` 接口名称 *约束: @Size(min = 1, max = 255, message = "{api_definition.name.length_range}");*
  - `method`: `String` http协议类型post/get/其它协议则是协议名(mqtt) *约束: @Size(max = 20, message = "{api_debug.method.length_range}");*
  - `path`: `String` http协议路径/其它协议则为空 *约束: @Size(max = 500, message = "{api_debug.path.length_range}");*
  - `status`: `String` 接口状态/进行中/已完成 *约束: @Size(min = 1, max = 50, message = "{api_definition.status.length_range}"); @EnumValue(enumClass = ApiDefinitionStatus.class);*
  - `moduleId`: `String` 模块fk *约束: @Size(min = 1, max = 50, message = "{api_definition.module_id.length_range}");*
  - `description`: `String` 描述 *约束: @Size(max = 1000, message = "{api_definition.description.length_range}");*
  - `request`: `Object` 请求内容
  - `response`: `List<HttpResponse>` 响应内容 *约束: @Valid;*
  - `uploadFileIds`: `List<String>` 新上传的文件ID
  - `linkFileIds`: `List<String>` 关联文件ID
  - `customFields`: `List<ApiDefinitionCustomField>` 自定义字段集合
  - `deleteFileIds`: `List<String>` 删除的文件ID
  - `unLinkFileIds`: `List<String>` 取消关联文件ID

**返回值**: `ApiDefinition`

#### **`PostMapping /api/definition/batch-update`** — 接口测试-接口管理-批量更新接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionBatchUpdateRequest` | Body |

**ApiDefinitionBatchUpdateRequest 字段明细**:
  > **继承**: `ApiDefinitionBatchRequest`
  - `type`: `String` 所需更新的字段名
  - `method`: `String` http协议类型post/get/其它协议则是协议名(mqtt)
  - `status`: `String` 接口状态/进行中/已完成 *约束: @Size(min = 1, max = 50, message = "{api_definition.status.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(min = 1, max = 50, message = "{api_definition.version_id.length_range}");*
  - `customField`: `ApiDefinitionCustomFieldDTO` 自定义字段

**返回值**: `void`

#### **`PostMapping /api/definition/file/copy`** — 接口测试-接口管理-复制接口时，复制文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiFileCopyRequest` | Body |

**ApiFileCopyRequest 字段明细**:
  - `resourceId`: `String` **[必填]** 资源id
  - `fileIds`: `List<String>` **[必填]** 文件数组

**返回值**: `Map<String, String>`

#### **`PostMapping /api/definition/copy`** — 接口测试-接口管理-复制接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionCopyRequest` | Body |

**ApiDefinitionCopyRequest 字段明细**:
  - `id`: `String` **[必填]** 接口pk *约束: @Size(min = 1, max = 50, message = "{api_definition.id.length_range}");*

**返回值**: `ApiDefinition`

#### **`PostMapping /api/definition/batch-move`** — 接口测试-接口管理-批量移动接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionBatchMoveRequest` | Body |

**ApiDefinitionBatchMoveRequest 字段明细**:
  > **继承**: `ApiDefinitionBatchRequest`
  - `moduleId`: `String` 模块ID *约束: @Size(max = 50, message = "{api_definition.module_id.length_range}");*

**返回值**: `void`

#### **`GetMapping /api/definition/version/{id}`** — 接口测试-接口管理-版本信息(接口是否存在多版本)

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `List<ApiDefinitionVersionDTO>`

#### **`GetMapping /api/definition/get-detail/{id}`** — 接口测试-接口管理-获取接口详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiDefinitionDTO`

#### **`GetMapping /api/definition/follow/{id}`** — 接口测试-接口管理-关注/取消关注用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/definition/page`** — 接口测试-接口管理-接口列表(deleted 状态为 1 时为回收站数据)

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionPageRequest` | Body |

**ApiDefinitionPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `id`: `String` 接口pk *约束: @Size(min = 1, max = 50, message = "{api_definition.id.length_range}");*
  - `name`: `String` 接口名称 *约束: @Size(min = 1, max = 255, message = "{api_definition.name.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(min = 1, max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(min = 1, max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `Pager<List<ApiDefinitionDTO>>`

#### **`GetMapping /api/definition/delete-to-gc/{id}`** — 接口测试-接口管理-删除接口定义到回收站

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `deleteAllVersion` | `boolean` | Query |

**返回值**: `void`

#### **`PostMapping /api/definition/batch/delete-to-gc`** — 接口测试-接口管理-批量删除接口定义到回收站

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionBatchDeleteRequest` | Body |

**返回值**: `void`

#### **`GetMapping /api/definition/delete/{id}`** — 接口测试-接口管理-删除回收站接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/definition/batch/delete`** — 接口测试-接口管理-批量从回收站删除接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionBatchRequest` | Body |

**ApiDefinitionBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/definition/recover`** — 接口测试-接口管理-恢复回收站接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionDeleteRequest` | Body |

**ApiDefinitionDeleteRequest 字段明细**:
  - `id`: `String` **[必填]** 接口pk *约束: @Size(min = 1, max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/definition/batch-recover`** — 接口测试-接口管理-批量从回收站恢复接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionBatchRequest` | Body |

**ApiDefinitionBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/definition/page-doc`** — 接口测试-接口管理-接口文档列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionPageRequest` | Body |

**ApiDefinitionPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `id`: `String` 接口pk *约束: @Size(min = 1, max = 50, message = "{api_definition.id.length_range}");*
  - `name`: `String` 接口名称 *约束: @Size(min = 1, max = 255, message = "{api_definition.name.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(min = 1, max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(min = 1, max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `Pager<List<ApiDefinitionDTO>>`

#### **`PostMapping /api/definition/upload/temp/file`** — 上传接口定义所需的文件资源，并返回文件ID

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`PostMapping /api/definition/doc`** — 接口测试-接口管理-接口文档列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionDocRequest` | Body |

**ApiDefinitionDocRequest 字段明细**:
  - `keyword`: `String` 关键字
  - `apiId`: `String` 接口pk *约束: @Size(min = 1, max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `type`: `String` 类型(ALL,MODULE,API)
  - `versionId`: `String` 版本fk *约束: @Size(min = 1, max = 50, message = "{api_definition.version_id.length_range}");*

**返回值**: `ApiDefinitionDocDTO`

#### **`PostMapping /api/definition/import`** — 接口测试-接口管理-导入接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |
| `request` | `ImportRequest` | Form |

**返回值**: `void`

#### **`PostMapping /api/definition/operation-history`** — 接口测试-接口管理-接口变更历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OperationHistoryRequest` | Body |

**OperationHistoryRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{operation_history.project_id.length_range}");*
  - `sourceId`: `String` **[必填]** 资源id
  - `createUser`: `String` 操作人
  - `types`: `List<String>` 操作类型
  - `modules`: `String` 操作模块

**返回值**: `Pager<List<OperationHistoryDTO>>`

#### **`PostMapping /api/definition/operation-history/recover`** — 接口测试-接口管理-接口变更历史恢复

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OperationHistoryVersionRequest` | Body |

**OperationHistoryVersionRequest 字段明细**:
  - `id`: `Long` **[必填]** 变更记录id
  - `sourceId`: `String` **[必填]** 资源id（当前变更记录的资源id）
  - `versionId`: `String` **[必填]** 版本id *约束: @Size(min = 1, max = 50, message = "{operation_history.version_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/definition/operation-history/save`** — 接口测试-接口管理-另存变更历史为指定版本

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OperationHistoryVersionRequest` | Body |

**OperationHistoryVersionRequest 字段明细**:
  - `id`: `Long` **[必填]** 变更记录id
  - `sourceId`: `String` **[必填]** 资源id（当前变更记录的资源id）
  - `versionId`: `String` **[必填]** 版本id *约束: @Size(min = 1, max = 50, message = "{operation_history.version_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/definition/edit/pos`** — 接口测试-接口管理-接口-拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiEditPosRequest` | Body |

**ApiEditPosRequest 字段明细**:
  > **继承**: `PosRequest`
  - `moduleId`: `String` 模块id  模块树列表拖拽的时候 这个字段必传 ,其他情况不传

**返回值**: `void`

#### **`GetMapping /api/definition/transfer/options/{projectId}`** — 接口测试-接口管理-接口-附件-转存目录下拉框

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/definition/transfer`** — 接口测试-接口管理-接口-附件-文件转存

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTransferRequest` | Body |

**ApiTransferRequest 字段明细**:
  > **继承**: `ApiFileRequest`
  - `moduleId`: `String` **[必填]** 转存的模块id
  - `originalName`: `String` **[必填]** 原始文件名

**返回值**: `String`

#### **`PostMapping /api/definition/json-schema/preview`** — 接口测试-接口管理-接口-json-schema-预览

| 参数 | 类型 | 来源 |
|------|------|------|
| `jsonSchemaItem` | `JsonSchemaItem` | Body |

**JsonSchemaItem 字段明细**:
  - `id`: `String`
  - `title`: `String`
  - `example`: `String`
  - `description`: `String`
  - `items`: `List<JsonSchemaItem>` *约束: @Valid;*
  - `properties`: `Map<String, JsonSchemaItem>`
  - `additionalProperties`: `JsonSchemaItem`
  - `required`: `List<String>`
  - `defaultValue`: `Object`
  - `pattern`: `String`
  - `maxLength`: `Integer`
  - `minLength`: `Integer`
  - `minimum`: `BigDecimal`
  - `maximum`: `BigDecimal`
  - `maxItems`: `Integer`
  - `minItems`: `Integer`
  - `format`: `String`
  - `enumValues`: `List<String>`
  - `value`: `String`

**返回值**: `String`

#### **`PostMapping /api/definition/json-schema/auto-generate`** — 接口测试-接口管理-接口-json-schema-自动生成测试数据

| 参数 | 类型 | 来源 |
|------|------|------|
| `jsonSchemaItem` | `JsonSchemaItem` | Body |

**JsonSchemaItem 字段明细**:
  - `id`: `String`
  - `title`: `String`
  - `example`: `String`
  - `description`: `String`
  - `items`: `List<JsonSchemaItem>` *约束: @Valid;*
  - `properties`: `Map<String, JsonSchemaItem>`
  - `additionalProperties`: `JsonSchemaItem`
  - `required`: `List<String>`
  - `defaultValue`: `Object`
  - `pattern`: `String`
  - `maxLength`: `Integer`
  - `minLength`: `Integer`
  - `minimum`: `BigDecimal`
  - `maximum`: `BigDecimal`
  - `maxItems`: `Integer`
  - `minItems`: `Integer`
  - `format`: `String`
  - `enumValues`: `List<String>`
  - `value`: `String`

**返回值**: `String`

#### **`PostMapping /api/definition/debug`** — 接口调试

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionRunRequest` | Body |

**ApiDefinitionRunRequest 字段明细**:
  > **继承**: `ApiDebugRunRequest`
  - `environmentId`: `String` 环境ID
  - `method`: `String` http协议类型post/get/其它协议则是协议名(mqtt)
  - `path`: `String` http协议路径/其它协议则为空
  - `moduleId`: `String` 模块fk
  - `num`: `Long` 接口编号  mock执行需要

**返回值**: `TaskRequestDTO`

#### **`PostMapping /api/definition/get-reference`** — 接口测试-接口管理-引用关系

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ReferenceRequest` | Body |

**ReferenceRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `resourceId`: `String` **[必填]** 资源id

**返回值**: `Pager<List<ReferenceDTO>>`

#### **`PostMapping /api/definition/export/{type}`** — 接口测试-接口管理-导出接口定义

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionBatchExportRequest` | Body |
| `type` | `String` | 路径 |

**ApiDefinitionBatchExportRequest 字段明细**:
  > **继承**: `ApiDefinitionBatchRequest`
  - `fileId`: `String` **[必填]** 文件id
  - `exportApiCase`: `boolean` 是否同步导出接口用例
  - `exportApiMock`: `boolean` 是否同步导出接口Mock

**返回值**: `String`

#### **`GetMapping /api/definition/stop/{taskId}`** — 接口测试-接口管理-导出-停止导出

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskId` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/definition/download/file/{projectId}/{fileId}`** — 接口测试-接口管理-下载文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `fileId` | `String` | 路径 |
| `httpServletResponse` | `HttpServletResponse` | 参数 |

**返回值**: `void`


### ApiDefinitionMockController
**业务标签**: 接口测试-接口管理-接口定义-Mock

#### **`PostMapping /api/definition/mock/page`** — 接口测试-接口管理-接口 Mock

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionMockPageRequest` | Body |

**ApiDefinitionMockPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `name`: `String` 接口 mock 名称 *约束: @Size(min = 1, max = 255, message = "{api_definition_mock.name.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.project_id.length_range}");*
  - `apiDefinitionId`: `String` 接口fk *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.api_definition_id.length_range}");*

**返回值**: `Pager<List<ApiDefinitionMockDTO>>`

#### **`PostMapping /api/definition/mock/detail`** — 接口测试-接口管理-获取 Mock 详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionMockRequest` | Body |

**ApiDefinitionMockRequest 字段明细**:
  - `id`: `String` **[必填]** 接口 mock pk *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.project_id.length_range}");*

**返回值**: `ApiDefinitionMockDTO`

#### **`PostMapping /api/definition/mock/add`** — 接口测试-接口管理-添加 Mock

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionMockAddRequest` | Body |

**ApiDefinitionMockAddRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.project_id.length_range}");*
  - `name`: `String` **[必填]** 接口 mock 名称 *约束: @Size(min = 1, max = 255, message = "{api_definition_mock.name.length_range}");*
  - `statusCode`: `int` 响应码
  - `mockMatchRule`: `MockMatchRule` 请求内容
  - `response`: `MockResponse` 请求内容
  - `apiDefinitionId`: `String` **[必填]** 接口fk *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.api_definition_id.length_range}");*
  - `uploadFileIds`: `List<String>` 新上传的文件ID
  - `linkFileIds`: `List<String>` 关联文件ID

**返回值**: `ApiDefinitionMock`

#### **`PostMapping /api/definition/mock/update`** — 接口测试-接口管理-更新 Mock

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionMockUpdateRequest` | Body |

**ApiDefinitionMockUpdateRequest 字段明细**:
  > **继承**: `ApiDefinitionMockAddRequest`
  - `id`: `String` **[必填]** 接口 mock pk *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.id.length_range}");*
  - `deleteFileIds`: `List<String>` 删除的文件ID
  - `unLinkFileIds`: `List<String>` 取消关联文件ID

**返回值**: `ApiDefinitionMock`

#### **`GetMapping /api/definition/mock/enable/{id}`** — 接口测试-接口管理-更新 Mock-更新状态

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/definition/mock/delete`** — 接口测试-接口管理-删除 Mock

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionMockRequest` | Body |

**ApiDefinitionMockRequest 字段明细**:
  - `id`: `String` **[必填]** 接口 mock pk *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.project_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/definition/mock/copy`** — 接口测试-接口管理-复制 Mock

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionMockRequest` | Body |

**ApiDefinitionMockRequest 字段明细**:
  - `id`: `String` **[必填]** 接口 mock pk *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_mock.project_id.length_range}");*

**返回值**: `ApiDefinitionMock`

#### **`PostMapping /api/definition/mock/upload/temp/file`** — 上传接口 Mock 所需的文件资源，并返回文件ID

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`GetMapping /api/definition/mock/transfer/options/{projectId}`** — 接口测试-接口管理-接口-附件-转存目录下拉框

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/definition/mock/transfer`** — 接口测试-接口管理-接口-附件-文件转存

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTransferRequest` | Body |

**ApiTransferRequest 字段明细**:
  > **继承**: `ApiFileRequest`
  - `moduleId`: `String` **[必填]** 转存的模块id
  - `originalName`: `String` **[必填]** 原始文件名

**返回值**: `String`

#### **`GetMapping /api/definition/mock/get-url/{id}`** — 接口测试-接口管理-获取 Mock URL

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `String`

#### **`PostMapping /api/definition/mock/batch/delete`** — 接口测试-接口管理-mock-批量删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCaseBatchRequest` | Body |

**ApiTestCaseBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `apiDefinitionId`: `String` 接口pk *约束: @Size(max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本来源 *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/definition/mock/batch/edit`** — 接口测试-接口管理-mock-批量编辑

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiMockBatchEditRequest` | Body |

**ApiMockBatchEditRequest 字段明细**:
  > **继承**: `ApiTestCaseBatchRequest`
  - `tags`: `LinkedHashSet<String>` 标签
  - `type`: `String` **[必填]** 批量编辑的类型 状态 :Status,标签: Tags
  - `enable`: `boolean` 状态  开启/关闭

**返回值**: `void`

#### **`PostMapping /api/definition/mock/operation-history/page`** — 接口测试-接口管理-mock-变更历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OperationHistoryRequest` | Body |

**OperationHistoryRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{operation_history.project_id.length_range}");*
  - `sourceId`: `String` **[必填]** 资源id
  - `createUser`: `String` 操作人
  - `types`: `List<String>` 操作类型
  - `modules`: `String` 操作模块

**返回值**: `Pager<List<OperationHistoryDTO>>`


### ApiDefinitionModuleController
**业务标签**: 接口测试-接口管理-模块

#### **`PostMapping /api/definition/module/tree`** — 接口测试-接口管理-模块-查找模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiModuleRequest` | Body |

**ApiModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/definition/module/add`** — 接口测试-接口管理-模块-添加模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ModuleCreateRequest` | Body |

**ModuleCreateRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_debug.project_id.length_range}");*
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{api_debug_module.name.length_range}");*

**返回值**: `String`

#### **`PostMapping /api/definition/module/update`** — 接口测试-接口管理-模块-修改模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ModuleUpdateRequest` | Body |

**ModuleUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 模块ID *约束: @Size(min = 1, max = 50, message = "{api_debug_module.id.length_range}");*
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{api_debug_module.name.length_range}");*

**返回值**: `boolean`

#### **`GetMapping /api/definition/module/delete/{id}`** — 接口测试-接口管理-模块-删除模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/definition/module/move`** — 接口测试-接口管理-模块-移动模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `NodeMoveRequest` | Body |

**NodeMoveRequest 字段明细**:
  - `dragNodeId`: `String` **[必填]** 被拖拽的节点
  - `dropNodeId`: `String` **[必填]** 放入的节点
  - `dropPosition`: `int` 放入的位置（取值：-1，,1。  -1：dropNodeId节点之前。 1：dropNodeId节点后）

**返回值**: `void`

#### **`PostMapping /api/definition/module/count`** — 接口测试-接口管理-模块-统计模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiModuleRequest` | Body |

**ApiModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `Map<String, Long>`

#### **`PostMapping /api/definition/module/trash/count`** — 接口测试-接口管理-模块-统计回收站模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiModuleRequest` | Body |

**ApiModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `Map<String, Long>`

#### **`PostMapping /api/definition/module/trash/tree`** — 接口测试-接口管理-模块-查找模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiModuleRequest` | Body |

**ApiModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/definition/module/env/tree`** — 获取环境中的接口树和选中的模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `EnvApiModuleRequest` | Body |

**EnvApiModuleRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `selectedModules`: `List<ApiModuleDTO>` 选中的模块

**返回值**: `EnvApiTreeDTO`

#### **`PostMapping /api/definition/module/only/tree`** — 接口测试-接口管理-模块-不包含请求数据的模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiModuleRequest` | Body |

**ApiModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `List<BaseTreeNode>`


### ApiDefinitionScheduleController
**业务标签**: 接口测试-接口管理-接口定义-定时同步

#### **`PostMapping /api/definition/schedule/add`** — 接口测试-接口管理-定时同步-创建

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScheduleRequest` | Body |

**ApiScheduleRequest 字段明细**:
  - `id`: `String` **[必填]** id *约束: @Size(min = 1, max = 50, message = "{api_definition_swagger.id.length_range}", groups = {Updated.class});*
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition_swagger.project_id.length_range}", groups = {Created.class, Updated.class});*
  - `name`: `String` **[必填]** 定时任务名称 *约束: @Size(min = 1, max = 255, message = "{api_definition_swagger.name.length_range}", groups = {Created.class, Updated.class});*
  - `moduleId`: `String` 模块ID *约束: @Size(max = 50, message = "{api_definition_swagger.module_id.length_range}", groups = {Created.class, Updated.class});*
  - `swaggerUrl`: `String` **[必填]** swagger地址 *约束: @Size(min = 1, max = 500, message = "{api_definition_swagger.swagger_url.length_range}", groups = {Created.class, Updated.class});*
  - `swaggerToken`: `String`
  - `taskId`: `String`
  - `authUsername`: `String` Basic Auth认证用户名
  - `authPassword`: `String` Basic Auth认证密码
  - `userId`: `String` 用户id
  - `value`: `String` **[必填]** cron 表达式 *约束: @Size(min = 1, max = 255, message = "{schedule.value.length_range}", groups = {Created.class, Updated.class});*
  - `config`: `String` 配置信息

**返回值**: `String`

#### **`PostMapping /api/definition/schedule/update`** — 接口测试-接口管理-定时同步-更新

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScheduleRequest` | Body |

**ApiScheduleRequest 字段明细**:
  - `id`: `String` **[必填]** id *约束: @Size(min = 1, max = 50, message = "{api_definition_swagger.id.length_range}", groups = {Updated.class});*
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition_swagger.project_id.length_range}", groups = {Created.class, Updated.class});*
  - `name`: `String` **[必填]** 定时任务名称 *约束: @Size(min = 1, max = 255, message = "{api_definition_swagger.name.length_range}", groups = {Created.class, Updated.class});*
  - `moduleId`: `String` 模块ID *约束: @Size(max = 50, message = "{api_definition_swagger.module_id.length_range}", groups = {Created.class, Updated.class});*
  - `swaggerUrl`: `String` **[必填]** swagger地址 *约束: @Size(min = 1, max = 500, message = "{api_definition_swagger.swagger_url.length_range}", groups = {Created.class, Updated.class});*
  - `swaggerToken`: `String`
  - `taskId`: `String`
  - `authUsername`: `String` Basic Auth认证用户名
  - `authPassword`: `String` Basic Auth认证密码
  - `userId`: `String` 用户id
  - `value`: `String` **[必填]** cron 表达式 *约束: @Size(min = 1, max = 255, message = "{schedule.value.length_range}", groups = {Created.class, Updated.class});*
  - `config`: `String` 配置信息

**返回值**: `String`

#### **`GetMapping /api/definition/schedule/switch/{id}`** — 接口测试-接口管理-定时同步-开启/关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/definition/schedule/delete/{id}`** — 接口测试-接口管理-定时同步-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/definition/schedule/get/{id}`** — 接口测试-接口管理-定时同步-查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiScheduleDTO`


### ApiDocShareController
**业务标签**: 接口测试-定义-分享

#### **`PostMapping /api/doc/share/page`** — 接口测试-定义-分页获取分享列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDocSharePageRequest` | Body |

**ApiDocSharePageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_doc_share.project_id.length_range}");*

**返回值**: `Pager<List<ApiDocShareDTO>>`

#### **`PostMapping /api/doc/share/add`** — 接口测试-定义-新增分享

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDocShareEditRequest` | Body |

**ApiDocShareEditRequest 字段明细**:
  - `id`: `String` **[必填]** 主键 *约束: @Size(min = 1, max = 50, message = "{api_doc_share.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 分享名称 *约束: @Size(min = 1, max = 255, message = "{api_doc_share.name.length_range}");*
  - `apiRange`: `String` **[必填]** 接口范围;全部接口(ALL)、模块(MODULE)、路径(PATH)、标签(TAG) *约束: @Size(min = 1, max = 10, message = "{api_doc_share.api_range.length_range}", groups = {Created.class, Updated.class});*
  - `rangeMatchSymbol`: `String` 范围匹配符;包含(CONTAINS)、等于(EQUALS)
  - `rangeMatchVal`: `String` 范围匹配值;eg: 选中路径范围时, 该值作为路径匹配
  - `invalidTime`: `Long` 截止时间值
  - `invalidUnit`: `String` 失效时间单位;小时(HOUR)、天(DAY)、月(MONTH)、年(YEAR)
  - `isPrivate`: `Boolean` **[必填]** 是否私有;0: 公开、1: 私有
  - `password`: `String` 访问密码;私有时需要访问密码
  - `allowExport`: `Boolean` 允许导出;0: 不允许、1: 允许
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_doc_share.project_id.length_range}", groups = {Created.class, Updated.class});*

**返回值**: `ApiDocShare`

#### **`PostMapping /api/doc/share/update`** — 接口测试-定义-更新分享

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDocShareEditRequest` | Body |

**ApiDocShareEditRequest 字段明细**:
  - `id`: `String` **[必填]** 主键 *约束: @Size(min = 1, max = 50, message = "{api_doc_share.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 分享名称 *约束: @Size(min = 1, max = 255, message = "{api_doc_share.name.length_range}");*
  - `apiRange`: `String` **[必填]** 接口范围;全部接口(ALL)、模块(MODULE)、路径(PATH)、标签(TAG) *约束: @Size(min = 1, max = 10, message = "{api_doc_share.api_range.length_range}", groups = {Created.class, Updated.class});*
  - `rangeMatchSymbol`: `String` 范围匹配符;包含(CONTAINS)、等于(EQUALS)
  - `rangeMatchVal`: `String` 范围匹配值;eg: 选中路径范围时, 该值作为路径匹配
  - `invalidTime`: `Long` 截止时间值
  - `invalidUnit`: `String` 失效时间单位;小时(HOUR)、天(DAY)、月(MONTH)、年(YEAR)
  - `isPrivate`: `Boolean` **[必填]** 是否私有;0: 公开、1: 私有
  - `password`: `String` 访问密码;私有时需要访问密码
  - `allowExport`: `Boolean` 允许导出;0: 不允许、1: 允许
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_doc_share.project_id.length_range}", groups = {Created.class, Updated.class});*

**返回值**: `ApiDocShare`

#### **`GetMapping /api/doc/share/delete/{id}`** — 接口测试-定义-删除分享

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/doc/share/check`** — 接口测试-定义-校验分享密码

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDocShareCheckRequest` | Body |

**ApiDocShareCheckRequest 字段明细**:
  - `docShareId`: `String` 分享ID
  - `password`: `String` 密码

**返回值**: `Boolean`

#### **`GetMapping /api/doc/share/detail/{id}`** — 接口测试-定义-分享-查看链接

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiDocShareDetail`

#### **`PostMapping /api/doc/share/module/tree`** — 接口测试-定义-分享-模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDocShareModuleRequest` | Body |

**ApiDocShareModuleRequest 字段明细**:
  > **继承**: `ApiModuleRequest`
  - `shareId`: `String` **[必填]** 分享ID *约束: @Size(min = 1, max = 50, message = "{api_doc_share.id.length_range}");*
  - `orgId`: `String` 组织ID

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/doc/share/module/count`** — 接口测试-定义-分享-模块树数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDocShareModuleRequest` | Body |

**ApiDocShareModuleRequest 字段明细**:
  > **继承**: `ApiModuleRequest`
  - `shareId`: `String` **[必填]** 分享ID *约束: @Size(min = 1, max = 50, message = "{api_doc_share.id.length_range}");*
  - `orgId`: `String` 组织ID

**返回值**: `Map<String, Long>`

#### **`PostMapping /api/doc/share/export/{type}`** — 接口测试-定义-分享-导出

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDocShareExportRequest` | Body |
| `type` | `String` | 路径 |

**ApiDocShareExportRequest 字段明细**:
  > **继承**: `ApiDefinitionBatchExportRequest`
  - `shareId`: `String` 分享ID
  - `orgId`: `String` 组织ID

**返回值**: `String`

#### **`GetMapping /api/doc/share/stop/{taskId}`** — 接口测试-定义-分享-导出-停止导出

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskId` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/doc/share/download/file/{projectId}/{fileId}`** — 接口测试-定义-分享-导出-下载文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `fileId` | `String` | 路径 |
| `httpServletResponse` | `HttpServletResponse` | 参数 |

**返回值**: `void`

#### **`GetMapping /api/doc/share/get-detail/{id}`** — 接口测试-接口管理-获取接口详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiDefinitionDTO`

#### **`GetMapping /api/doc/share/plugin/script/{id}/{orgId}`** — 获取定义的插件脚本

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `orgId` | `String` | 路径 |

**返回值**: `Object`


### ApiReportController
**业务标签**: 接口测试-接口报告-用例

#### **`PostMapping /api/report/case/page`** — 接口测试-接口报告-用例()

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiReportPageRequest` | Body |

**ApiReportPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `Pager<List<ApiReportListDTO>>`

#### **`PostMapping /api/report/case/rename/{id}`** — 接口测试-接口报告-用例报告重命名

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `name` | `Object` | Body |

**返回值**: `void`

#### **`GetMapping /api/report/case/delete/{id}`** — 接口测试-接口报告-用例报告删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/report/case/batch/delete`** — 接口测试-接口报告-用例报告批量删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiReportBatchRequest` | Body |

**ApiReportBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/report/case/batch-param`** — 接口测试-接口报告-获取用例报告批量参数

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiReportBatchRequest` | Body |

**ApiReportBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `List<String>`

#### **`GetMapping /api/report/case/get/{id}`** — 接口测试-接口报告-报告获取

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiReportDTO`

#### **`GetMapping /api/report/case/share/{shareId}/{reportId}`** — 接口测试-接口报告-分享报告获取

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |

**返回值**: `ApiReportDTO`

#### **`GetMapping /api/report/case/get/detail/{reportId}/{stepId}`** — 接口测试-接口报告-报告详情获取

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |
| `stepId` | `String` | 路径 |

**返回值**: `List<ApiReportDetailDTO>`

#### **`GetMapping /api/report/case/share/detail/{shareId}/{reportId}/{stepId}`**

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |
| `stepId` | `String` | 路径 |

**返回值**: `List<ApiReportDetailDTO>`

#### **`PostMapping /api/report/case/export/{reportId}`** — 接口测试-用例报告-导出日志

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/report/case/batch-export`** — 接口测试-用例报告-批量导出日志

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiReportBatchRequest` | Body |

**ApiReportBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `void`

#### **`GetMapping /api/report/case/task-report/{id}`** — 系统-任务中心-接口用例执行任务详情-查看

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiTaskReportDTO`


### ApiShareController
**业务标签**: 接口测试-接口管理-接口分享

#### **`PostMapping /api/share/doc/gen`** — 接口测试-接口管理-接口文档分享

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiDefinitionDocRequest` | Body |

**ApiDefinitionDocRequest 字段明细**:
  - `keyword`: `String` 关键字
  - `apiId`: `String` 接口pk *约束: @Size(min = 1, max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `type`: `String` 类型(ALL,MODULE,API)
  - `versionId`: `String` 版本fk *约束: @Size(min = 1, max = 50, message = "{api_definition.version_id.length_range}");*

**返回值**: `ShareInfoDTO`

#### **`GetMapping /api/share/doc/view/{shareId}`** — 接口测试-接口管理-接口文档分享查看

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |

**返回值**: `ApiDefinitionDocDTO`


### ApiTestCaseAIController
**业务标签**: 接口测试-接口管理-接口用例-AI生成

#### **`PostMapping /api/case/ai/chat`** — 聊天

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCaseAIRequest` | Body |

**ApiTestCaseAIRequest 字段明细**:
  > **继承**: `AIChatRequest`
  - `apiDefinitionId`: `String` **[必填]** 接口定义ID
  - `configId`: `String` 配置ID

**返回值**: `String`

#### **`GetMapping /api/case/ai/get/config`** — 接口管理-接口用例-获取用户AI提示词配置

**无入参**

**返回值**: `ApiCaseAIConfigDTO`

#### **`PostMapping /api/case/ai/save/config`** — 接口管理-接口用例-保存用户AI提示词配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `promptDTO` | `ApiCaseAIConfigDTO` | Body |

**ApiCaseAIConfigDTO 字段明细**:
  - `normal`: `Boolean`
  - `abnormal`: `Boolean`
  - `caseName`: `Boolean`
  - `requestParams`: `Boolean`
  - `preScript`: `Boolean`
  - `postScript`: `Boolean`
  - `assertion`: `Boolean`

**返回值**: `void`

#### **`PostMapping /api/case/ai/transform`** — 接口管理-接口用例-单条AI数据生成用例对象

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiCaseAiTransformDTO` | Body |

**ApiCaseAiTransformDTO 字段明细**:
  - `apiDefinitionId`: `String` **[必填]** 接口定义ID
  - `prompt`: `String` **[必填]** 提示词

**返回值**: `ApiTestCaseDTO`

#### **`PostMapping /api/case/ai/batch/save`** — 接口管理-接口用例-批量保存AI用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiCaseAiTransformDTO` | Body |

**ApiCaseAiTransformDTO 字段明细**:
  - `apiDefinitionId`: `String` **[必填]** 接口定义ID
  - `prompt`: `String` **[必填]** 提示词

**返回值**: `ApiCaseAiResponse`


### ApiTestCaseController
**业务标签**: 接口测试-接口管理-接口用例

#### **`PostMapping /api/case/add`** — 接口测试-接口管理-接口用例-新增

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCaseAddRequest` | Body |

**ApiTestCaseAddRequest 字段明细**:
  - `name`: `String` **[必填]** 用例名称 *约束: @Size(min = 1, max = 255, message = "{api_debug.name.length_range}");*
  - `projectId`: `String` **[必填]** 项目fk *约束: @Size(min = 1, max = 50, message = "{api_debug.project_id.length_range}");*
  - `priority`: `String` **[必填]** 用例等级 *约束: @Size(min = 1, max = 50, message = "{api_test_case.priority.length_range}");*
  - `status`: `String` **[必填]** 用例状态 *约束: @Size(min = 1, max = 20, message = "{api_test_case.status.length_range}"); @EnumValue(enumClass = ApiDefinitionStatus.class);*
  - `apiDefinitionId`: `String` **[必填]** 接口fk *约束: @Size(min = 1, max = 50, message = "{api_test_case.api_definition_id.length_range}");*
  - `environmentId`: `String` 环境fk *约束: @Size(max = 50, message = "{api_test_case.environment_id.length_range}");*
  - `request`: `Object` **[必填]** 请求内容
  - `uploadFileIds`: `List<String>` 新上传的文件ID
  - `linkFileIds`: `List<String>` 关联文件ID

**返回值**: `ApiTestCase`

#### **`GetMapping /api/case/get-detail/{id}`** — 接口测试-接口管理-接口用例-获取详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiTestCaseDTO`

#### **`GetMapping /api/case/delete-to-gc/{id}`** — 接口测试-接口管理-接口用例-移动到回收站

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/case/recover/{id}`** — 接口测试-接口管理-接口用例-恢复

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/case/follow/{id}`** — 接口测试-接口管理-接口用例-关注

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/case/unfollow/{id}`** — 接口测试-接口管理-接口用例-取消关注

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/case/delete/{id}`** — 接口测试-接口管理-接口用例-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/case/update`** — 接口测试-接口管理-接口用例-更新

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCaseUpdateRequest` | Body |

**ApiTestCaseUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 用例Id *约束: @Size(min = 1, max = 50, message = "{api_debug.project_id.length_range}");*
  - `name`: `String` **[必填]** 用例名称 *约束: @Size(min = 1, max = 255, message = "{api_debug.name.length_range}");*
  - `priority`: `String` **[必填]** 用例等级 *约束: @Size(min = 1, max = 50, message = "{api_test_case.priority.length_range}");*
  - `status`: `String` **[必填]** 用例状态 *约束: @Size(min = 1, max = 20, message = "{api_test_case.status.length_range}"); @EnumValue(enumClass = ApiDefinitionStatus.class);*
  - `environmentId`: `String` 环境fk *约束: @Size(max = 50, message = "{api_test_case.environment_id.length_range}");*
  - `request`: `Object` **[必填]** 请求内容
  - `uploadFileIds`: `List<String>` 新上传的文件ID
  - `linkFileIds`: `List<String>` 关联文件ID
  - `deleteFileIds`: `List<String>` 删除的文件ID
  - `unLinkFileIds`: `List<String>` 取消关联文件ID

**返回值**: `ApiTestCase`

#### **`PostMapping /api/case/file/copy`** — 接口测试-接口管理-复制用例时，复制文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiFileCopyRequest` | Body |

**ApiFileCopyRequest 字段明细**:
  - `resourceId`: `String` **[必填]** 资源id
  - `fileIds`: `List<String>` **[必填]** 文件数组

**返回值**: `Map<String, String>`

#### **`GetMapping /api/case/update-priority/{id}/{priority}`** — 接口测试-接口管理-接口用例-更新等级

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `priority` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/case/update-status/{id}/{status}`** — 接口测试-接口管理-接口用例-更新状态

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `status` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/case/page`** — 接口测试-接口管理-接口用例-分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCasePageRequest` | Body |

**ApiTestCasePageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `apiDefinitionId`: `String` 接口pk *约束: @Size(max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本来源 *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `Pager<List<ApiTestCaseDTO>>`

#### **`PostMapping /api/case/statistics`** — 接口测试-接口管理-接口用例-统计

| 参数 | 类型 | 来源 |
|------|------|------|
| `ids` | `List<String>` | Body |

**返回值**: `List<ApiTestCaseDTO>`

#### **`PostMapping /api/case/batch/delete`** — 接口测试-接口管理-接口用例-批量删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCaseBatchRequest` | Body |

**ApiTestCaseBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `apiDefinitionId`: `String` 接口pk *约束: @Size(max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本来源 *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/case/batch/delete-to-gc`** — 接口测试-接口管理-接口用例-批量移动到回收站

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCaseBatchRequest` | Body |

**ApiTestCaseBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `apiDefinitionId`: `String` 接口pk *约束: @Size(max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本来源 *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/case/batch/edit`** — 接口测试-接口管理-接口用例-批量编辑

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiCaseBatchEditRequest` | Body |

**ApiCaseBatchEditRequest 字段明细**:
  > **继承**: `ApiTestCaseBatchRequest`
  - `tags`: `LinkedHashSet<String>` 标签
  - `type`: `String` **[必填]** 批量编辑的类型  用例等级: Priority,状态 :Status,标签: Tags,用例环境: Environment
  - `environmentId`: `String` 环境id *约束: @Size(max = 50, message = "{api_test_case.env_id.length_range}");*
  - `status`: `String` 用例状态 *约束: @Size(max = 20, message = "{api_test_case.status.length_range}");*
  - `priority`: `String` 用例等级 *约束: @Size(max = 50, message = "{api_test_case.priority.length_range_}");*

**返回值**: `void`

#### **`PostMapping /api/case/batch/recover`** — 接口测试-接口管理-接口用例-批量恢复

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCaseBatchRequest` | Body |

**ApiTestCaseBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `apiDefinitionId`: `String` 接口pk *约束: @Size(max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本来源 *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/case/batch/api-change/sync`** — 接口测试-接口管理-接口用例-批量编辑

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiCaseBatchSyncRequest` | Body |

**返回值**: `void`

#### **`PostMapping /api/case/trash/page`** — 接口测试-接口管理-接口用例-回收站-分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCasePageRequest` | Body |

**ApiTestCasePageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `apiDefinitionId`: `String` 接口pk *约束: @Size(max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本来源 *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `Pager<List<ApiTestCaseDTO>>`

#### **`PostMapping /api/case/edit/pos`** — 接口测试-接口管理-接口用例-拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PosRequest` | Body |

**PosRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目id
  - `moveId`: `String` **[必填]** 移动用例id
  - `targetId`: `String` **[必填]** 目标用例id
  - `moveMode`: `String` **[必填]** 移动类型

**返回值**: `void`

#### **`PostMapping /api/case/upload/temp/file`** — 上传接口调试所需的文件资源，并返回文件ID

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`PostMapping /api/case/execute/page`** — 接口测试-接口管理-接口用例-获取执行历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ExecutePageRequest` | Body |

**ExecutePageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `id`: `String` **[必填]** 用例id/场景id *约束: @Size(min = 1, max = 50, message = "{api_test_case.id.length_range}");*

**返回值**: `Pager<List<ExecuteReportDTO>>`

#### **`PostMapping /api/case/operation-history/page`** — 接口测试-接口管理-接口用例-接口变更历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OperationHistoryRequest` | Body |

**OperationHistoryRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{operation_history.project_id.length_range}");*
  - `sourceId`: `String` **[必填]** 资源id
  - `createUser`: `String` 操作人
  - `types`: `List<String>` 操作类型
  - `modules`: `String` 操作模块

**返回值**: `Pager<List<OperationHistoryDTO>>`

#### **`PostMapping /api/case/transfer`** — 接口测试-接口管理-接口用例-附件-文件转存

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTransferRequest` | Body |

**ApiTransferRequest 字段明细**:
  > **继承**: `ApiFileRequest`
  - `moduleId`: `String` **[必填]** 转存的模块id
  - `originalName`: `String` **[必填]** 原始文件名

**返回值**: `String`

#### **`GetMapping /api/case/transfer/options/{projectId}`** — 接口测试-接口管理-接口用例-附件-转存目录下拉框

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/case/debug`** — 用例调试

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiCaseRunRequest` | Body |

**ApiCaseRunRequest 字段明细**:
  > **继承**: `ApiDebugRunRequest`
  - `environmentId`: `String` 环境ID
  - `apiDefinitionId`: `String` **[必填]** 接口定义ID

**返回值**: `TaskRequestDTO`

#### **`GetMapping /api/case/run/{id}`** — 用例执行, 传ID执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `reportId` | `String` | Query |

**返回值**: `TaskRequestDTO`

#### **`PostMapping /api/case/run`** — 用例执行，传请求详情执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiCaseRunRequest` | Body |

**ApiCaseRunRequest 字段明细**:
  > **继承**: `ApiDebugRunRequest`
  - `environmentId`: `String` 环境ID
  - `apiDefinitionId`: `String` **[必填]** 接口定义ID

**返回值**: `TaskRequestDTO`

#### **`PostMapping /api/case/batch/run`** — 批量执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTestCaseBatchRunRequest` | Body |

**ApiTestCaseBatchRunRequest 字段明细**:
  > **继承**: `ApiTestCaseBatchRequest`
  - `runModeConfig`: `ApiRunModeRequest` 运行模式配置 *约束: @Valid;*

**返回值**: `void`

#### **`PostMapping /api/case/get-reference`** — 接口测试-接口管理-接口用例-引用关系

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ReferenceRequest` | Body |

**ReferenceRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `resourceId`: `String` **[必填]** 资源id

**返回值**: `Pager<List<ReferenceDTO>>`

#### **`GetMapping /api/case/api-change/clear/{id}`** — 清除接口参数变更标识

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/case/api-change/ignore/{id}`** — 忽略接口变更提示

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `ignore` | `boolean` | Query |

**返回值**: `void`

#### **`PostMapping /api/case/api-change/sync`** — 获取同步后的用例详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiCaseSyncRequest` | Body |

**ApiCaseSyncRequest 字段明细**:
  - `apiCaseRequest`: `Object` **[必填]** 用例的请求详情
  - `id`: `String` **[必填]** 用例ID

**返回值**: `AbstractMsTestElement`

#### **`GetMapping /api/case/api/compare/{id}`** — 与接口定义对比

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiCaseCompareData`


### ApiScenarioBatchOperationController
**业务标签**: 接口测试-接口场景批量操作

#### **`PostMapping /api/scenario/batch-operation/edit`** — 接口测试-接口场景批量操作-批量编辑

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioBatchEditRequest` | Body |

**ApiScenarioBatchEditRequest 字段明细**:
  > **继承**: `ApiScenarioBatchRequest`
  - `tags`: `LinkedHashSet<String>` 标签
  - `type`: `String` **[必填]** 批量编辑的类型  用例等级: Priority,状态 :Status,标签: Tags,用例环境: Environment
  - `envId`: `String` 环境id *约束: @Size(max = 50, message = "{api_test_case.environment_id.length_range}");*
  - `groupId`: `String` 环境组id *约束: @Size(max = 50, message = "{api_scenario.group_id.length_range}");*
  - `status`: `String` 用例状态 *约束: @Size(max = 20, message = "{api_test_case.status.length_range}");*
  - `priority`: `String` 用例等级 *约束: @Size(max = 50, message = "{api_test_case.priority.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/scenario/batch-operation/delete-gc`** — 接口测试-接口场景批量操作-回收站列表-批量删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioBatchRequest` | Body |

**ApiScenarioBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `apiScenarioId`: `String` 场景pk
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk
  - `refId`: `String` 版本来源

**返回值**: `ApiScenarioBatchOperationResponse`

#### **`PostMapping /api/scenario/batch-operation/recover-gc`** — 接口测试-接口场景批量操作-回收站列表-批量恢复

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioBatchRequest` | Body |

**ApiScenarioBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `apiScenarioId`: `String` 场景pk
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk
  - `refId`: `String` 版本来源

**返回值**: `ApiScenarioBatchOperationResponse`

#### **`PostMapping /api/scenario/batch-operation/delete`** — 接口测试-接口场景批量操作-场景列表操作-批量删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioBatchRequest` | Body |

**ApiScenarioBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `apiScenarioId`: `String` 场景pk
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk
  - `refId`: `String` 版本来源

**返回值**: `ApiScenarioBatchOperationResponse`

#### **`PostMapping /api/scenario/batch-operation/move`** — 接口测试-接口场景批量操作-场景列表操作-批量移动

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioBatchCopyMoveRequest` | Body |

**ApiScenarioBatchCopyMoveRequest 字段明细**:
  > **继承**: `ApiScenarioBatchRequest`
  - `targetModuleId`: `String` **[必填]** 复制的目标模块ID *约束: @Size(max = 50, message = "{api_scenario.target_module_id.length_range}");*

**返回值**: `ApiScenarioBatchOperationResponse`

#### **`PostMapping /api/scenario/batch-operation/copy`** — 接口测试-接口场景批量操作-场景列表操作-批量复制

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioBatchCopyMoveRequest` | Body |

**ApiScenarioBatchCopyMoveRequest 字段明细**:
  > **继承**: `ApiScenarioBatchRequest`
  - `targetModuleId`: `String` **[必填]** 复制的目标模块ID *约束: @Size(max = 50, message = "{api_scenario.target_module_id.length_range}");*

**返回值**: `ApiScenarioBatchOperationResponse`

#### **`PostMapping /api/scenario/batch-operation/run`** — 接口测试-接口场景批量操作-场景列表操作-批量执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioBatchRunRequest` | Body |

**ApiScenarioBatchRunRequest 字段明细**:
  > **继承**: `ApiScenarioBatchRequest`
  - `runModeConfig`: `ApiRunModeRequest` 运行模式配置 *约束: @Valid;*

**返回值**: `void`

#### **`PostMapping /api/scenario/batch-operation/schedule-config`** — 接口测试-接口场景管理-定时任务批量配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioBatchScheduleConfigRequest` | Body |

**ApiScenarioBatchScheduleConfigRequest 字段明细**:
  > **继承**: `ApiScenarioBatchRequest`
  - `enable`: `boolean` 启用/禁用
  - `cron`: `String` Cron表达式
  - `config`: `ApiRunModeConfigDTO` 定时任务配置

**返回值**: `void`


### ApiScenarioController
**业务标签**: 接口测试-接口场景管理

#### **`PostMapping /api/scenario/page`** — 接口测试-接口场景管理-场景列表(deleted 状态为 1 时为回收站数据)

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioPageRequest` | Body |

**ApiScenarioPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `scenarioId`: `String` 场景pk *约束: @Size(min = 1, max = 50, message = "{api_scenario_step.scenario_id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(min = 1, max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(min = 1, max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `Pager<List<ApiScenarioDTO>>`

#### **`PostMapping /api/scenario/statistics`** — 接口测试-接口场景管理-获取通过率

| 参数 | 类型 | 来源 |
|------|------|------|
| `ids` | `List<String>` | Body |

**返回值**: `List<ApiScenarioDTO>`

#### **`PostMapping /api/scenario/trash/page`** — 接口测试-接口场景管理-场景列表(deleted 状态为 1 时为回收站数据)

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioPageRequest` | Body |

**ApiScenarioPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `scenarioId`: `String` 场景pk *约束: @Size(min = 1, max = 50, message = "{api_scenario_step.scenario_id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(min = 1, max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(min = 1, max = 50, message = "{api_definition.ref_id.length_range}");*

**返回值**: `Pager<List<ApiScenarioDTO>>`

#### **`GetMapping /api/scenario/follow/{id}`** — 接口测试-接口场景管理-关注/ 取消关注

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/scenario/add`** — 接口测试-接口场景管理-创建场景

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioAddRequest` | Body |

**ApiScenarioAddRequest 字段明细**:
  - `name`: `String` **[必填]** 场景名称 *约束: @Size(min = 1, max = 255, message = "{api_scenario.name.length_range}");*
  - `priority`: `String` **[必填]** 场景级别/P0/P1等 *约束: @Size(min = 1, max = 10, message = "{api_scenario.priority.length_range}");*
  - `status`: `String` **[必填]** 场景状态/未规划/已完成 等 *约束: @Size(min = 1, max = 20, message = "{api_scenario.status.length_range}"); @EnumValue(enumClass = ApiScenarioStatus.class);*
  - `projectId`: `String` **[必填]** 项目fk *约束: @Size(min = 1, max = 50, message = "{api_scenario.project_id.length_range}");*
  - `moduleId`: `String` **[必填]** 场景模块fk *约束: @Size(max = 50, message = "{api_scenario.module_id.length_range}");*
  - `description`: `String` 描述信息 *约束: @Size(max = 1000, message = "{api_definition.description.length_range}");*
  - `tags`: `List<String>` 标签
  - `environmentId`: `String` 环境或者环境组ID *约束: @Size(max = 50, message = "{api_scenario.environment_id.length_range}");*
  - `copyFromScenarioId`: `String` 复制的原场景ID *约束: @Size(max = 50);*
  - `steps`: `List<ApiScenarioStepRequest>` 步骤集合 *约束: @Valid;*
  - `stepDetails`: `Map<String, Object>` 步骤详情
  - `stepFileParam`: `Map<String, ResourceAddFileParam>` 步骤文件操作相关参数

**返回值**: `ApiScenario`

#### **`PostMapping /api/scenario/upload/temp/file`** — 接口测试-接口场景管理-上传场景所需的文件资源，并返回文件ID

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`PostMapping /api/scenario/update`** — 接口测试-接口场景管理-更新场景

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioUpdateRequest` | Body |

**ApiScenarioUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** id *约束: @Size(max = 50, message = "{api_scenario.id.length_range}", groups = {Created.class, Updated.class});*
  - `name`: `String` 场景名称 *约束: @Size(max = 255, message = "{api_scenario.name.length_range}");*
  - `priority`: `String` 场景级别/P0/P1等 *约束: @Size(max = 10, message = "{api_scenario.priority.length_range}");*
  - `status`: `String` 场景状态/未规划/已完成 等 *约束: @Size(max = 20, message = "{api_scenario.status.length_range}"); @EnumValue(enumClass = ApiScenarioStatus.class);*
  - `moduleId`: `String` 场景模块fk *约束: @Size(max = 50, message = "{api_scenario.module_id.length_range}");*
  - `projectId`: `String` **[必填]** 项目fk *约束: @Size(min = 1, max = 50, message = "{api_scenario.project_id.length_range}");*
  - `description`: `String` 描述信息 *约束: @Size(max = 1000, message = "{api_definition.description.length_range}");*
  - `grouped`: `Boolean` 是否为环境组
  - `environmentId`: `String` 环境或者环境组ID *约束: @Size(max = 50, message = "{api_scenario.environment_id.length_range}");*
  - `steps`: `List<ApiScenarioStepRequest>` 步骤集合 *约束: @Valid;*
  - `stepDetails`: `Map<String, Object>` 步骤详情
  - `stepFileParam`: `Map<String, ResourceUpdateFileParam>` 步骤文件操作相关参数

**返回值**: `ApiScenario`

#### **`GetMapping /api/scenario/delete/{id}`** — 接口测试-接口场景管理-删除场景

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/scenario/delete-to-gc/{id}`** — 接口测试-接口场景管理-删除场景到回收站

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/scenario/get/{scenarioId}`** — 接口测试-接口场景管理-获取场景详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `scenarioId` | `String` | 路径 |

**返回值**: `ApiScenarioDetailDTO`

#### **`PostMapping /api/scenario/step/get/un-save`** — 接口测试-接口场景管理-获取未保存的场景步骤详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioStepDetailRequest` | Body |

**ApiScenarioStepDetailRequest 字段明细**:
  - `id`: `String` **[必填]** 步骤id *约束: @Size(max = 50, message = "{api_scenario_step.id.length_range}");*
  - `copyFromStepId`: `String` 复制的目标步骤ID
  - `resourceId`: `String` 资源id
  - `stepType`: `String` **[必填]** 步骤类型/API/CASE等 *约束: @EnumValue(enumClass = ApiScenarioStepType.class);*
  - `refType`: `String` **[必填]** 引用/复制/自定义 *约束: @EnumValue(enumClass = ApiScenarioStepRefType.class);*

**返回值**: `Object`

#### **`GetMapping /api/scenario/step/get/{stepId}`** — 接口测试-接口场景管理-获取场景步骤详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `stepId` | `String` | 路径 |

**返回值**: `Object`

#### **`PostMapping /api/scenario/step/file/copy`** — 接口测试-接口场景管理-复制步骤时，复制步骤文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioStepFileCopyRequest` | Body |

**ApiScenarioStepFileCopyRequest 字段明细**:
  - `copyFromStepId`: `String` 复制的目标步骤ID
  - `resourceId`: `String` 资源id
  - `stepType`: `String` 步骤类型/API/CASE等 *约束: @EnumValue(enumClass = ApiScenarioStepType.class);*
  - `isTempFile`: `Boolean` **[必填]** 是否是临时文件
  - `fileIds`: `List<String>` **[必填]** 文件数组

**返回值**: `Map<String, String>`

#### **`GetMapping /api/scenario/step/resource-info/{resourceId}`** — 接口测试-接口场景管理-获取步骤关联资源的信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `resourceId` | `String` | 路径 |
| `resourceType` | `String` | Query |

**返回值**: `ApiStepResourceInfo`

#### **`GetMapping /api/scenario/recover/{id}`** — 接口测试-接口场景管理-恢复场景

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/scenario/debug`** — 接口测试-接口场景管理-场景调试

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioDebugRequest` | Body |

**ApiScenarioDebugRequest 字段明细**:
  > **继承**: `ApiScenarioParseParam`
  - `id`: `String` **[必填]** id *约束: @Size(max = 50, message = "{api_scenario.id.length_range}");*
  - `reportId`: `String` 报告ID，传了可以实时获取结果，不传则不支持实时获取 *约束: @Size(max = 50);*
  - `steps`: `List<ApiScenarioStepRequest>` 步骤集合 *约束: @Valid;*
  - `projectId`: `String` **[必填]** 项目ID
  - `stepFileParam`: `Map<String, ResourceAddFileParam>` 步骤文件操作相关参数
  - `fileParam`: `ResourceAddFileParam` 场景文件操作相关参数

**返回值**: `TaskRequestDTO`

#### **`PostMapping /api/scenario/run`** — 接口测试-接口场景管理-场景执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioDebugRequest` | Body |

**ApiScenarioDebugRequest 字段明细**:
  > **继承**: `ApiScenarioParseParam`
  - `id`: `String` **[必填]** id *约束: @Size(max = 50, message = "{api_scenario.id.length_range}");*
  - `reportId`: `String` 报告ID，传了可以实时获取结果，不传则不支持实时获取 *约束: @Size(max = 50);*
  - `steps`: `List<ApiScenarioStepRequest>` 步骤集合 *约束: @Valid;*
  - `projectId`: `String` **[必填]** 项目ID
  - `stepFileParam`: `Map<String, ResourceAddFileParam>` 步骤文件操作相关参数
  - `fileParam`: `ResourceAddFileParam` 场景文件操作相关参数

**返回值**: `TaskRequestDTO`

#### **`GetMapping /api/scenario/run/{id}`** — 接口测试-接口场景管理-场景执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `reportId` | `String` | Query |

**返回值**: `TaskRequestDTO`

#### **`GetMapping /api/scenario/update-status/{id}/{status}`** — 接口测试-接口场景管理-更新状态

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `status` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/scenario/update-priority/{id}/{priority}`** — 接口测试-接口场景管理-更新等级

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `priority` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/scenario/schedule-config`** — 接口测试-接口场景管理-定时任务配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioScheduleConfigRequest` | Body |

**ApiScenarioScheduleConfigRequest 字段明细**:
  - `scenarioId`: `String` **[必填]** 场景ID *约束: @Size(min = 1, max = 50, message = "{api_scenario.id.length_range}");*
  - `enable`: `boolean` 启用/禁用
  - `cron`: `String` **[必填]** Cron表达式
  - `config`: `ApiRunModeConfigDTO` 定时任务配置

**返回值**: `String`

#### **`GetMapping /api/scenario/schedule-config-delete/{scenarioId}`** — 接口测试-接口场景管理-删除定时任务配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `scenarioId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/scenario/association/page`** — 接口测试-接口场景管理-场景引用关系列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioAssociationPageRequest` | Body |

**ApiScenarioAssociationPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `id`: `String` 场景pk *约束: @Size(min = 1, max = 50, message = "{api_scenario_step.scenario_id.length_range}");*

**返回值**: `Pager<List<ApiScenarioAssociationDTO>>`

#### **`PostMapping /api/scenario/get/system-request`** — 接口测试-接口场景管理-获取系统请求

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioSystemRequest` | Body |

**ApiScenarioSystemRequest 字段明细**:
  - `apiRequest`: `ScenarioSystemRequest` 接口的参数
  - `caseRequest`: `ScenarioSystemRequest` 用例的参数
  - `scenarioRequest`: `ScenarioSystemRequest` 场景的参数
  - `refType`: `String` **[必填]** 关联类型 COPY:复制  REF:引用 *约束: @EnumValue(enumClass = ApiScenarioStepRefType.class);*

**返回值**: `List<ApiScenarioStepDTO>`

#### **`PostMapping /api/scenario/edit/pos`** — 接口测试-接口场景管理-场景-拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PosRequest` | Body |

**PosRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目id
  - `moveId`: `String` **[必填]** 移动用例id
  - `targetId`: `String` **[必填]** 目标用例id
  - `moveMode`: `String` **[必填]** 移动类型

**返回值**: `void`

#### **`PostMapping /api/scenario/execute/page`** — 接口测试-接口场景管理-场景-获取执行历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ExecutePageRequest` | Body |

**ExecutePageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `id`: `String` **[必填]** 用例id/场景id *约束: @Size(min = 1, max = 50, message = "{api_test_case.id.length_range}");*

**返回值**: `Pager<List<ExecuteReportDTO>>`

#### **`PostMapping /api/scenario/operation-history/page`** — 接口测试-接口场景管理-场景-接口变更历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OperationHistoryRequest` | Body |

**OperationHistoryRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{operation_history.project_id.length_range}");*
  - `sourceId`: `String` **[必填]** 资源id
  - `createUser`: `String` 操作人
  - `types`: `List<String>` 操作类型
  - `modules`: `String` 操作模块

**返回值**: `Pager<List<OperationHistoryDTO>>`

#### **`PostMapping /api/scenario/transfer`** — 接口测试-接口场景管理-场景-附件-文件转存

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTransferRequest` | Body |

**ApiTransferRequest 字段明细**:
  > **继承**: `ApiFileRequest`
  - `moduleId`: `String` **[必填]** 转存的模块id
  - `originalName`: `String` **[必填]** 原始文件名

**返回值**: `String`

#### **`PostMapping /api/scenario/step/transfer`** — 接口测试-接口场景管理-场景步骤-附件-文件转存

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiTransferRequest` | Body |

**ApiTransferRequest 字段明细**:
  > **继承**: `ApiFileRequest`
  - `moduleId`: `String` **[必填]** 转存的模块id
  - `originalName`: `String` **[必填]** 原始文件名

**返回值**: `String`

#### **`GetMapping /api/scenario/transfer/options/{projectId}`** — 接口测试-接口场景管理-场景-附件-转存目录下拉框

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/scenario/get-reference`** — 接口测试-接口场景管理-场景-引用关系

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ReferenceRequest` | Body |

**ReferenceRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `resourceId`: `String` **[必填]** 资源id

**返回值**: `Pager<List<ReferenceDTO>>`

#### **`PostMapping /api/scenario/export/{type}`** — 接口测试-接口场景管理-场景-导出场景

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioBatchExportRequest` | Body |
| `type` | `String` | 路径 |

**ApiScenarioBatchExportRequest 字段明细**:
  > **继承**: `ApiScenarioBatchRequest`
  - `fileId`: `String` **[必填]** 文件id
  - `exportAllRelatedData`: `boolean`

**返回值**: `String`

#### **`PostMapping /api/scenario/import`** — 接口测试-接口场景管理-场景-导入场景

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |
| `request` | `ApiScenarioImportRequest` | Form |

**返回值**: `void`

#### **`GetMapping /api/scenario/stop/{taskId}`** — 接口测试-接口场景管理-导出-停止导出

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskId` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /api/scenario/download/file/{projectId}/{fileId}`** — 接口测试-接口场景管理-下载文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `fileId` | `String` | 路径 |
| `httpServletResponse` | `HttpServletResponse` | 参数 |

**返回值**: `void`


### ApiScenarioModuleController
**业务标签**: 接口测试-接口场景-模块

#### **`PostMapping /api/scenario/module/tree`** — 接口测试-接口场景-模块-查找模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioModuleRequest` | Body |

**ApiScenarioModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `scenarioId`: `String` 场景pk *约束: @Size(min = 1, max = 50, message = "{api_scenario_step.scenario_id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /api/scenario/module/add`** — 接口测试-接口场景-模块-添加模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ModuleCreateRequest` | Body |

**ModuleCreateRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_debug.project_id.length_range}");*
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{api_debug_module.name.length_range}");*

**返回值**: `String`

#### **`PostMapping /api/scenario/module/update`** — 接口测试-接口场景-模块-修改模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ModuleUpdateRequest` | Body |

**ModuleUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 模块ID *约束: @Size(min = 1, max = 50, message = "{api_debug_module.id.length_range}");*
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{api_debug_module.name.length_range}");*

**返回值**: `boolean`

#### **`GetMapping /api/scenario/module/delete/{id}`** — 接口测试-接口场景-模块-删除模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/scenario/module/move`** — 接口测试-接口场景-模块-移动模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `NodeMoveRequest` | Body |

**NodeMoveRequest 字段明细**:
  - `dragNodeId`: `String` **[必填]** 被拖拽的节点
  - `dropNodeId`: `String` **[必填]** 放入的节点
  - `dropPosition`: `int` 放入的位置（取值：-1，,1。  -1：dropNodeId节点之前。 1：dropNodeId节点后）

**返回值**: `void`

#### **`PostMapping /api/scenario/module/count`** — 接口测试-接口场景-模块-统计模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioModuleRequest` | Body |

**ApiScenarioModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `scenarioId`: `String` 场景pk *约束: @Size(min = 1, max = 50, message = "{api_scenario_step.scenario_id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `Map<String, Long>`

#### **`PostMapping /api/scenario/module/trash/count`** — 接口测试-接口场景-模块-统计回收站模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioModuleRequest` | Body |

**ApiScenarioModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `scenarioId`: `String` 场景pk *约束: @Size(min = 1, max = 50, message = "{api_scenario_step.scenario_id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `Map<String, Long>`

#### **`PostMapping /api/scenario/module/trash/tree`** — 接口测试-接口场景-模块-查找模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiScenarioModuleRequest` | Body |

**ApiScenarioModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `scenarioId`: `String` 场景pk *约束: @Size(min = 1, max = 50, message = "{api_scenario_step.scenario_id.length_range}");*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `List<BaseTreeNode>`


### ApiScenarioReportController
**业务标签**: 接口测试-接口报告-场景

#### **`PostMapping /api/report/scenario/page`** — 接口测试-接口报告-场景()

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiReportPageRequest` | Body |

**ApiReportPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `Pager<List<ApiScenarioReportListDTO>>`

#### **`PostMapping /api/report/scenario/rename/{id}`** — 接口测试-接口报告-场景报告重命名

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `name` | `Object` | Body |

**返回值**: `void`

#### **`GetMapping /api/report/scenario/delete/{id}`** — 接口测试-接口报告-场景报告删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/report/scenario/batch/delete`** — 接口测试-接口报告-场景报告批量删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiReportBatchRequest` | Body |

**ApiReportBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `void`

#### **`PostMapping /api/report/scenario/batch-param`** — 接口测试-接口报告-获取场景报告批量参数

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiReportBatchRequest` | Body |

**ApiReportBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `List<String>`

#### **`GetMapping /api/report/scenario/get/{id}`** — 接口测试-接口报告-报告获取

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiScenarioReportDTO`

#### **`GetMapping /api/report/scenario/share/{shareId}/{reportId}`** — 接口测试-接口报告-分享报告获取

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |

**返回值**: `ApiScenarioReportDTO`

#### **`GetMapping /api/report/scenario/get/detail/{reportId}/{stepId}`** — 接口测试-接口报告-报告详情获取

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |
| `stepId` | `String` | 路径 |

**返回值**: `List<ApiScenarioReportDetailDTO>`

#### **`GetMapping /api/report/scenario/share/detail/{shareId}/{reportId}/{stepId}`**

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |
| `stepId` | `String` | 路径 |

**返回值**: `List<ApiScenarioReportDetailDTO>`

#### **`PostMapping /api/report/scenario/export/{reportId}`** — 接口测试-场景报告-导出日志

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /api/report/scenario/batch-export`** — 接口测试-场景报告-导出日志

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiReportBatchRequest` | Body |

**ApiReportBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{api_definition.project_id.length_range}");*

**返回值**: `void`

#### **`GetMapping /api/report/scenario/task-step/{id}`** — 系统-任务中心-场景用例执行任务详情-查看(任务步骤)

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ExecTaskDetailDTO`

#### **`GetMapping /api/report/scenario/task-report/{reportId}/{stepId}`** — 系统-任务中心-场景用例执行任务详情-查看(步骤结果)

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |
| `stepId` | `String` | 路径 |

**返回值**: `List<ApiScenarioReportDetailDTO>`


### ApiScenarioSelectAssociateController
**业务标签**: 接口测试-接口场景管理-场景导入系统参数

#### **`PostMapping /api/scenario/associate/all`** — 接口场景管理-场景导入系统参数

| 参数 | 类型 | 来源 |
|------|------|------|
| `requestMap` | `Map<String, ApiScenarioSelectAssociateDTO>` | Body |

**返回值**: `List<ApiScenarioStepDTO>`


## case-management 模块

共 15 个 Controller，127 个接口


### CaseReviewController
**业务标签**: 用例管理-用例评审

#### **`PostMapping /case/review/page`** — 用例管理-用例评审-用例列表查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewPageRequest` | Body |

**返回值**: `Pager<List<CaseReviewDTO>>`

#### **`PostMapping /case/review/module/count`** — 用例管理-用例评审-统计模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewPageRequest` | Body |

**返回值**: `Map<String, Long>`

#### **`PostMapping /case/review/add`** — 用例管理-用例评审-创建用例评审

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewRequest` | Body |

**返回值**: `CaseReview`

#### **`PostMapping /case/review/copy`** — 用例管理-用例评审-复制用例评审

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewCopyRequest` | Body |

**返回值**: `CaseReview`

#### **`PostMapping /case/review/edit`** — 用例管理-用例评审-编辑用例评审

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewRequest` | Body |

**返回值**: `void`

#### **`GetMapping /case/review/user-option/{projectId}`** — 用例管理-用例评审-获取具有评审权限的用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserDTO>`

#### **`PostMapping /case/review/edit/follower`** — 用例管理-用例评审-关注/取消关注用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewFollowerRequest` | Body |

**返回值**: `void`

#### **`PostMapping /case/review/associate`** — 用例管理-用例评审-关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewAssociateRequest` | Body |

**返回值**: `void`

#### **`GetMapping /case/review/disassociate/{reviewId}/{caseId}`** — 用例管理-用例评审-取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `reviewId` | `String` | 路径 |
| `caseId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /case/review/edit/pos`** — 用例管理-用例评审-拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PosRequest` | Body |

**PosRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目id
  - `moveId`: `String` **[必填]** 移动用例id
  - `targetId`: `String` **[必填]** 目标用例id
  - `moveMode`: `String` **[必填]** 移动类型

**返回值**: `void`

#### **`GetMapping /case/review/detail/{id}`** — 用例管理-用例评审-查看评审详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `CaseReviewDTO`

#### **`PostMapping /case/review/batch/move`** — 用例管理-用例评审-批量移动用例评审

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewBatchRequest` | Body |

**返回值**: `void`

#### **`GetMapping /case/review/delete/{projectId}/{reviewId}`** — 用例管理-用例评审-删除用例评审

| 参数 | 类型 | 来源 |
|------|------|------|
| `reviewId` | `String` | 路径 |
| `projectId` | `String` | 路径 |

**返回值**: `void`


### CaseReviewFunctionalCaseController
**业务标签**: 用例管理-用例评审-评审列表-评审详情

#### **`GetMapping /case/review/detail/get-ids/{reviewId}`** — 用例管理-用例评审-评审列表-评审详情-获取已关联用例id集合(关联用例弹窗前调用)

| 参数 | 类型 | 来源 |
|------|------|------|
| `reviewId` | `String` | 路径 |

**返回值**: `List<String>`

#### **`PostMapping /case/review/detail/page`** — 用例管理-用例评审-评审列表-评审详情-已关联用例列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ReviewFunctionalCasePageRequest` | Body |

**返回值**: `Pager<List<ReviewFunctionalCaseDTO>>`

#### **`GetMapping /case/review/detail/tree/{reviewId}`** — 用例管理-用例评审-评审列表-评审详情-已关联用例列表模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `reviewId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /case/review/detail/module/count`** — 用例管理-用例评审-评审列表-评审详情-已关联用例统计模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ReviewFunctionalCasePageRequest` | Body |

**返回值**: `Map<String, Long>`

#### **`PostMapping /case/review/detail/batch/disassociate`** — 用例管理-用例评审-评审列表-评审详情-列表-批量取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BaseReviewCaseBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /case/review/detail/edit/pos`** — 用例管理-用例评审-评审列表-评审详情-列表-拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewFunctionalCasePosRequest` | Body |

**返回值**: `void`

#### **`PostMapping /case/review/detail/batch/review`** — 用例管理-用例评审-评审列表-评审详情-列表-批量评审

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BatchReviewFunctionalCaseRequest` | Body |

**返回值**: `void`

#### **`PostMapping /case/review/detail/mind/multiple/review`** — 评审详情-脑图-多人评审返回评审结果

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `MindReviewFunctionalCaseRequest` | Body |

**返回值**: `String`

#### **`PostMapping /case/review/detail/batch/edit/reviewers`** — 用例管理-用例评审-评审列表-评审详情-列表-批量修改评审人

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BatchEditReviewerRequest` | Body |

**返回值**: `void`

#### **`GetMapping /case/review/detail/reviewer/status/{reviewId}/{caseId}`** — 用例管理-用例评审-评审列表-评审详情-评审结果的气泡数据

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "评审id"` | 参数 |
| `reviewId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `` | `(description = "用例id"` | 参数 |
| `caseId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |

**返回值**: `List<OptionDTO>`

#### **`GetMapping /case/review/detail/reviewer/list/{reviewId}/{caseId}`** — 用例管理-用例评审-评审列表-评审详情-获取单个用例的评审人

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "评审id"` | 参数 |
| `reviewId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `` | `(description = "用例id"` | 参数 |
| `caseId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |

**返回值**: `List<CaseReviewFunctionalCaseUser>`

#### **`GetMapping /case/review/detail/reviewer/status/total/{reviewId}/{caseId}`** — 用例管理-用例评审-评审列表-评审详情-评审总结过结果和每个评审人最后结果气泡数据

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "评审id"` | 参数 |
| `reviewId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `` | `(description = "用例id"` | 参数 |
| `caseId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |

**返回值**: `ReviewerAndStatusDTO`


### CaseReviewModuleController
**业务标签**: 用例管理-用例评审-模块

#### **`GetMapping /case/review/module/tree/{projectId}`** — 用例管理-用例评审-模块-获取模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /case/review/module/add`** — 用例管理-用例评审-模块-添加模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewModuleCreateRequest` | Body |

**返回值**: `String`

#### **`PostMapping /case/review/module/update`** — 用例管理-用例评审-模块-修改模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CaseReviewModuleUpdateRequest` | Body |

**返回值**: `void`

#### **`PostMapping /case/review/module/move`** — 用例管理-用例评审-模块-移动模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `NodeMoveRequest` | Body |

**NodeMoveRequest 字段明细**:
  - `dragNodeId`: `String` **[必填]** 被拖拽的节点
  - `dropNodeId`: `String` **[必填]** 放入的节点
  - `dropPosition`: `int` 放入的位置（取值：-1，,1。  -1：dropNodeId节点之前。 1：dropNodeId节点后）

**返回值**: `void`

#### **`GetMapping /case/review/module/delete/{moduleId}`** — 用例管理-用例评审-模块-删除模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleId` | `String` | 路径 |

**返回值**: `void`


### FunctionalCaseAIController
**业务标签**: 用例管理-功能用例-AI生成用例

#### **`GetMapping /functional/case/ai/get/config`** — 用例管理-功能用例-获取用户AI提示词

**无入参**

**返回值**: `FunctionalCaseAIConfigDTO`

#### **`PostMapping /functional/case/ai/save/config`** — 用例管理-功能用例-保存用户AI提示词

| 参数 | 类型 | 来源 |
|------|------|------|
| `configDTO` | `FunctionalCaseAIConfigDTO` | Body |

**FunctionalCaseAIConfigDTO 字段明细**:
  - `designConfig`: `FunctionalCaseAIDesignConfigDTO` AI模型用例生成方法提示词配置
  - `templateConfig`: `FunctionalCaseAITemplateConfigDTO` AI模型生成用例的提示词配置

**返回值**: `void`

#### **`PostMapping /functional/case/ai/transform`** — 用例管理-功能用例-单条AI数据生成用例对象

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AIChatRequest` | Body |

**AIChatRequest 字段明细**:
  - `prompt`: `String` **[必填]** 提示词
  - `chatModelId`: `String` **[必填]** 模型ID
  - `conversationId`: `String` **[必填]** 对话ID
  - `organizationId`: `String` **[必填]** 组织ID

**返回值**: `FunctionalCaseAiDTO`

#### **`PostMapping /functional/case/ai/chat`** — 用例管理-功能用例-AI对话

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AIChatRequest` | Body |

**AIChatRequest 字段明细**:
  - `prompt`: `String` **[必填]** 提示词
  - `chatModelId`: `String` **[必填]** 模型ID
  - `conversationId`: `String` **[必填]** 对话ID
  - `organizationId`: `String` **[必填]** 组织ID

**返回值**: `String`

#### **`PostMapping /functional/case/ai/batch/save`** — 用例管理-功能用例-多条AI数据生成用例对象

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseAIChatRequest` | Body |

**返回值**: `void`


### FunctionalCaseAttachmentController
**业务标签**: 用例管理-功能用例-附件

#### **`PostMapping /attachment/page`** — 用例管理-功能用例-附件-关联文件列表分页接口

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileMetadataTableRequest` | Body |

**FileMetadataTableRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `moduleIds`: `List<String>` 模块ID(根据模块树查询时要把当前节点以及子节点都放在这里。)
  - `fileType`: `String` 文件类型
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<FileInformationResponse>>`

#### **`PostMapping /attachment/preview`** — 用例管理-功能用例-附件/富文本(原图/文件)-文件预览

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseFileRequest` | Body |

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /attachment/download`** — 用例管理-功能用例-附件/富文本(原图/文件)-文件下载

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseFileRequest` | Body |

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /attachment/check-update`** — 用例管理-功能用例-附件-检查文件是否存在更新

| 参数 | 类型 | 来源 |
|------|------|------|
| `fileIds` | `List<String>` | Body |

**返回值**: `List<String>`

#### **`GetMapping /attachment/update/{projectId}/{id}`** — 用例管理-功能用例-附件-更新文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `String`

#### **`PostMapping /attachment/transfer`** — 用例管理-功能用例-附件-文件转存

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AttachmentTransferRequest` | Body |

**返回值**: `String`

#### **`PostMapping /attachment/upload/file`** — 用例管理-功能用例-上传文件并关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseAssociationFileRequest` | Form |
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |

**返回值**: `void`

#### **`PostMapping /attachment/delete/file`** — 用例管理-功能用例-删除文件并取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseDeleteFileRequest` | Body |

**返回值**: `void`

#### **`GetMapping /attachment/options/{projectId}`** — 用例管理-功能用例-附件-转存目录下拉框

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /attachment/upload/temp/file`** — 用例管理-功能用例-上传富文本里所需的文件资源，并返回文件ID

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`GetMapping /attachment/download/file/{projectId}/{fileId}/{compressed}`** — 用例管理-功能用例-预览上传的富文本里所需的文件资源原图

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `fileId` | `String` | 路径 |
| `` | `(description = "查看压缩图片"` | 参数 |
| `compressed` | `requiredMode = Schema.RequiredMode.REQUIRED) boolean` | 路径 |

**返回值**: `ResponseEntity<byte[]>`


### FunctionalCaseCommentController
**业务标签**: 用例管理-功能用例-用例评论

#### **`PostMapping /functional/case/comment/save`** — 用例管理-功能用例-用例评论-创建评论

| 参数 | 类型 | 来源 |
|------|------|------|
| `functionalCaseCommentRequest` | `FunctionalCaseCommentRequest` | Body |

**返回值**: `FunctionalCaseComment`

#### **`PostMapping /functional/case/comment/update`** — 用例管理-功能用例-用例评论-修改评论

| 参数 | 类型 | 来源 |
|------|------|------|
| `functionalCaseCommentRequest` | `FunctionalCaseCommentRequest` | Body |

**返回值**: `FunctionalCaseComment`

#### **`GetMapping /functional/case/comment/delete/{commentId}`** — 用例管理-功能用例-用例评论-删除评论

| 参数 | 类型 | 来源 |
|------|------|------|
| `commentId` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /functional/case/comment/get/list/{caseId}`** — 用例管理-功能用例-用例评论-获取用例评论

| 参数 | 类型 | 来源 |
|------|------|------|
| `caseId` | `String` | 路径 |

**返回值**: `List<FunctionalCaseCommentDTO>`


### FunctionalCaseController
**业务标签**: 用例管理-功能用例

#### **`GetMapping /functional/case/default/template/field/{projectId}`** — 用例管理-功能用例-获取默认模板自定义字段

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `TemplateDTO`

#### **`PostMapping /functional/case/add`** — 用例管理-功能用例-新增用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseAddRequest` | Form |
| `` | `(value = "files"` | Form |
| `files` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `FunctionalCase`

#### **`GetMapping /functional/case/detail/{id}`** — 用例管理-功能用例-查看用例详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `FunctionalCaseDetailDTO`

#### **`PostMapping /functional/case/update`** — 用例管理-功能用例-更新用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseEditRequest` | Form |
| `` | `(value = "files"` | Form |
| `files` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `FunctionalCase`

#### **`PostMapping /functional/case/edit/follower`** — 用例管理-功能用例-关注/取消关注用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseFollowerRequest` | Body |

**返回值**: `void`

#### **`GetMapping /functional/case/version/{id}`** — 用例管理-功能用例-版本信息(用例是否存在多版本)

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `List<FunctionalCaseVersionDTO>`

#### **`PostMapping /functional/case/delete`** — 用例管理-功能用例-删除用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseDeleteRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/page`** — 用例管理-功能用例-用例列表查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCasePageRequest` | Body |

**返回值**: `Pager<List<FunctionalCasePageDTO>>`

#### **`PostMapping /functional/case/module/count`** — 用例管理-功能用例-统计模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCasePageRequest` | Body |

**返回值**: `Map<String, Long>`

#### **`PostMapping /functional/case/batch/delete-to-gc`** — 用例管理-功能用例-批量删除用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseBatchRequest` | Body |

**返回值**: `void`

#### **`GetMapping /functional/case/custom/field/{projectId}`** — 用例管理-功能用例-获取表头自定义字段(高级搜索中的自定义字段)

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<CustomFieldOptions>`

#### **`PostMapping /functional/case/batch/move`** — 用例管理-功能用例-批量移动用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseBatchMoveRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/batch/copy`** — 用例管理-功能用例-批量复制用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseBatchMoveRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/batch/edit`** — 用例管理-功能用例-批量编辑用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseBatchEditRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/edit/pos`** — 用例管理-功能用例-拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PosRequest` | Body |

**PosRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目id
  - `moveId`: `String` **[必填]** 移动用例id
  - `targetId`: `String` **[必填]** 目标用例id
  - `moveMode`: `String` **[必填]** 移动类型

**返回值**: `void`

#### **`GetMapping /functional/case/download/excel/template/{projectId}`** — 用例管理-功能用例-excel导入-下载模板

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `response` | `HttpServletResponse` | 参数 |

**返回值**: `void`

#### **`PostMapping /functional/case/pre-check/excel`** — 用例管理-功能用例-excel导入检查

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseImportRequest` | Form |
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |

**返回值**: `FunctionalCaseImportResponse`

#### **`PostMapping /functional/case/pre-check/xmind`** — 用例管理-功能用例-xmind导入检查

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseImportRequest` | Form |
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |

**返回值**: `FunctionalCaseImportResponse`

#### **`PostMapping /functional/case/import/excel`** — 用例管理-功能用例-excel导入

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseImportRequest` | Form |
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |

**返回值**: `FunctionalCaseImportResponse`

#### **`PostMapping /functional/case/import/xmind`** — 用例管理-功能用例-xmind导入

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseImportRequest` | Form |
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |

**返回值**: `FunctionalCaseImportResponse`

#### **`PostMapping /functional/case/operation-history`** — 用例管理-功能用例-变更历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OperationHistoryRequest` | Body |

**OperationHistoryRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{operation_history.project_id.length_range}");*
  - `sourceId`: `String` **[必填]** 资源id
  - `createUser`: `String` 操作人
  - `types`: `List<String>` 操作类型
  - `modules`: `String` 操作模块

**返回值**: `Pager<List<OperationHistoryDTO>>`

#### **`PostMapping /functional/case/export/excel`** — 用例管理-功能用例-excel导出

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseExportRequest` | Body |

**返回值**: `String`

#### **`GetMapping /functional/case/stop/{taskId}`** — 用例管理-功能用例-导出-停止导出

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskId` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /functional/case/download/xmind/template/{projectId}`** — 用例管理-功能用例-xmind导入-下载模板

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `response` | `HttpServletResponse` | 参数 |

**返回值**: `void`

#### **`GetMapping /functional/case/export/columns/{projectId}`** — 用例管理-获取导出字段配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `FunctionalCaseExportColumns`

#### **`GetMapping /functional/case/download/file/{projectId}/{fileId}`** — 用例管理-功能用例-下载文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `fileId` | `String` | 路径 |

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /functional/case/export/xmind`** — 用例管理-功能用例-xmind导出

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseExportRequest` | Body |

**返回值**: `String`

#### **`GetMapping /functional/case/check/export-task`** — 用例管理-功能用例-导出任务校验

**无入参**

**返回值**: `ExportTaskDTO`


### FunctionalCaseDemandController
**业务标签**: 用例管理-功能用例-关联需求

#### **`PostMapping /functional/case/demand/page`** — 用例管理-功能用例-关联需求-获取已关联的需求列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `QueryDemandListRequest` | Body |

**返回值**: `Pager<List<FunctionalDemandDTO>>`

#### **`PostMapping /functional/case/demand/add`** — 用例管理-功能用例详情-关联需求-新增/关联需求

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseDemandRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/demand/update`** — 用例管理-功能用例-关联需求-更新需求

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseDemandRequest` | Body |

**返回值**: `void`

#### **`GetMapping /functional/case/demand/cancel/{id}`** — 用例管理-功能用例-关联需求-取消关联需求

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /functional/case/demand/batch/relevance`** — 用例管理-功能用例列表-关联需求-批量关联新增需求

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseDemandBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/demand/third/list/page`** — 用例管理-功能用例-关联需求-获取三方需求列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalThirdDemandPageRequest` | Body |

**返回值**: `PluginPager<PlatformDemandDTO>`


### FunctionalCaseMinderController
**业务标签**: 用例管理-功能用例-脑图

#### **`PostMapping /functional/mind/case/tree`** — 用例管理-功能用例-脑图-获取空白节点和模块的组合树

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseMindTreeRequest` | Body |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /functional/mind/case/list`** — 用例管理-功能用例-脑图用例跟根据模块ID查询列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseMindRequest` | Body |

**返回值**: `Pager<List<FunctionalMinderTreeDTO>>`

#### **`PostMapping /functional/mind/case/edit`** — 脑图保存

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseMinderEditRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/mind/case/review/list`** — 用例管理-功能用例-脑图用例跟根据模块ID查询列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseReviewMindRequest` | Body |

**返回值**: `Pager<List<FunctionalMinderTreeDTO>>`

#### **`PostMapping /functional/mind/case/plan/list`** — 测试计划-功能用例-脑图用例跟根据模块ID查询列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCasePlanMindRequest` | Body |

**返回值**: `Pager<List<FunctionalMinderTreeDTO>>`

#### **`PostMapping /functional/mind/case/collection/list`** — 测试集-功能用例-脑图用例跟根据测试集ID查询列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseCollectionMindRequest` | Body |

**返回值**: `Pager<List<FunctionalMinderTreeDTO>>`


### FunctionalCaseModuleController
**业务标签**: 用例管理-功能用例-模块

#### **`GetMapping /functional/case/module/tree/{projectId}`** — 用例管理-功能用例-模块-获取模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /functional/case/module/add`** — 用例管理-功能用例-模块-添加模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseModuleCreateRequest` | Body |

**返回值**: `String`

#### **`PostMapping /functional/case/module/update`** — 用例管理-功能用例-模块-修改模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseModuleUpdateRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/module/move`** — 用例管理-功能用例-模块-移动模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `NodeMoveRequest` | Body |

**NodeMoveRequest 字段明细**:
  - `dragNodeId`: `String` **[必填]** 被拖拽的节点
  - `dropNodeId`: `String` **[必填]** 放入的节点
  - `dropPosition`: `int` 放入的位置（取值：-1，,1。  -1：dropNodeId节点之前。 1：dropNodeId节点后）

**返回值**: `void`

#### **`GetMapping /functional/case/module/delete/{moduleId}`** — 用例管理-功能用例-模块-删除模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleId` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /functional/case/module/trash/tree/{projectId}`** — 用例管理-功能用例-回收站-模块-获取模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`


### FunctionalCaseRelationshipController
**业务标签**: 用例管理-功能用例-用例详情-前后置关系

#### **`GetMapping /functional/case/relationship/get-ids/{caseId}`** — 用例管理-功能用例-用例详情-前后置关系-获取已关联用例id集合(关联用例弹窗前调用)

| 参数 | 类型 | 来源 |
|------|------|------|
| `caseId` | `String` | 路径 |

**返回值**: `List<String>`

#### **`PostMapping /functional/case/relationship/relate/page`** — 用例管理-功能用例-用例详情-前后置关系-弹窗获取用例列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `RelationshipPageRequest` | Body |

**返回值**: `Pager<List<FunctionalCasePageDTO>>`

#### **`PostMapping /functional/case/relationship/add`** — 用例管理-功能用例-用例详情-前后置关系-添加前后置关系

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `RelationshipAddRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/relationship/page`** — 用例管理-功能用例-用例详情-前后置关系-列表查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `RelationshipRequest` | Body |

**返回值**: `Pager<List<FunctionalCaseRelationshipDTO>>`

#### **`PostMapping /functional/case/relationship/delete`** — 用例管理-功能用例-用例详情-前后置关系-取消关联

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `RelationshipDeleteRequest` | Body |

**返回值**: `void`


### FunctionalCaseReviewController
**业务标签**: 用例管理-功能用例-评审

#### **`PostMapping /functional/case/review/page`** — 用例管理-功能用例-评审-列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseReviewListRequest` | Body |

**返回值**: `Pager<List<FunctionalCaseReviewDTO>>`

#### **`GetMapping /functional/case/review/comment/{caseId}`** — 用例管理-功能用例-评审-获取评审评论历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `caseId` | `String` | 路径 |

**返回值**: `List<CaseReviewHistoryDTO>`


### FunctionalCaseTrashController
**业务标签**: 用例管理-功能用例-回收站

#### **`PostMapping /functional/case/trash/page`** — 用例管理-功能用例-回收站-用例列表查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCasePageRequest` | Body |

**返回值**: `Pager<List<FunctionalCasePageDTO>>`

#### **`PostMapping /functional/case/trash/module/count`** — 用例管理-功能用例-回收站-模块树统计用例数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCasePageRequest` | Body |

**返回值**: `Map<String, Long>`

#### **`GetMapping /functional/case/trash/recover/{id}`** — 用例管理-功能用例-回收站-恢复用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /functional/case/trash/batch/recover`** — 用例管理-功能用例-回收站-批量恢复用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseBatchRequest` | Body |

**返回值**: `void`

#### **`GetMapping /functional/case/trash/delete/{id}`** — 用例管理-功能用例-回收站-彻底删除用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /functional/case/trash/batch/delete`** — 用例管理-功能用例-回收站-批量彻底删除用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseBatchRequest` | Body |

**返回值**: `void`


### FunctionalTestCaseController
**业务标签**: 用例管理-功能用例-关联其他用例

#### **`PostMapping /functional/case/test/associate/case/page`** — 用例管理-功能用例-关联其他用例-获取需要关联的用例列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestCasePageProviderRequest` | Body |

**返回值**: `Pager<List<TestCaseProviderDTO>>`

#### **`PostMapping /functional/case/test/associate/case/module/count`** — 用例管理-功能用例-关联其他用例-统计需要关联用例模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestCasePageProviderRequest` | Body |

**返回值**: `Map<String, Long>`

#### **`PostMapping /functional/case/test/associate/case/module/tree`** — 用例管理-功能用例-关联其他用例-获取需要关联的用例模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AssociateCaseModuleRequest` | Body |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /functional/case/test/associate/case`** — 用例管理-功能用例-关联其他用例-关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AssociateOtherCaseRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/test/disassociate/case`** — 用例管理-功能用例-关联其他用例-取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `DisassociateOtherCaseRequest` | Body |

**返回值**: `void`

#### **`PostMapping /functional/case/test/has/associate/case/page`** — 用例管理-功能用例-关联其他用例-获取已关联的用例列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseTestRequest` | Body |

**返回值**: `Pager<List<FunctionalCaseTestDTO>>`

#### **`PostMapping /functional/case/test/associate/bug/page`** — 用例管理-功能用例-关联其他用例-获取缺陷列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugPageProviderRequest` | Body |

**返回值**: `Pager<List<BugProviderDTO>>`

#### **`PostMapping /functional/case/test/associate/bug`** — 用例管理-功能用例-关联其他用例-关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AssociateBugRequest` | Body |

**返回值**: `void`

#### **`GetMapping /functional/case/test/disassociate/bug/{id}`** — 用例管理-功能用例-关联其他用例-取消关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /functional/case/test/has/associate/bug/page`** — 用例管理-功能用例-关联其他用例-获取已关联的缺陷列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AssociateBugPageRequest` | Body |

**返回值**: `Pager<List<BugProviderDTO>>`

#### **`PostMapping /functional/case/test/has/associate/plan/page`** — 用例管理-功能用例-关联其他用例-获取已关联的测试计划列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AssociatePlanPageRequest` | Body |

**返回值**: `Pager<List<FunctionalCaseTestPlanDTO>>`

#### **`GetMapping /functional/case/test/plan/comment/{caseId}`** — 用例管理-功能用例-测试计划-获取执行评论历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `caseId` | `String` | 路径 |

**返回值**: `List<TestPlanCaseExecuteHistoryDTO>`


### ReviewFunctionalCaseController
**业务标签**: 用例管理-用例评审-评审功能用例

#### **`PostMapping /review/functional/case/save`** — 用例管理-用例评审-评审功能用例-提交评审

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ReviewFunctionalCaseRequest` | Body |

**返回值**: `void`

#### **`GetMapping /review/functional/case/get/list/{reviewId}/{caseId}`** — 用例管理-用例评审-评审功能用例-获取用例评审历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `reviewId` | `String` | 路径 |
| `caseId` | `String` | 路径 |

**返回值**: `List<CaseReviewHistoryDTO>`

#### **`PostMapping /review/functional/case/upload/temp/file`** — 用例管理-用例评审-上传富文本里所需的文件资源，并返回文件ID

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`PostMapping /review/functional/case/preview`** — 用例管理-用例评审-附件/富文本(原图/文件)-文件预览

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseFileRequest` | Body |

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /review/functional/case/download`** — 用例管理-功能用例-附件/富文本(原图/文件)-文件下载

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCaseFileRequest` | Body |

**返回值**: `ResponseEntity<byte[]>`

#### **`GetMapping /review/functional/case/download/file/{projectId}/{fileId}/{compressed}`** — 用例管理-功能用例-预览上传的富文本里所需的文件资源原图

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `fileId` | `String` | 路径 |
| `compressed` | `boolean` | 路径 |

**返回值**: `ResponseEntity<byte[]>`


## bug-management 模块

共 6 个 Controller，50 个接口


### BugAttachmentController
**业务标签**: 缺陷管理-附件

#### **`GetMapping /bug/attachment/list/{bugId}`** — 缺陷管理-附件-列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `bugId` | `String` | 路径 |

**返回值**: `List<BugFileDTO>`

#### **`PostMapping /bug/attachment/file/page`** — 缺陷管理-附件-关联文件库文件列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileMetadataTableRequest` | Body |

**FileMetadataTableRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `moduleIds`: `List<String>` 模块ID(根据模块树查询时要把当前节点以及子节点都放在这里。)
  - `fileType`: `String` 文件类型
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<FileInformationResponse>>`

#### **`PostMapping /bug/attachment/upload`** — 缺陷管理-附件-上传/关联文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugUploadFileRequest` | Form |
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |

**返回值**: `void`

#### **`PostMapping /bug/attachment/delete`** — 缺陷管理-附件-删除/取消关联文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugDeleteFileRequest` | Body |

**BugDeleteFileRequest 字段明细**:
  - `bugId`: `String` **[必填]** 缺陷ID
  - `projectId`: `String` **[必填]** 项目ID
  - `refId`: `String` 文件关系ID
  - `associated`: `Boolean` 是否关联

**返回值**: `void`

#### **`PostMapping /bug/attachment/preview`** — 缺陷管理-附件-预览

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugFileSourceRequest` | Body |

**BugFileSourceRequest 字段明细**:
  - `bugId`: `String` 缺陷ID
  - `projectId`: `String` **[必填]** 项目ID
  - `fileId`: `String` 文件关系ID
  - `associated`: `Boolean` 是否关联

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /bug/attachment/download`** — 缺陷管理-附件-下载

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugFileSourceRequest` | Body |

**BugFileSourceRequest 字段明细**:
  - `bugId`: `String` 缺陷ID
  - `projectId`: `String` **[必填]** 项目ID
  - `fileId`: `String` 文件关系ID
  - `associated`: `Boolean` 是否关联

**返回值**: `ResponseEntity<byte[]>`

#### **`GetMapping /bug/attachment/transfer/options/{projectId}`** — 缺陷管理-附件-转存文件库模块集合

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /bug/attachment/transfer`** — 缺陷管理-附件-本地文件转存

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugFileTransferRequest` | Body |

**BugFileTransferRequest 字段明细**:
  > **继承**: `BugFileSourceRequest`
  - `moduleId`: `String` **[必填]** 转存的模块id
  - `fileName`: `String` 文件别名

**返回值**: `String`

#### **`PostMapping /bug/attachment/check-update`** — 缺陷管理-附件-检查关联文件集合是否存在更新

| 参数 | 类型 | 来源 |
|------|------|------|
| `fileIds` | `List<String>` | Body |

**返回值**: `List<String>`

#### **`PostMapping /bug/attachment/update`** — 缺陷管理-附件-更新关联文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugDeleteFileRequest` | Body |

**BugDeleteFileRequest 字段明细**:
  - `bugId`: `String` **[必填]** 缺陷ID
  - `projectId`: `String` **[必填]** 项目ID
  - `refId`: `String` 文件关系ID
  - `associated`: `Boolean` 是否关联

**返回值**: `String`

#### **`PostMapping /bug/attachment/upload/md/file`** — 缺陷管理-富文本附件-上传

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`GetMapping /bug/attachment/preview/md/{projectId}/{fileId}/{compressed}`** — 缺陷管理-富文本缩略图-预览

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `fileId` | `String` | 路径 |
| `compressed` | `boolean` | 路径 |

**返回值**: `ResponseEntity<byte[]>`


### BugCommentController
**业务标签**: 缺陷管理-评论

#### **`GetMapping /bug/comment/get/{bugId}`** — 缺陷管理-评论-获取评论集合

| 参数 | 类型 | 来源 |
|------|------|------|
| `bugId` | `String` | 路径 |

**返回值**: `List<BugCommentDTO>`

#### **`PostMapping /bug/comment/add`** — 缺陷管理-评论-新增/回复评论

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugCommentEditRequest` | Body |

**BugCommentEditRequest 字段明细**:
  - `id`: `String` **[必填]** 评论ID
  - `bugId`: `String` 缺陷ID
  - `replyUser`: `String` 回复人
  - `notifier`: `String` 通知人, @名称展示, 以用户ID';'分隔
  - `parentId`: `String` 父评论ID
  - `content`: `String` 评论内容
  - `event`: `String` **[必填]** 任务事件(仅评论: ’COMMENT‘; 评论并@: ’AT‘; 回复评论/回复并@: ’REPLY‘;)
  - `richTextTmpFileIds`: `List<String>` 富文本临时文件ID

**返回值**: `BugComment`

#### **`PostMapping /bug/comment/update`** — 缺陷管理-评论-编辑评论

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugCommentEditRequest` | Body |

**BugCommentEditRequest 字段明细**:
  - `id`: `String` **[必填]** 评论ID
  - `bugId`: `String` 缺陷ID
  - `replyUser`: `String` 回复人
  - `notifier`: `String` 通知人, @名称展示, 以用户ID';'分隔
  - `parentId`: `String` 父评论ID
  - `content`: `String` 评论内容
  - `event`: `String` **[必填]** 任务事件(仅评论: ’COMMENT‘; 评论并@: ’AT‘; 回复评论/回复并@: ’REPLY‘;)
  - `richTextTmpFileIds`: `List<String>` 富文本临时文件ID

**返回值**: `BugComment`

#### **`GetMapping /bug/comment/delete/{commentId}`** — 缺陷管理-评论-删除评论

| 参数 | 类型 | 来源 |
|------|------|------|
| `commentId` | `String` | 路径 |

**返回值**: `void`


### BugController
**业务标签**: 缺陷管理

#### **`GetMapping /bug/current-platform/{projectId}`** — 缺陷管理-列表-获取当前项目所属平台

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `String`

#### **`GetMapping /bug/header/custom-field/{projectId}`** — 缺陷管理-列表-获取表头自定义字段集合

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<TemplateCustomFieldDTO>`

#### **`GetMapping /bug/header/columns-option/{projectId}`** — 缺陷管理-列表-获取表头状态选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `BugColumnsOptionDTO`

#### **`PostMapping /bug/page`** — 缺陷管理-列表-分页获取缺陷列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugPageRequest` | Body |

**BugPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目ID
  - `useTrash`: `boolean` 是否回收站, 后台默认设置
  - `todoParam`: `BugTodoRequest` 待办参数: 后台默认设置

**返回值**: `Pager<List<BugDTO>>`

#### **`PostMapping /bug/add`** — 缺陷管理-列表-创建缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugEditRequest` | Form |
| `` | `(value = "files"` | Form |
| `files` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `Bug`

#### **`PostMapping /bug/update`** — 缺陷管理-列表-编辑缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugEditRequest` | Form |
| `` | `(value = "files"` | Form |
| `files` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `Bug`

#### **`GetMapping /bug/check-exist/{id}`** — 缺陷管理-列表-校验缺陷是否存在

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `boolean`

#### **`GetMapping /bug/get/{id}`** — 缺陷管理-列表-查看缺陷(详情&&编辑&&复制)

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `BugDetailDTO`

#### **`GetMapping /bug/delete/{id}`** — 缺陷管理-列表-删除缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /bug/sync/{projectId}`** — 缺陷管理-列表-同步缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /bug/sync/all`** — 缺陷管理-列表-同步缺陷(区间)

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugSyncRequest` | Body |

**BugSyncRequest 字段明细**:
  - `projectId`: `String` 项目ID
  - `pre`: `Boolean` 创建时间前或后
  - `createTime`: `Long` 创建时间

**返回值**: `void`

#### **`GetMapping /bug/sync/check/{projectId}`** — 缺陷管理-列表-校验缺陷同步状态

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `BugSyncResult`

#### **`GetMapping /bug/export/columns/{projectId}`** — 缺陷管理-列表-获取导出字段配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `BugExportColumns`

#### **`PostMapping /bug/export`** — 缺陷管理-列表-批量导出缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugExportRequest` | Body |

**BugExportRequest 字段明细**:
  > **继承**: `BugBatchRequest`
  - `exportColumns`: `List<BugExportColumn>` **[必填]** 导出的字段

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /bug/batch-delete`** — 缺陷管理-列表-批量删除缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugBatchRequest` | Body |

**BugBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` 项目ID
  - `useTrash`: `boolean` 是否回收站
  - `sort`: `String` 排序参数

**返回值**: `void`

#### **`PostMapping /bug/batch-update`** — 缺陷管理-列表-批量编辑缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugBatchUpdateRequest` | Body |

**BugBatchUpdateRequest 字段明细**:
  > **继承**: `BugBatchRequest`
  - `tags`: `List<String>` 标签内容
  - `append`: `boolean` 是否追加
  - `clear`: `boolean` 是否清空
  - `updateUser`: `String` 更新人
  - `updateTime`: `Long` 更新时间

**返回值**: `void`

#### **`PostMapping /bug/edit/pos`** — 缺陷管理-列表-拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PosRequest` | Body |

**PosRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目id
  - `moveId`: `String` **[必填]** 移动用例id
  - `targetId`: `String` **[必填]** 目标用例id
  - `moveMode`: `String` **[必填]** 移动类型

**返回值**: `void`

#### **`GetMapping /bug/template/option/{projectId}`** — 缺陷管理-详情-获取当前项目模板选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<ProjectTemplateOptionDTO>`

#### **`PostMapping /bug/template/detail`** — 缺陷管理-详情-获取模板详情内容

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugTemplateRequest` | Body |

**BugTemplateRequest 字段明细**:
  - `id`: `String` 模板ID
  - `projectId`: `String` 项目ID
  - `fromStatusId`: `String` 缺陷当前状态ID
  - `platformBugKey`: `String` 缺陷第三方平台Key
  - `showLocal`: `Boolean` 是否展示本地的模板详情

**返回值**: `TemplateDTO`

#### **`GetMapping /bug/follow/{id}`** — 缺陷管理-详情-关注缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /bug/unfollow/{id}`** — 缺陷管理-详情-取消关注缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`


### BugHistoryController
**业务标签**: 缺陷管理-变更历史

#### **`PostMapping /bug/history/page`** — 缺陷管理-变更历史-列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OperationHistoryRequest` | Body |

**OperationHistoryRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{operation_history.project_id.length_range}");*
  - `sourceId`: `String` **[必填]** 资源id
  - `createUser`: `String` 操作人
  - `types`: `List<String>` 操作类型
  - `modules`: `String` 操作模块

**返回值**: `Pager<List<OperationHistoryDTO>>`


### BugRelateCaseController
**业务标签**: 缺陷管理-关联用例

#### **`PostMapping /bug/case/un-relate/page`** — 缺陷管理-关联用例-未关联用例-列表分页

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestCasePageProviderRequest` | Body |

**返回值**: `Pager<List<TestCaseProviderDTO>>`

#### **`PostMapping /bug/case/un-relate/module/count`** — 缺陷管理-关联用例-未关联用例-模块树数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AssociateCaseModuleRequest` | Body |

**返回值**: `Map<String, Long>`

#### **`PostMapping /bug/case/un-relate/module/tree`** — 缺陷管理-关联用例-未关联用例-模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AssociateCaseModuleRequest` | Body |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /bug/case/relate`** — 缺陷管理-关联用例-关联

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AssociateOtherCaseRequest` | Body |

**返回值**: `void`

#### **`PostMapping /bug/case/page`** — 缺陷管理-关联用例-列表分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugRelatedCasePageRequest` | Body |

**BugRelatedCasePageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `bugId`: `String` 缺陷ID

**返回值**: `Pager<List<BugRelateCaseDTO>>`

#### **`GetMapping /bug/case/un-relate/{id}`** — 缺陷管理-关联用例-取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /bug/case/check-permission/{projectId}/{caseType}`** — 缺陷管理-关联用例-查看用例权限校验

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `caseType` | `String` | 路径 |

**返回值**: `BugCaseCheckResult`


### BugTrashController
**业务标签**: 缺陷管理-回收站

#### **`PostMapping /bug/trash/page`** — 缺陷管理-回收站-获取缺陷列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugPageRequest` | Body |

**BugPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目ID
  - `useTrash`: `boolean` 是否回收站, 后台默认设置
  - `todoParam`: `BugTodoRequest` 待办参数: 后台默认设置

**返回值**: `Pager<List<BugDTO>>`

#### **`GetMapping /bug/trash/recover/{id}`** — 缺陷管理-回收站-恢复

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /bug/trash/delete/{id}`** — 缺陷管理-回收站-彻底删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /bug/trash/batch-recover`** — 缺陷管理-回收站-批量恢复

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugBatchRequest` | Body |

**BugBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` 项目ID
  - `useTrash`: `boolean` 是否回收站
  - `sort`: `String` 排序参数

**返回值**: `void`

#### **`PostMapping /bug/trash/batch-delete`** — 缺陷管理-回收站-批量彻底删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugBatchRequest` | Body |

**BugBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` 项目ID
  - `useTrash`: `boolean` 是否回收站
  - `sort`: `String` 排序参数

**返回值**: `void`


## test-plan 模块

共 13 个 Controller，143 个接口


### TestPlanApiCaseController
**业务标签**: 测试计划接口用例

#### **`PostMapping /test-plan/api/case/sort`** — 测试计划功能用例-功能用例拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ResourceSortRequest` | Body |

**ResourceSortRequest 字段明细**:
  > **继承**: `PosRequest`
  - `testCollectionId`: `String` **[必填]** 测试集ID

**返回值**: `TestPlanOperationResponse`

#### **`PostMapping /test-plan/api/case/page`** — 测试计划-已关联接口用例列表分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiCaseRequest` | Body |

**TestPlanApiCaseRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `collectionId`: `String` 计划集id
  - `apiDefinitionId`: `String` 接口pk *约束: @Size(max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` 项目ID *约束: @Size(max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本来源 *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `nullExecutorKey`: `boolean` 是否包含空执行人

**返回值**: `Pager<List<TestPlanApiCasePageResponse>>`

#### **`PostMapping /test-plan/api/case/module/count`** — 测试计划-已关联接口用例模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiCaseModuleRequest` | Body |

**返回值**: `Map<String, Long>`

#### **`PostMapping /test-plan/api/case/tree`** — 测试计划-已关联接口用例列表模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiCaseTreeRequest` | Body |

**TestPlanApiCaseTreeRequest 字段明细**:
  - `testPlanId`: `String` **[必填]** 测试计划id

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /test-plan/api/case/disassociate`** — 测试计划-计划详情-接口用例列表-取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanDisassociationRequest` | Body |

**TestPlanDisassociationRequest 字段明细**:
  - `testPlanId`: `String` 测试计划ID
  - `id`: `String` 测试计划用例关系ID

**返回值**: `TestPlanAssociationResponse`

#### **`PostMapping /test-plan/api/case/batch/disassociate`** — 测试计划-计划详情-列表-批量取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiCaseBatchRequest` | Body |

**TestPlanApiCaseBatchRequest 字段明细**:
  > **继承**: `BasePlanCaseBatchRequest`
  - `protocols`: `List<String>` 接口协议

**返回值**: `TestPlanAssociationResponse`

#### **`PostMapping /test-plan/api/case/batch/update/executor`** — 测试计划-计划详情-接口用例列表-批量更新执行人

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiCaseUpdateRequest` | Body |

**TestPlanApiCaseUpdateRequest 字段明细**:
  > **继承**: `TestPlanApiCaseBatchRequest`
  - `userId`: `String` **[必填]** 执行人id

**返回值**: `void`

#### **`GetMapping /test-plan/api/case/run/{id}`** — 用例执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `reportId` | `String` | Query |

**返回值**: `TaskRequestDTO`

#### **`PostMapping /test-plan/api/case/batch/run`** — 批量执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiCaseBatchRunRequest` | Body |

**返回值**: `void`

#### **`GetMapping /test-plan/api/case/report/get/{id}`** — 测试计划-用例列表-执行结果获取

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiReportDTO`

#### **`GetMapping /test-plan/api/case/report/get/detail/{reportId}/{stepId}`** — 测试计划-用例列表-执行结果获取-报告详情获取

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |
| `stepId` | `String` | 路径 |

**返回值**: `List<ApiReportDetailDTO>`

#### **`PostMapping /test-plan/api/case/batch/move`** — 测试计划-计划详情-接口用例-批量移动

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiCaseBatchMoveRequest` | Body |

**TestPlanApiCaseBatchMoveRequest 字段明细**:
  > **继承**: `TestPlanApiCaseBatchRequest`
  - `targetCollectionId`: `String` **[必填]** 目标计划集id

**返回值**: `void`

#### **`PostMapping /test-plan/api/case/associate/bug/page`** — 测试计划-计划详情-接口用例-获取待关联缺陷列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugPageProviderRequest` | Body |

**返回值**: `Pager<List<BugProviderDTO>>`

#### **`PostMapping /test-plan/api/case/associate/bug`** — 测试计划-计划详情-接口用例-关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseAssociateBugRequest` | Body |

**TestPlanCaseAssociateBugRequest 字段明细**:
  > **继承**: `AssociateBugRequest`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `testPlanCaseId`: `String` **[必填]** 测试计划关联用例的id

**返回值**: `void`

#### **`GetMapping /test-plan/api/case/disassociate/bug/{id}`** — 测试计划-计划详情-接口用例-取消关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /test-plan/api/case/batch/add-bug`** — 测试计划-计划详情-接口用例-批量添加缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiCaseBatchAddBugRequest` | Form |
| `` | `(value = "files"` | Form |
| `files` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `void`

#### **`PostMapping /test-plan/api/case/batch/associate-bug`** — 测试计划-计划详情-接口用例-批量关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiAssociateBugRequest` | Body |

**TestPlanApiAssociateBugRequest 字段明细**:
  > **继承**: `TestPlanApiCaseBatchRequest`
  - `bugIds`: `List<String>` **[必填]** 缺陷ID集合

**返回值**: `void`


### TestPlanApiScenarioController
**业务标签**: 测试计划场景用例

#### **`PostMapping /test-plan/api/scenario/page`** — 测试计划-已关联场景用例列表分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiScenarioRequest` | Body |

**TestPlanApiScenarioRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `collectionId`: `String` 计划集id
  - `scenarioId`: `String` 场景pk *约束: @Size(min = 1, max = 50, message = "{api_scenario_step.scenario_id.length_range}");*
  - `projectId`: `String` 项目ID *约束: @Size(max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(min = 1, max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(min = 1, max = 50, message = "{api_definition.ref_id.length_range}");*
  - `nullExecutorKey`: `boolean` 是否包含空执行人

**返回值**: `Pager<List<TestPlanApiScenarioPageResponse>>`

#### **`PostMapping /test-plan/api/scenario/module/count`** — 测试计划-已关联场景用例模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiScenarioModuleRequest` | Body |

**返回值**: `Map<String, Long>`

#### **`PostMapping /test-plan/api/scenario/tree`** — 测试计划-已关联场景用例列表模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanTreeRequest` | Body |

**TestPlanTreeRequest 字段明细**:
  - `testPlanId`: `String` **[必填]** 测试计划id

**返回值**: `List<BaseTreeNode>`

#### **`GetMapping /test-plan/api/scenario/run/{id}`** — 接口测试-接口场景管理-场景执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `reportId` | `String` | Query |

**返回值**: `TaskRequestDTO`

#### **`PostMapping /test-plan/api/scenario/batch/run`** — 批量执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiScenarioBatchRunRequest` | Body |

**返回值**: `void`

#### **`PostMapping /test-plan/api/scenario/disassociate`** — 测试计划-计划详情-场景用例列表-取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanDisassociationRequest` | Body |

**TestPlanDisassociationRequest 字段明细**:
  - `testPlanId`: `String` 测试计划ID
  - `id`: `String` 测试计划用例关系ID

**返回值**: `TestPlanAssociationResponse`

#### **`PostMapping /test-plan/api/scenario/batch/disassociate`** — 测试计划-计划详情-列表-批量取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BasePlanCaseBatchRequest` | Body |

**BasePlanCaseBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `moduleIds`: `List<String>` 模块id
  - `collectionId`: `String` 计划集id
  - `projectId`: `String` 项目Id
  - `nullExecutorKey`: `boolean` 是否包含空执行人

**返回值**: `TestPlanAssociationResponse`

#### **`PostMapping /test-plan/api/scenario/batch/update/executor`** — 测试计划-计划详情-场景用例列表-批量更新执行人

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiScenarioUpdateRequest` | Body |

**TestPlanApiScenarioUpdateRequest 字段明细**:
  > **继承**: `BasePlanCaseBatchRequest`
  - `userId`: `String` **[必填]** 执行人id

**返回值**: `void`

#### **`GetMapping /test-plan/api/scenario/report/get/{id}`** — 测试计划-计划详情-场景用例列表-查看执行结果

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ApiScenarioReportDTO`

#### **`GetMapping /test-plan/api/scenario/report/get/detail/{reportId}/{stepId}`** — 测试计划-计划详情-场景用例列表-执行结果详情获取

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |
| `stepId` | `String` | 路径 |

**返回值**: `List<ApiScenarioReportDetailDTO>`

#### **`PostMapping /test-plan/api/scenario/sort`** — 测试计划-场景用例拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ResourceSortRequest` | Body |

**ResourceSortRequest 字段明细**:
  > **继承**: `PosRequest`
  - `testCollectionId`: `String` **[必填]** 测试集ID

**返回值**: `TestPlanOperationResponse`

#### **`PostMapping /test-plan/api/scenario/batch/move`** — 测试计划-计划详情-场景用例-批量移动

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BaseBatchMoveRequest` | Body |

**BaseBatchMoveRequest 字段明细**:
  > **继承**: `BasePlanCaseBatchRequest`
  - `targetCollectionId`: `String` **[必填]** 目标计划集id

**返回值**: `void`

#### **`PostMapping /test-plan/api/scenario/associate/bug/page`** — 测试计划-计划详情-场景用例-获取待关联缺陷列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugPageProviderRequest` | Body |

**返回值**: `Pager<List<BugProviderDTO>>`

#### **`PostMapping /test-plan/api/scenario/associate/bug`** — 测试计划-计划详情-场景用例-关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseAssociateBugRequest` | Body |

**TestPlanCaseAssociateBugRequest 字段明细**:
  > **继承**: `AssociateBugRequest`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `testPlanCaseId`: `String` **[必填]** 测试计划关联用例的id

**返回值**: `void`

#### **`GetMapping /test-plan/api/scenario/disassociate/bug/{id}`** — 测试计划-计划详情-场景用例-取消关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /test-plan/api/scenario/batch/add-bug`** — 测试计划-计划详情-场景用例-批量添加缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanScenarioBatchAddBugRequest` | Form |
| `` | `(value = "files"` | Form |
| `files` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `void`

#### **`PostMapping /test-plan/api/scenario/batch/associate-bug`** — 测试计划-计划详情-场景用例-批量关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanScenarioBatchAssociateBugRequest` | Body |

**TestPlanScenarioBatchAssociateBugRequest 字段明细**:
  > **继承**: `BasePlanCaseBatchRequest`
  - `bugIds`: `List<String>` **[必填]** 缺陷ID集合

**返回值**: `void`


### TestPlanAssociateController
**业务标签**: 测试计划关联用例弹窗接口相关

#### **`PostMapping /test-plan/association/page`** — 测试计划-关联用例弹窗-功能用例列表查询(项目)

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FunctionalCasePageRequest` | Body |

**返回值**: `Pager<List<FunctionalCasePageDTO>>`

#### **`PostMapping /test-plan/association/api/page`** — 测试计划-关联用例弹窗-接口列表查询(项目)

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiRequest` | Body |

**TestPlanApiRequest 字段明细**:
  > **继承**: `ApiDefinitionPageRequest`
  - `testPlanId`: `String` **[必填]** 测试计划id

**返回值**: `Pager<List<ApiDefinitionDTO>>`

#### **`PostMapping /test-plan/association/api/case/page`** — 测试计划-关联用例弹窗-接口CASE列表查询(项目)

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiCaseRequest` | Body |

**TestPlanApiCaseRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `collectionId`: `String` 计划集id
  - `apiDefinitionId`: `String` 接口pk *约束: @Size(max = 50, message = "{api_definition.id.length_range}");*
  - `projectId`: `String` 项目ID *约束: @Size(max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本来源 *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `nullExecutorKey`: `boolean` 是否包含空执行人

**返回值**: `Pager<List<ApiTestCaseDTO>>`

#### **`PostMapping /test-plan/association/api/scenario/page`** — 测试计划-关联用例弹窗-接口场景列表查询(项目)

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanApiScenarioRequest` | Body |

**TestPlanApiScenarioRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `collectionId`: `String` 计划集id
  - `scenarioId`: `String` 场景pk *约束: @Size(min = 1, max = 50, message = "{api_scenario_step.scenario_id.length_range}");*
  - `projectId`: `String` 项目ID *约束: @Size(max = 50, message = "{api_definition.project_id.length_range}");*
  - `versionId`: `String` 版本fk *约束: @Size(min = 1, max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(min = 1, max = 50, message = "{api_definition.ref_id.length_range}");*
  - `nullExecutorKey`: `boolean` 是否包含空执行人

**返回值**: `Pager<List<ApiScenarioDTO>>`

#### **`PostMapping /test-plan/association/api/case/module/count`** — 测试计划-关联用例弹窗-接口CASE模块数量(项目)

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ApiModuleRequest` | Body |

**ApiModuleRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{api_definition_module.project_id.length_range}");*
  - `keyword`: `String` 关键字
  - `versionId`: `String` 版本fk *约束: @Size(max = 50, message = "{api_definition.version_id.length_range}");*
  - `refId`: `String` 版本引用fk *约束: @Size(max = 50, message = "{api_definition.ref_id.length_range}");*
  - `testPlanId`: `String` 测试计划id

**返回值**: `Map<String, Long>`


### TestPlanBugController
**业务标签**: 测试计划-详情-缺陷列表

#### **`PostMapping /test-plan/bug/page`** — 缺陷列表-分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanBugPageRequest` | Body |

**TestPlanBugPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `planId`: `String` **[必填]** 计划ID
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<TestPlanBugPageResponse>>`


### TestPlanCollectionMinderController
**业务标签**: 测试规划脑图

#### **`GetMapping /test-plan/mind/data/{planId}`** — 测试规划脑图列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `planId` | `String` | 路径 |

**返回值**: `List<TestPlanCollectionMinderTreeDTO>`

#### **`PostMapping /test-plan/mind/data/edit`** — 测试规划脑图列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCollectionMinderEditRequest` | Body |

**TestPlanCollectionMinderEditRequest 字段明细**:
  - `planId`: `String` **[必填]** 测试计划id
  - `editList`: `List<TestPlanCollectionMinderEditDTO>` 新增/修改的节点集合

**返回值**: `void`


### TestPlanController
**业务标签**: 测试计划

#### **`PostMapping /test-plan/page`** — 测试计划-表格分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanTableRequest` | Body |

**TestPlanTableRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `moduleIds`: `List<String>` 模块ID(根据模块树查询时要把当前节点以及子节点都放在这里。)
  - `projectId`: `String` **[必填]** 项目ID
  - `type`: `String` **[必填]** 类型
  - `keywordFilterIds`: `List<String>` 通过Keyword过滤出的测试子计划的测试计划组id
  - `innerIds`: `List<String>` 通过其他条件查询出来的，必须要包含的测试计划ID
  - `combineInnerIds`: `List<String>`
  - `combineOperator`: `String`
  - `myTodoUserId`: `String` 我的待办用户ID, 组合使用: myTodo=true, myTodoUserId=xxx
  - `doneExcludeIds`: `List<String>` 已办的测试计划ID集合 (用作待办排除)
  - `extraIncludeChildIds`: `List<String>` 额外的子计划ID集合
  - `includeItemTestPlanIds`: `List<String>` 应当包含的子测试计划ID （用于程序内部筛选过滤）

**返回值**: `Pager<List<TestPlanResponse>>`

#### **`PostMapping /test-plan/rage`** — 测试计划-测试计划统计

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCoverageRequest` | Body |

**TestPlanCoverageRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `TestPlanCoverageDTO`

#### **`GetMapping /test-plan/group-list/{projectId}`** — 测试计划-测试计划组查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<TestPlan>`

#### **`GetMapping /test-plan/test-plan-list/{projectId}`** — 测试计划-测试计划组查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<TestPlan>`

#### **`GetMapping /test-plan/list-in-group/{groupId}`** — 测试计划-表格分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `groupId` | `String` | 路径 |

**返回值**: `List<TestPlanResponse>`

#### **`PostMapping /test-plan/statistics`** — 测试计划-获取计划详情统计{通过率, 执行进度}

| 参数 | 类型 | 来源 |
|------|------|------|
| `ids` | `List<String>` | Body |

**返回值**: `List<TestPlanStatisticsResponse>`

#### **`PostMapping /test-plan/module/count`** — 测试计划-模块统计

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanTableRequest` | Body |

**TestPlanTableRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `moduleIds`: `List<String>` 模块ID(根据模块树查询时要把当前节点以及子节点都放在这里。)
  - `projectId`: `String` **[必填]** 项目ID
  - `type`: `String` **[必填]** 类型
  - `keywordFilterIds`: `List<String>` 通过Keyword过滤出的测试子计划的测试计划组id
  - `innerIds`: `List<String>` 通过其他条件查询出来的，必须要包含的测试计划ID
  - `combineInnerIds`: `List<String>`
  - `combineOperator`: `String`
  - `myTodoUserId`: `String` 我的待办用户ID, 组合使用: myTodo=true, myTodoUserId=xxx
  - `doneExcludeIds`: `List<String>` 已办的测试计划ID集合 (用作待办排除)
  - `extraIncludeChildIds`: `List<String>` 额外的子计划ID集合
  - `includeItemTestPlanIds`: `List<String>` 应当包含的子测试计划ID （用于程序内部筛选过滤）

**返回值**: `Map<String, Long>`

#### **`PostMapping /test-plan/add`** — 测试计划-创建测试计划

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCreateRequest` | Body |

**TestPlanCreateRequest 字段明细**:
  - `projectId`: `String` **[必填]** 测试计划所属项目 *约束: @Size(min = 1, max = 50, message = "{test_plan.project_id.length_range}");*
  - `name`: `String` **[必填]** 测试计划名称 *约束: @Size(min = 1, max = 255, message = "{test_plan.name.length_range}");*
  - `plannedStartTime`: `Long` 计划开始时间
  - `plannedEndTime`: `Long` 计划结束时间
  - `description`: `String` 描述
  - `automaticStatusUpdate`: `boolean` 是否自定更新功能用例状态
  - `repeatCase`: `boolean` 是否允许重复添加用例
  - `baseAssociateCaseRequest`: `BaseAssociateCaseRequest` 查询用例的条件

**返回值**: `TestPlan`

#### **`PostMapping /test-plan/update`** — 测试计划-更新测试计划

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanUpdateRequest` | Body |

**TestPlanUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 测试计划ID
  - `name`: `String` 测试计划名称 *约束: @Size(min = 1, max = 255, message = "{test_plan.name.length_range}");*
  - `tags`: `LinkedHashSet<String>` 标签
  - `plannedStartTime`: `Long` 计划开始时间
  - `plannedEndTime`: `Long` 计划结束时间
  - `description`: `String` 描述
  - `testPlanning`: `Boolean` 是否开启测试规划
  - `automaticStatusUpdate`: `Boolean` 是否自定更新功能用例状态
  - `repeatCase`: `Boolean` 是否允许重复添加用例
  - `passThreshold`: `Double` 测试计划通过阈值;0-100 *约束: @Max(value = 100); @Min(value = 0);*

**返回值**: `TestPlan`

#### **`GetMapping /test-plan/delete/{id}`** — 测试计划-删除测试计划

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /test-plan/edit/follower`** — 测试计划-关注/取消关注

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanFollowerRequest` | Body |

**TestPlanFollowerRequest 字段明细**:
  - `userId`: `String` **[必填]** 用户id
  - `testPlanId`: `String` **[必填]** 用例id

**返回值**: `void`

#### **`GetMapping /test-plan/archived/{id}`** — 测试计划-归档

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /test-plan/{id}`** — 测试计划-抽屉详情(单个测试计划获取详情用于编辑)

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `TestPlanDetailResponse`

#### **`PostMapping /test-plan/batch-delete`** — 测试计划-批量删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanBatchProcessRequest` | Body |

**TestPlanBatchProcessRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID
  - `moduleIds`: `List<String>` 模块ID

**返回值**: `void`

#### **`GetMapping /test-plan/copy/{id}`** — 测试计划-复制测试计划

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `TestPlanSingleOperationResponse`

#### **`PostMapping /test-plan/batch-copy`** — 测试计划-批量复制测试计划

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanBatchRequest` | Body |

**TestPlanBatchRequest 字段明细**:
  > **继承**: `TestPlanBatchProcessRequest`
  - `targetId`: `String` **[必填]** 目标ID

**返回值**: `TestPlanOperationResponse`

#### **`PostMapping /test-plan/batch-move`** — 测试计划-批量移动测试计划

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanBatchRequest` | Body |

**TestPlanBatchRequest 字段明细**:
  > **继承**: `TestPlanBatchProcessRequest`
  - `targetId`: `String` **[必填]** 目标ID

**返回值**: `TestPlanOperationResponse`

#### **`PostMapping /test-plan/batch-archived`** — 测试计划-批量归档

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanBatchProcessRequest` | Body |

**TestPlanBatchProcessRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID
  - `moduleIds`: `List<String>` 模块ID

**返回值**: `void`

#### **`PostMapping /test-plan/batch-edit`** — 测试计划-批量编辑

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanBatchEditRequest` | Body |

**TestPlanBatchEditRequest 字段明细**:
  > **继承**: `TestPlanBatchProcessRequest`
  - `clear`: `boolean` 是否清空
  - `tags`: `List<String>` 标签
  - `editColumn`: `String` 本次编辑的字段

**返回值**: `void`

#### **`PostMapping /test-plan/sort`** — 测试计划移动（测试计划拖进、拖出到测试计划组、测试计划在测试计划组内的排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PosRequest` | Body |

**PosRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目id
  - `moveId`: `String` **[必填]** 移动用例id
  - `targetId`: `String` **[必填]** 目标用例id
  - `moveMode`: `String` **[必填]** 移动类型

**返回值**: `TestPlanOperationResponse`

#### **`PostMapping /test-plan/schedule-config`** — 接口测试-接口场景管理-定时任务配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BaseScheduleConfigRequest` | Body |

**BaseScheduleConfigRequest 字段明细**:
  - `resourceId`: `String` **[必填]** 定时任务资源ID *约束: @Size(min = 1, max = 50, message = "{api_scenario.id.length_range}");*
  - `enable`: `boolean` 启用/禁用
  - `cron`: `String` **[必填]** Cron表达式 *约束: @Size(max = 255, message = "{length.too.large}");*

**返回值**: `String`

#### **`PostMapping /test-plan/batch-schedule-config`** — 接口测试-接口场景管理-定时任务批量配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanScheduleBatchConfigRequest` | Body |

**TestPlanScheduleBatchConfigRequest 字段明细**:
  > **继承**: `TestPlanBatchProcessRequest`
  - `enable`: `boolean` 启用/禁用
  - `cron`: `String` Cron表达式 *约束: @Size(max = 255, message = "{length.too.large}");*

**返回值**: `void`

#### **`GetMapping /test-plan/schedule-config-delete/{testPlanId}`** — 接口测试-接口场景管理-删除定时任务配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `testPlanId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /test-plan/his/page`** — 测试计划-执行历史-列表分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanExecuteHisPageRequest` | Body |

**TestPlanExecuteHisPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `testPlanId`: `String` 测试计划/计划组ID

**返回值**: `Pager<List<TestPlanExecuteHisDTO>>`


### TestPlanExecuteController
**业务标签**: 测试计划执行

#### **`PostMapping /test-plan-execute/single`** — 测试计划单独执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanExecuteRequest` | Body |

**TestPlanExecuteRequest 字段明细**:
  - `executeId`: `String` **[必填]** 执行ID

**返回值**: `String`

#### **`PostMapping /test-plan-execute/batch`** — 测试计划-批量执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanBatchExecuteRequest` | Body |

**TestPlanBatchExecuteRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID
  - `executeIds`: `List<String>` **[必填]** 执行ID

**返回值**: `void`

#### **`GetMapping /test-plan-execute/user-option/{projectId}`** — 执行人下拉选项(空选项)

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserExtendDTO>`


### TestPlanFunctionalCaseController
**业务标签**: 测试计划功能用例

#### **`PostMapping /test-plan/functional/case/sort`** — 测试计划功能用例-功能用例拖拽排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ResourceSortRequest` | Body |

**ResourceSortRequest 字段明细**:
  > **继承**: `PosRequest`
  - `testCollectionId`: `String` **[必填]** 测试集ID

**返回值**: `TestPlanOperationResponse`

#### **`PostMapping /test-plan/functional/case/page`** — 测试计划-已关联功能用例分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseRequest` | Body |

**TestPlanCaseRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `projectId`: `String` 项目ID
  - `versionId`: `String` 版本id
  - `refId`: `String` 版本来源
  - `moduleIds`: `List<String>` 模块id
  - `collectionId`: `String` 计划集id
  - `nullExecutorKey`: `boolean` 是否包含空执行人

**返回值**: `Pager<List<TestPlanCasePageResponse>>`

#### **`PostMapping /test-plan/functional/case/tree`** — 测试计划-已关联功能用例列表模块树

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanTreeRequest` | Body |

**TestPlanTreeRequest 字段明细**:
  - `testPlanId`: `String` **[必填]** 测试计划id

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /test-plan/functional/case/module/count`** — 测试计划-已关联功能用例模块数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseModuleRequest` | Body |

**返回值**: `Map<String, Long>`

#### **`PostMapping /test-plan/functional/case/disassociate`** — 测试计划-计划详情-列表-取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanDisassociationRequest` | Body |

**TestPlanDisassociationRequest 字段明细**:
  - `testPlanId`: `String` 测试计划ID
  - `id`: `String` 测试计划用例关系ID

**返回值**: `TestPlanAssociationResponse`

#### **`PostMapping /test-plan/functional/case/batch/disassociate`** — 测试计划-计划详情-列表-批量取消关联用例

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BasePlanCaseBatchRequest` | Body |

**BasePlanCaseBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `moduleIds`: `List<String>` 模块id
  - `collectionId`: `String` 计划集id
  - `projectId`: `String` 项目Id
  - `nullExecutorKey`: `boolean` 是否包含空执行人

**返回值**: `TestPlanAssociationResponse`

#### **`PostMapping /test-plan/functional/case/associate/bug/page`** — 测试计划-计划详情-功能用例-获取待关联缺陷列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BugPageProviderRequest` | Body |

**返回值**: `Pager<List<BugProviderDTO>>`

#### **`PostMapping /test-plan/functional/case/associate/bug`** — 测试计划-计划详情-功能用例-关联其他用例-关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseAssociateBugRequest` | Body |

**TestPlanCaseAssociateBugRequest 字段明细**:
  > **继承**: `AssociateBugRequest`
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `testPlanCaseId`: `String` **[必填]** 测试计划关联用例的id

**返回值**: `void`

#### **`GetMapping /test-plan/functional/case/disassociate/bug/{id}`** — 用例管理-功能用例-关联其他用例-取消关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /test-plan/functional/case/run`** — 测试计划-计划详情-功能用例-执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseRunRequest` | Body |

**TestPlanCaseRunRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目Id
  - `id`: `String` **[必填]** id
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `caseId`: `String` **[必填]** 用例id
  - `lastExecResult`: `String` **[必填]** 最终执行结果
  - `stepsExecResult`: `String` 步骤执行结果
  - `content`: `String` 执行内容
  - `notifier`: `String` 评论@的人的Id, 多个以';'隔开
  - `planCommentFileIds`: `List<String>` 测试计划执行评论富文本的文件id集合

**返回值**: `void`

#### **`PostMapping /test-plan/functional/case/batch/run`** — 测试计划-计划详情-功能用例-批量执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseBatchRunRequest` | Body |

**TestPlanCaseBatchRunRequest 字段明细**:
  > **继承**: `BasePlanCaseBatchRequest`
  - `projectId`: `String` 项目Id
  - `lastExecResult`: `String` **[必填]** 最终执行结果
  - `content`: `String` 执行内容
  - `notifier`: `String` 评论@的人的Id, 多个以';'隔开
  - `planCommentFileIds`: `List<String>` 测试计划执行评论富文本的文件id集合

**返回值**: `void`

#### **`PostMapping /test-plan/functional/case/has/associate/bug/page`** — 测试计划-计划详情-功能用例-获取已关联的缺陷列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AssociateBugPageRequest` | Body |

**返回值**: `Pager<List<BugProviderDTO>>`

#### **`PostMapping /test-plan/functional/case/batch/update/executor`** — 测试计划-计划详情-功能用例-批量更新执行人

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseUpdateRequest` | Body |

**TestPlanCaseUpdateRequest 字段明细**:
  > **继承**: `BasePlanCaseBatchRequest`
  - `userId`: `String` **[必填]** 执行人id

**返回值**: `void`

#### **`GetMapping /test-plan/functional/case/detail/{id}`** — 测试计划-计划详情-功能用例-获取用例详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `TestPlanCaseDetailResponse`

#### **`PostMapping /test-plan/functional/case/exec/history`** — 测试计划-计划详情-功能用例-执行历史

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseExecHistoryRequest` | Body |

**TestPlanCaseExecHistoryRequest 字段明细**:
  - `testPlanId`: `String` **[必填]** 测试计划id
  - `id`: `String` **[必填]** id
  - `caseId`: `String` **[必填]** 用例id

**返回值**: `List<TestPlanCaseExecHistoryResponse>`

#### **`GetMapping /test-plan/functional/case/user-option/{projectId}`** — 测试计划-计划详情-功能用例-获取用户列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserDTO>`

#### **`PostMapping /test-plan/functional/case/batch/move`** — 测试计划-计划详情-功能用例-批量移动

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BaseBatchMoveRequest` | Body |

**BaseBatchMoveRequest 字段明细**:
  > **继承**: `BasePlanCaseBatchRequest`
  - `targetCollectionId`: `String` **[必填]** 目标计划集id

**返回值**: `void`

#### **`PostMapping /test-plan/functional/case/batch/add-bug`** — 测试计划-计划详情-功能用例-批量添加缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseBatchAddBugRequest` | Form |
| `` | `(value = "files"` | Form |
| `files` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `void`

#### **`PostMapping /test-plan/functional/case/batch/associate-bug`** — 测试计划-计划详情-功能用例-批量关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseBatchAssociateBugRequest` | Body |

**TestPlanCaseBatchAssociateBugRequest 字段明细**:
  > **继承**: `TestPlanCaseMinderRequest`
  - `bugIds`: `List<String>` **[必填]** 缺陷ID集合

**返回值**: `void`


### TestPlanFunctionalCaseMinderController
**业务标签**: 测试计划-功能用例-脑图-操作

#### **`PostMapping /test-plan/functional/case/minder/batch/add-bug`** — 测试计划-功能用例-脑图-批量添加缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseBatchAddBugRequest` | Form |
| `` | `(value = "files"` | Form |
| `files` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `void`

#### **`PostMapping /test-plan/functional/case/minder/batch/associate-bug`** — 测试计划-计划详情-功能用例-脑图-批量关联缺陷

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanCaseBatchAssociateBugRequest` | Body |

**TestPlanCaseBatchAssociateBugRequest 字段明细**:
  > **继承**: `TestPlanCaseMinderRequest`
  - `bugIds`: `List<String>` **[必填]** 缺陷ID集合

**返回值**: `void`


### TestPlanModuleController
**业务标签**: 测试计划管理-模块树

#### **`GetMapping /test-plan/module/tree/{projectId}`** — 测试计划管理-模块树-查找模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /test-plan/module/add`** — 测试计划管理-模块树-添加模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanModuleCreateRequest` | Body |

**TestPlanModuleCreateRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{test_plan_module.name.length_range}");*

**返回值**: `String`

#### **`PostMapping /test-plan/module/update`** — 测试计划管理-模块树-修改模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanModuleUpdateRequest` | Body |

**TestPlanModuleUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 模块ID
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{test_plan_module.name.length_range}");*

**返回值**: `boolean`

#### **`GetMapping /test-plan/module/delete/{deleteId}`** — 测试计划管理-模块树-删除模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `deleteId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /test-plan/module/move`** — 测试计划管理-模块树-移动模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `NodeMoveRequest` | Body |

**NodeMoveRequest 字段明细**:
  - `dragNodeId`: `String` **[必填]** 被拖拽的节点
  - `dropNodeId`: `String` **[必填]** 放入的节点
  - `dropPosition`: `int` 放入的位置（取值：-1，,1。  -1：dropNodeId节点之前。 1：dropNodeId节点后）

**返回值**: `void`


### TestPlanReportController
**业务标签**: 测试计划-报告

#### **`PostMapping /test-plan/report/page`** — 测试计划-报告-表格分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportPageRequest` | Body |

**TestPlanReportPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<TestPlanReportPageResponse>>`

#### **`PostMapping /test-plan/report/rename/{id}`** — 测试计划-报告-重命名

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `name` | `Object` | Body |

**返回值**: `void`

#### **`GetMapping /test-plan/report/delete/{id}`** — 测试计划-报告-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /test-plan/report/batch-delete`** — 测试计划-报告-批量删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportBatchRequest` | Body |

**TestPlanReportBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `void`

#### **`PostMapping /test-plan/report/batch-param`** — 测试计划-报告-获取批量参数

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportBatchRequest` | Body |

**TestPlanReportBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `List<String>`

#### **`PostMapping /test-plan/report/manual-gen`** — 测试计划-详情-手动生成报告

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportManualRequest` | Body |

**TestPlanReportManualRequest 字段明细**:
  > **继承**: `TestPlanReportGenRequest`
  - `reportName`: `String` 报告名称
  - `components`: `List<TestPlanReportComponentSaveRequest>` 报告组件集合
  - `richTextTmpFileIds`: `List<String>` 富文本组件临时生成的文件ID(图片)

**返回值**: `String`

#### **`PostMapping /test-plan/report/auto-gen`** — 测试计划-详情-自动生成报告

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportGenRequest` | Body |

**TestPlanReportGenRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID
  - `testPlanId`: `String` **[必填]** 计划ID/计划组ID
  - `triggerMode`: `String` 触发方式

**返回值**: `String`

#### **`GetMapping /test-plan/report/get/{reportId}`** — 测试计划-报告-详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |

**返回值**: `TestPlanReportDetailResponse`

#### **`GetMapping /test-plan/report/get-task/{taskId}`** — 测试计划|组-执行历史-执行结果

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskId` | `String` | 路径 |

**返回值**: `TestPlanTaskReportResponse`

#### **`GetMapping /test-plan/report/get-result/{taskId}`** — 测试计划|组-任务-执行结果

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskId` | `String` | 路径 |

**返回值**: `TestPlanReportDetailResponse`

#### **`GetMapping /test-plan/report/get-layout/{reportId}`** — 测试计划-报告-组件布局

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |

**返回值**: `List<TestPlanReportComponent>`

#### **`PostMapping /test-plan/report/upload/md/file`** — 测试计划-报告-详情-上传富文本(图片)

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`PostMapping /test-plan/report/detail/edit`** — 测试计划-报告-详情-富文本组件内容更新

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportDetailEditRequest` | Body |

**TestPlanReportDetailEditRequest 字段明细**:
  - `id`: `String` **[必填]** 报告ID
  - `componentId`: `String` 组件ID; {默认布局时使用报告总结枚举值作为ID}
  - `componentValue`: `String` 报告总结
  - `richTextTmpFileIds`: `List<String>` 富文本临时文件ID(图片)

**返回值**: `TestPlanReportDetailResponse`

#### **`PostMapping /test-plan/report/detail/bug/page`** — 测试计划-报告-详情-缺陷分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportDetailPageRequest` | Body |

**TestPlanReportDetailPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `reportId`: `String` **[必填]** 报告ID
  - `collectionId`: `String` 测试集ID
  - `detailReportIds`: `List<String>` 报告ID集合

**返回值**: `Pager<List<BugDTO>>`

#### **`PostMapping /test-plan/report/detail/functional/case/page`** — 测试计划-报告-详情-功能用例分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportDetailPageRequest` | Body |

**TestPlanReportDetailPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `reportId`: `String` **[必填]** 报告ID
  - `collectionId`: `String` 测试集ID
  - `detailReportIds`: `List<String>` 报告ID集合

**返回值**: `Pager<List<ReportDetailCasePageDTO>>`

#### **`GetMapping /test-plan/report/detail/functional/case/step/{reportId}`** — 测试计划-报告-详情-功能用例-执行步骤结果

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |

**返回值**: `TestPlanCaseExecHistoryResponse`

#### **`PostMapping /test-plan/report/detail/api/case/page`** — 测试计划-报告-详情-接口用例分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportDetailPageRequest` | Body |

**TestPlanReportDetailPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `reportId`: `String` **[必填]** 报告ID
  - `collectionId`: `String` 测试集ID
  - `detailReportIds`: `List<String>` 报告ID集合

**返回值**: `Pager<List<ReportDetailCasePageDTO>>`

#### **`PostMapping /test-plan/report/detail/scenario/case/page`** — 测试计划-报告-详情-场景用例分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportDetailPageRequest` | Body |

**TestPlanReportDetailPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `reportId`: `String` **[必填]** 报告ID
  - `collectionId`: `String` 测试集ID
  - `detailReportIds`: `List<String>` 报告ID集合

**返回值**: `Pager<List<ReportDetailCasePageDTO>>`

#### **`PostMapping /test-plan/report/detail/plan/report/page`** — 测试计划-报告-集合报告详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportDetailPageRequest` | Body |

**TestPlanReportDetailPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `reportId`: `String` **[必填]** 报告ID
  - `collectionId`: `String` 测试集ID
  - `detailReportIds`: `List<String>` 报告ID集合

**返回值**: `Pager<List<TestPlanReportDetailResponse>>`

#### **`GetMapping /test-plan/report/preview/md/{projectId}/{fileId}/{compressed}`** — 缺陷管理-富文本缩略图-预览

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `fileId` | `String` | 路径 |
| `compressed` | `boolean` | 路径 |

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /test-plan/report/export/{reportId}`** — 测试计划-报告-导出日志

| 参数 | 类型 | 来源 |
|------|------|------|
| `reportId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /test-plan/report/batch-export`** — 测试计划-报告-批量导出日志

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportBatchRequest` | Body |

**TestPlanReportBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `void`

#### **`PostMapping /test-plan/report/detail/{type}/collection/page`** — 测试计划-报告-详情-测试集分页查询(不同用例类型)

| 参数 | 类型 | 来源 |
|------|------|------|
| `type` | `String` | 路径 |
| `request` | `TestPlanReportDetailPageRequest` | Body |

**TestPlanReportDetailPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `reportId`: `String` **[必填]** 报告ID
  - `collectionId`: `String` 测试集ID
  - `detailReportIds`: `List<String>` 报告ID集合

**返回值**: `Pager<List<TestPlanReportDetailCollectionResponse>>`


### TestPlanReportShareController
**业务标签**: 测试计划-分享

#### **`PostMapping /test-plan/report/share/gen`** — 测试计划-报告-分享

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanReportShareRequest` | Body |

**TestPlanReportShareRequest 字段明细**:
  - `shareType`: `String` 分享类型 资源的类型 Single, Batch, API_SHARE_REPORT, TEST_PLAN_SHARE_REPORT
  - `lang`: `String` 语言
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{share_info.project_id.length_range}", groups = {Created.class, Updated.class});*
  - `reportId`: `String` **[必填]** 分享扩展数据 资源的ID

**返回值**: `TestPlanShareInfo`

#### **`GetMapping /test-plan/report/share/get/{id}`** — 测试计划-报告-获取分享链接

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `TestPlanShareResponse`

#### **`GetMapping /test-plan/report/share/get-share-time/{id}`** — 测试计划-报告-获取分享链接的有效时间

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `String`

#### **`GetMapping /test-plan/report/share/get-layout/{shareId}/{reportId}`** — 测试计划-报告-组件布局

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |

**返回值**: `List<TestPlanReportComponent>`

#### **`GetMapping /test-plan/report/share/get/detail/{shareId}/{reportId}`** — 测试计划-报告分享-详情查看

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |

**返回值**: `TestPlanReportDetailResponse`

#### **`PostMapping /test-plan/report/share/detail/bug/page`** — 测试计划-报告-详情-缺陷分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanShareReportDetailRequest` | Body |

**TestPlanShareReportDetailRequest 字段明细**:
  > **继承**: `TestPlanReportDetailPageRequest`
  - `shareId`: `String` **[必填]** 分享ID

**返回值**: `Pager<List<BugDTO>>`

#### **`PostMapping /test-plan/report/share/detail/functional/case/page`** — 测试计划-报告-详情-功能用例分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanShareReportDetailRequest` | Body |

**TestPlanShareReportDetailRequest 字段明细**:
  > **继承**: `TestPlanReportDetailPageRequest`
  - `shareId`: `String` **[必填]** 分享ID

**返回值**: `Pager<List<ReportDetailCasePageDTO>>`

#### **`PostMapping /test-plan/report/share/detail/api/case/page`** — 测试计划-报告-详情-接口用例分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanShareReportDetailRequest` | Body |

**TestPlanShareReportDetailRequest 字段明细**:
  > **继承**: `TestPlanReportDetailPageRequest`
  - `shareId`: `String` **[必填]** 分享ID

**返回值**: `Pager<List<ReportDetailCasePageDTO>>`

#### **`PostMapping /test-plan/report/share/detail/scenario/case/page`** — 测试计划-报告-详情-场景用例分页查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanShareReportDetailRequest` | Body |

**TestPlanShareReportDetailRequest 字段明细**:
  > **继承**: `TestPlanReportDetailPageRequest`
  - `shareId`: `String` **[必填]** 分享ID

**返回值**: `Pager<List<ReportDetailCasePageDTO>>`

#### **`PostMapping /test-plan/report/share/detail/plan/report/page`** — 测试计划-报告-集合报告详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestPlanShareReportDetailRequest` | Body |

**TestPlanShareReportDetailRequest 字段明细**:
  > **继承**: `TestPlanReportDetailPageRequest`
  - `shareId`: `String` **[必填]** 分享ID

**返回值**: `Pager<List<TestPlanReportDetailResponse>>`

#### **`GetMapping /test-plan/report/share/detail/api-report/{shareId}/{reportId}`** — 测试计划-接口用例-查看报告

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |

**返回值**: `ApiReportDTO`

#### **`GetMapping /test-plan/report/share/detail/api-report/get/{shareId}/{reportId}/{stepId}`** — 测试计划-接口用例-查看报告详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |
| `stepId` | `String` | 路径 |

**返回值**: `List<ApiReportDetailDTO>`

#### **`GetMapping /test-plan/report/share/detail/scenario-report/{shareId}/{reportId}`** — 测试计划-接口场景-查看报告

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |

**返回值**: `ApiScenarioReportDTO`

#### **`GetMapping /test-plan/report/share/detail/scenario-report/get/{shareId}/{reportId}/{stepId}`** — 测试计划-接口场景-查看报告详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |
| `stepId` | `String` | 路径 |

**返回值**: `List<ApiScenarioReportDetailDTO>`

#### **`GetMapping /test-plan/report/share/detail/functional/case/step/{shareId}/{reportId}`** — 测试计划-报告-详情-功能用例-执行步骤结果

| 参数 | 类型 | 来源 |
|------|------|------|
| `shareId` | `String` | 路径 |
| `reportId` | `String` | 路径 |

**返回值**: `TestPlanCaseExecHistoryResponse`

#### **`PostMapping /test-plan/report/share/detail/{type}/collection/page`** — 测试计划-报告-详情-测试集分页查询(不同用例类型)

| 参数 | 类型 | 来源 |
|------|------|------|
| `type` | `String` | 路径 |
| `request` | `TestPlanShareReportDetailRequest` | Body |

**TestPlanShareReportDetailRequest 字段明细**:
  > **继承**: `TestPlanReportDetailPageRequest`
  - `shareId`: `String` **[必填]** 分享ID

**返回值**: `Pager<List<TestPlanReportDetailCollectionResponse>>`


### TestPlanTaskCenterController
**业务标签**: 任务中心-实时任务-测试计划

#### **`PostMapping /task/center/plan/project/real-time/page`** — 项目-任务中心-测试计划-实时任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterPageRequest` | Body |

**返回值**: `Pager<List<TaskCenterDTO>>`

#### **`PostMapping /task/center/plan/org/real-time/page`** — 组织-任务中心-测试计划-实时任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterPageRequest` | Body |

**返回值**: `Pager<List<TaskCenterDTO>>`

#### **`PostMapping /task/center/plan/system/real-time/page`** — 系统-任务中心-测试计划-实时任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterPageRequest` | Body |

**返回值**: `Pager<List<TaskCenterDTO>>`

#### **`GetMapping /task/center/plan/project/stop/{id}`** — 项目-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /task/center/plan/org/stop/{id}`** — 组织-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /task/center/plan/system/stop/{id}`** — 系统-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /task/center/plan/system/stop`** — 系统-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/plan/org/stop`** — 组织-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/plan/project/stop`** — 项目-任务中心-接口用例/场景-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterBatchRequest` | Body |

**返回值**: `void`


## project-management 模块

共 22 个 Controller，173 个接口


### CustomFunctionController
**业务标签**: 项目管理-公共脚本

#### **`PostMapping /project/custom/func/page`** — 项目管理-公共脚本-列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CustomFunctionPageRequest` | Body |

**CustomFunctionPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{custom_function.project_id.length_range}");*
  - `type`: `String` 脚本语言类型
  - `status`: `String` 脚本状态（草稿/测试通过）

**返回值**: `Pager<List<CustomFunctionDTO>>`

#### **`GetMapping /project/custom/func/columns-option/{projectId}`** — 项目管理-公共脚本-请求头筛选相关选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `CustomFuncColumnsOptionDTO`

#### **`GetMapping /project/custom/func/detail/{id}`** — 项目管理-公共脚本-脚本详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `CustomFunctionDTO`

#### **`PostMapping /project/custom/func/add`** — 项目管理-公共脚本-脚本添加

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CustomFunctionRequest` | Body |

**CustomFunctionRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{custom_function.project_id.length_range}");*
  - `name`: `String` **[必填]** 函数名 *约束: @Size(min = 1, max = 255, message = "{custom_function.name.length_range}");*
  - `type`: `String` 脚本语言类型 *约束: @EnumValue(enumClass = ScriptLanguageType.class);*
  - `status`: `String` 脚本状态（草稿/测试通过）
  - `description`: `String` 函数描述
  - `params`: `String` 参数列表
  - `script`: `String` 函数体
  - `result`: `String` 执行结果

**返回值**: `CustomFunction`

#### **`PostMapping /project/custom/func/update`** — 项目管理-公共脚本-脚本更新

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CustomFunctionUpdateRequest` | Body |

**CustomFunctionUpdateRequest 字段明细**:
  > **继承**: `CustomFunctionRequest`
  - `id`: `String` **[必填]** 主键ID *约束: @Size(min = 1, max = 50, message = "{custom_function.id.length_range}");*

**返回值**: `void`

#### **`PostMapping /project/custom/func/status`** — 项目管理-公共脚本-脚本更新状态

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CustomFunctionUpdateRequest` | Body |

**CustomFunctionUpdateRequest 字段明细**:
  > **继承**: `CustomFunctionRequest`
  - `id`: `String` **[必填]** 主键ID *约束: @Size(min = 1, max = 50, message = "{custom_function.id.length_range}");*

**返回值**: `void`

#### **`GetMapping /project/custom/func/delete/{id}`** — 项目管理-脚本删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/custom/func/history/page`** — 项目管理-公共脚本-变更历史-列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OperationHistoryRequest` | Body |

**OperationHistoryRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目id *约束: @Size(min = 1, max = 50, message = "{operation_history.project_id.length_range}");*
  - `sourceId`: `String` **[必填]** 资源id
  - `createUser`: `String` 操作人
  - `types`: `List<String>` 操作类型
  - `modules`: `String` 操作模块

**返回值**: `Pager<List<OperationHistoryDTO>>`


### EnvironmentController
**业务标签**: 项目管理-环境

#### **`PostMapping /project/environment/list`** — 项目管理-环境-环境目录-列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `EnvironmentFilterRequest` | Body |

**EnvironmentFilterRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project_parameters.project_id.length_range}");*
  - `keyword`: `String` 关键字

**返回值**: `List<Environment>`

#### **`GetMapping /project/environment/get/{id}`** — 项目管理-环境-环境目录-详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `EnvironmentInfoDTO`

#### **`GetMapping /project/environment/scripts/{projectId}`** — 项目管理-环境-环境目录-接口插件前端配置脚本列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<EnvironmentPluginScriptDTO>`

#### **`PostMapping /project/environment/add`** — 项目管理-环境-环境目录-新增

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `EnvironmentRequest` | Form |
| `` | `(value = "file"` | Form |
| `sslFiles` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `Environment`

#### **`PostMapping /project/environment/update`** — 项目管理-环境-环境目录-修改

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `EnvironmentRequest` | Form |
| `` | `(value = "file"` | Form |
| `sslFiles` | `required = false) List<MultipartFile>` | 参数 |

**返回值**: `Environment`

#### **`GetMapping /project/environment/delete/{id}`** — 项目管理-环境-环境目录-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/environment/database/validate`** — 项目管理-环境-数据库配置-校验

| 参数 | 类型 | 来源 |
|------|------|------|
| `databaseConfig` | `DataSource` | Body |

**DataSource 字段明细**:
  - `id`: `String` id
  - `dataSource`: `String` 数据源名称
  - `driver`: `String` 数据驱动
  - `driverId`: `String` **[必填]** 数据驱动id
  - `dbUrl`: `String` 数据库连接url
  - `username`: `String` 用户名
  - `password`: `String` 密码

**返回值**: `void`

#### **`GetMapping /project/environment/database/driver-options/{organizationId}`** — 项目管理-环境-数据库配置-数据库驱动选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `List<OptionDTO>`

#### **`PostMapping /project/environment/import`** — 项目管理-环境-环境目录-导入

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `EnvironmentImportRequest` | Form |
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |

**返回值**: `void`

#### **`PostMapping /project/environment/export`** — 项目管理-环境-环境目录-导出

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /project/environment/get/entry`**

| 参数 | 类型 | 来源 |
|------|------|------|
| `password` | `String` | Form |
| `sslFiles` | `MultipartFile` | Form |

**返回值**: `List<KeyStoreEntry>`

#### **`PostMapping /project/environment/edit/pos`** — 项目管理-环境-环境目录-修改排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PosRequest` | Body |

**PosRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目id
  - `moveId`: `String` **[必填]** 移动用例id
  - `targetId`: `String` **[必填]** 目标用例id
  - `moveMode`: `String` **[必填]** 移动类型

**返回值**: `void`

#### **`GetMapping /project/environment/get-options/{projectId}`** — 项目管理-环境-环境目录-列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<EnvironmentOptionsDTO>`


### EnvironmentGroupController
**业务标签**: 项目管理-环境组

#### **`PostMapping /project/environment/group/add`** — 项目管理-环境组-新增

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `EnvironmentGroupRequest` | Body |

**EnvironmentGroupRequest 字段明细**:
  - `id`: `String` 环境组id
  - `name`: `String` **[必填]** 环境组名称
  - `projectId`: `String` **[必填]** 项目ID
  - `description`: `String` 环境组描述
  - `envGroupProject`: `List<EnvironmentGroupProjectDTO>` 环境组id

**返回值**: `EnvironmentGroup`

#### **`GetMapping /project/environment/group/delete/{id}`** — 项目管理-环境组-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/environment/group/update`** — 项目管理-环境组-修改

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `EnvironmentGroupRequest` | Body |

**EnvironmentGroupRequest 字段明细**:
  - `id`: `String` 环境组id
  - `name`: `String` **[必填]** 环境组名称
  - `projectId`: `String` **[必填]** 项目ID
  - `description`: `String` 环境组描述
  - `envGroupProject`: `List<EnvironmentGroupProjectDTO>` 环境组id

**返回值**: `EnvironmentGroup`

#### **`PostMapping /project/environment/group/list`** — 项目管理-环境组-列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `EnvironmentFilterRequest` | Body |

**EnvironmentFilterRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project_parameters.project_id.length_range}");*
  - `keyword`: `String` 关键字

**返回值**: `List<EnvironmentGroup>`

#### **`GetMapping /project/environment/group/get/{id}`** — 项目管理-环境组-详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `EnvironmentGroupDTO`

#### **`GetMapping /project/environment/group/get-project/{organizationId}`** — 项目管理-环境组-获取项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `List<OptionDTO>`

#### **`PostMapping /project/environment/group/edit/pos`** — 项目管理-环境-环境组-修改排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PosRequest` | Body |

**PosRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目id
  - `moveId`: `String` **[必填]** 移动用例id
  - `targetId`: `String` **[必填]** 目标用例id
  - `moveMode`: `String` **[必填]** 移动类型

**返回值**: `void`


### FakeErrorController
**业务标签**: 项目管理-项目与权限-接口测试-误报规则配置

#### **`PostMapping /fake/error/add`** — 项目与权限-接口测试-新增误报规则

| 参数 | 类型 | 来源 |
|------|------|------|
| `dto` | `List<FakeErrorDTO>` | Body |

**返回值**: `ResultHolder`

#### **`PostMapping /fake/error/list`** — 项目与权限-接口测试-获取误报规则列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FakeErrorRequest` | Body |

**FakeErrorRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<FakeError>>`

#### **`PostMapping /fake/error/update`** — 项目与权限-接口测试-编辑误报规则

| 参数 | 类型 | 来源 |
|------|------|------|
| `requests` | `List<FakeErrorDTO>` | Body |

**返回值**: `ResultHolder`

#### **`PostMapping /fake/error/delete`** — 应用设置-接口测试-删除误报规则

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FakeErrorDelRequest` | Body |

**FakeErrorDelRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `void`

#### **`PostMapping /fake/error/update/enable`** — 项目与权限-接口测试-启用/禁用误报规则

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FakeErrorStatusRequest` | Body |

**FakeErrorStatusRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `enable`: `Boolean` 是否禁用
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `void`


### FileAssociationController
**业务标签**: 项目管理-文件管理-文件关联

#### **`GetMapping /project/file/association/list/{id}`** — 项目管理-文件管理-文件关联-文件资源关联列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `List<FileAssociationResponse>`

#### **`GetMapping /project/file/association/upgrade/{projectId}/{id}`** — 项目管理-文件管理-文件关联-更新资源关联的文件到最新版本

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `String`

#### **`PostMapping /project/file/association/delete`** — 项目管理-文件管理-文件关联-取消文件和资源的关联

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileAssociationDeleteRequest` | Body |

**FileAssociationDeleteRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目Id

**返回值**: `int`


### FileManagementController
**业务标签**: 项目管理-文件管理-文件

#### **`GetMapping /project/file/type/{projectId}`** — 项目管理-文件管理-获取已存在的文件类型

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<String>`

#### **`PostMapping /project/file/page`** — 项目管理-文件管理-表格分页查询文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileMetadataTableRequest` | Body |

**FileMetadataTableRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `moduleIds`: `List<String>` 模块ID(根据模块树查询时要把当前节点以及子节点都放在这里。)
  - `fileType`: `String` 文件类型
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<FileInformationResponse>>`

#### **`GetMapping /project/file/get/{id}`** — 项目管理-文件管理-查看文件详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `FileInformationResponse`

#### **`PostMapping /project/file/module/count`** — 项目管理-文件管理-表格分页查询文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileMetadataTableRequest` | Body |

**FileMetadataTableRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `moduleIds`: `List<String>` 模块ID(根据模块树查询时要把当前节点以及子节点都放在这里。)
  - `fileType`: `String` 文件类型
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Map<String, Long>`

#### **`PostMapping /project/file/upload`** — 项目管理-文件管理-上传文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileUploadRequest` | Form |
| `` | `(value = "file"` | Form |
| `uploadFile` | `required = false) MultipartFile` | 参数 |

**返回值**: `String`

#### **`PostMapping /project/file/re-upload`** — 项目管理-文件管理-重新上传文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileReUploadRequest` | Form |
| `` | `(value = "file"` | Form |
| `uploadFile` | `required = false) MultipartFile` | 参数 |

**返回值**: `String`

#### **`GetMapping /project/file/download/{id}`** — 项目管理-文件管理-下载文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /project/file/delete`** — 项目管理-文件管理-删除文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileBatchProcessRequest` | Body |

**FileBatchProcessRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID
  - `fileType`: `String` 文件类型
  - `moduleIds`: `List<String>` 模块ID

**返回值**: `void`

#### **`PostMapping /project/file/update`** — 项目管理-文件管理-修改文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileUpdateRequest` | Body |

**FileUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 文件Id
  - `name`: `String` 文件名称 *约束: @Size(min = 1, max = 255, message = "{file_metadata.name.length_range}");*
  - `description`: `String` 文件描述
  - `moduleId`: `String` 模块ID
  - `enable`: `Boolean` 开启/关闭(目前用于jar文件)

**返回值**: `void`

#### **`GetMapping /project/file/jar-file-status/{fileId}/{enable}`** — 项目管理-文件管理-Jar文件启用禁用操作

| 参数 | 类型 | 来源 |
|------|------|------|
| `fileId` | `String` | 路径 |
| `enable` | `boolean` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/file/batch-download`** — 项目管理-文件管理-批量下载文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileBatchProcessRequest` | Body |
| `httpServletResponse` | `HttpServletResponse` | 参数 |

**FileBatchProcessRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `projectId`: `String` **[必填]** 项目ID
  - `fileType`: `String` 文件类型
  - `moduleIds`: `List<String>` 模块ID

**返回值**: `void`

#### **`PostMapping /project/file/batch-move`** — 项目管理-文件管理-批量移动文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileBatchMoveRequest` | Body |

**FileBatchMoveRequest 字段明细**:
  > **继承**: `FileBatchProcessRequest`
  - `moveModuleId`: `String` **[必填]** 目标模块ID

**返回值**: `void`

#### **`GetMapping /project/file/file-version/{fileId}`** — 项目管理-文件管理-文件历史版本

| 参数 | 类型 | 来源 |
|------|------|------|
| `fileId` | `String` | 路径 |

**返回值**: `List<FileVersionResponse>`


### FileModuleController
**业务标签**: 项目管理-文件管理-模块

#### **`GetMapping /project/file-module/tree/{projectId}`** — 项目管理-文件管理-模块-查找模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /project/file-module/add`** — 项目管理-文件管理-模块-添加模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileModuleCreateRequest` | Body |

**FileModuleCreateRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{file_module.name.length_range}");*

**返回值**: `String`

#### **`PostMapping /project/file-module/update`** — 项目管理-文件管理-模块-修改模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileModuleUpdateRequest` | Body |

**FileModuleUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 模块ID
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{file_module.name.length_range}");*

**返回值**: `boolean`

#### **`GetMapping /project/file-module/delete/{deleteId}`** — 项目管理-文件管理-模块-删除模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `deleteId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/file-module/move`** — 项目管理-文件管理-模块-移动模块

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `NodeMoveRequest` | Body |

**NodeMoveRequest 字段明细**:
  - `dragNodeId`: `String` **[必填]** 被拖拽的节点
  - `dropNodeId`: `String` **[必填]** 放入的节点
  - `dropPosition`: `int` 放入的位置（取值：-1，,1。  -1：dropNodeId节点之前。 1：dropNodeId节点后）

**返回值**: `void`


### FilePreviewController
**业务标签**: 项目管理-文件预览

#### **`GetMapping /file/preview/original/{userId}/{fileId}`** — 预览原图

| 参数 | 类型 | 来源 |
|------|------|------|
| `userId` | `String` | 路径 |
| `fileId` | `String` | 路径 |

**返回值**: `ResponseEntity<byte[]>`

#### **`GetMapping /file/preview/compressed/{userId}/{fileId}`** — 预览缩略图

| 参数 | 类型 | 来源 |
|------|------|------|
| `userId` | `String` | 路径 |
| `fileId` | `String` | 路径 |

**返回值**: `ResponseEntity<byte[]>`


### FileRepositoryController
**业务标签**: 项目管理-文件管理-存储库

#### **`GetMapping /project/file/repository/list/{projectId}`** — 项目管理-文件管理-存储库-存储库列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<BaseTreeNode>`

#### **`GetMapping /project/file/repository/file-type/{projectId}`** — 项目管理-文件管理-存储库-获取已存在的存储库文件类型

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<String>`

#### **`PostMapping /project/file/repository/add-repository`** — 项目管理-文件管理-存储库-添加存储库

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileRepositoryCreateRequest` | Body |

**FileRepositoryCreateRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID
  - `name`: `String` **[必填]** 模块名称 *约束: @Size(min = 1, max = 255, message = "{file_module.name.length_range}");*
  - `platform`: `String` **[必填]** 存储库类型
  - `url`: `String` **[必填]** 存储库地址 *约束: @Size(min = 1, max = 255, message = "Url " + "{length.too.large}");*
  - `token`: `String` **[必填]** 存储库token
  - `userName`: `String` 用户名

**返回值**: `String`

#### **`GetMapping /project/file/repository/info/{id}`** — 项目管理-文件管理-存储库-存储库信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `FileRepositoryResponse`

#### **`PostMapping /project/file/repository/update-repository`** — 项目管理-文件管理-存储库-修改存储库

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileRepositoryUpdateRequest` | Body |

**FileRepositoryUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 模块ID
  - `name`: `String` 模块名称 *约束: @Size(min = 1, max = 255, message = "{file_module.name.length_range}");*
  - `platform`: `String` 存储库类型
  - `token`: `String` 存储库token
  - `userName`: `String` 用户名

**返回值**: `boolean`

#### **`PostMapping /project/file/repository/connect`** — 项目管理-文件管理-存储库-测试存储库链接

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `FileRepositoryConnectRequest` | Body |

**FileRepositoryConnectRequest 字段明细**:
  - `url`: `String` **[必填]** 存储库地址
  - `token`: `String` **[必填]** 存储库token
  - `userName`: `String` 用户名

**返回值**: `void`

#### **`PostMapping /project/file/repository/add-file`** — 项目管理-文件管理-存储库-添加文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `RepositoryFileAddRequest` | Body |

**RepositoryFileAddRequest 字段明细**:
  - `moduleId`: `String` **[必填]** 模块Id
  - `branch`: `String` **[必填]** 分支名
  - `filePath`: `String` **[必填]** 文件路径
  - `enable`: `boolean` 开启/关闭(目前用于jar文件)

**返回值**: `String`

#### **`GetMapping /project/file/repository/pull-file/{id}`** — 项目管理-文件管理-存储库-更新文件

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `String`


### GlobalParamsController
**业务标签**: 项目管理-环境-全局参数

#### **`PostMapping /project/global/params/add`** — 项目管理-环境-全局参数-新增

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `GlobalParamsRequest` | Body |

**GlobalParamsRequest 字段明细**:
  - `id`: `String` **[必填]** ID *约束: @Size(min = 1, max = 50, message = "{project_parameters.id.length_range}", groups = {Updated.class});*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project_parameters.project_id.length_range}", groups = {Created.class, Updated.class});*
  - `globalParams`: `GlobalParams` 全局参数

**返回值**: `ProjectParameter`

#### **`PostMapping /project/global/params/update`** — 项目管理-环境-全局参数-修改

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `GlobalParamsRequest` | Body |

**GlobalParamsRequest 字段明细**:
  - `id`: `String` **[必填]** ID *约束: @Size(min = 1, max = 50, message = "{project_parameters.id.length_range}", groups = {Updated.class});*
  - `projectId`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project_parameters.project_id.length_range}", groups = {Created.class, Updated.class});*
  - `globalParams`: `GlobalParams` 全局参数

**返回值**: `ProjectParameter`

#### **`GetMapping /project/global/params/get/{projectId}`** — 项目管理-环境-全局参数-详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `GlobalParamsDTO`

#### **`GetMapping /project/global/params/export/{projectId}`** — 项目管理-环境-全局参数-导出

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `ResponseEntity<byte[]>`

#### **`PostMapping /project/global/params/import`** — 项目管理-环境-全局参数-导入

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(value = "file"` | Form |
| `file` | `required = false) MultipartFile` | 参数 |

**返回值**: `void`


### NoticeMessageTaskController
**业务标签**: 项目管理-消息管理-消息设置

#### **`PostMapping notice/message/task/save`** — 项目管理-消息管理-消息设置-保存消息设置

| 参数 | 类型 | 来源 |
|------|------|------|
| `class` | `({Created.` | 参数 |
| `messageTaskRequest` | `Updated.class})  MessageTaskRequest` | Body |

**返回值**: `ResultHolder`

#### **`GetMapping notice/message/task/get/{projectId}`** — 项目管理-消息管理-消息设置-获取消息设置

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<MessageTaskDTO>`

#### **`GetMapping notice/message/task/get/user/{projectId}`** — 项目管理-消息管理-消息设置-获取用户列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<OptionDTO>`

#### **`GetMapping notice/message/template/detail/{projectId}`** — 项目管理-消息管理-消息设置-查看消息模版详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `taskType` | `String` | Query |
| `event` | `String` | Query |
| `robotId` | `String` | Query |

**返回值**: `MessageTemplateConfigDTO`


### NoticeTemplateController
**业务标签**: 项目管理-消息设置-模版设置

#### **`GetMapping notice/template/get/fields/{projectId}`** — 项目管理-消息设置-模版设置-获取消息模版字段

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `taskType` | `String` | Query |

**返回值**: `MessageTemplateResultDTO`


### ProjectApplicationController
**业务标签**: 项目管理-项目与权限-菜单管理

#### **`PostMapping /project/application/update/test-plan`** — 测试计划-配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `application` | `ProjectApplication` | Body |

**返回值**: `void`

#### **`PostMapping /project/application/test-plan`** — 测试计划-获取配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectApplicationRequest` | Body |

**返回值**: `Map<String, Object>`

#### **`PostMapping /project/application/update/api`** — 接口测试-配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `application` | `ProjectApplication` | Body |

**返回值**: `void`

#### **`PostMapping /project/application/api`** — 接口测试-获取配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectApplicationRequest` | Body |

**返回值**: `Map<String, Object>`

#### **`PostMapping /project/application/update/task`** — 任务中心-配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `application` | `ProjectApplication` | Body |

**返回值**: `void`

#### **`PostMapping /project/application/task`** — 任务中心-获取配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectApplicationRequest` | Body |

**返回值**: `Map<String, Object>`

#### **`GetMapping /project/application/api/user/{projectId}`** — 接口测试-获取审核人

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<User>`

#### **`GetMapping /project/application/api/resource/pool/{projectId}`** — 接口测试-获取资源池列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<OptionDTO>`

#### **`PostMapping /project/application/update/case`** — 用例管理-配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `application` | `ProjectApplication` | Body |

**返回值**: `void`

#### **`PostMapping /project/application/case`** — 用例管理-获取配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectApplicationRequest` | Body |

**返回值**: `Map<String, Object>`

#### **`GetMapping /project/application/case/platform/{organizationId}`** — 用例管理-获取平台下拉框列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `List<OptionDTO>`

#### **`GetMapping /project/application/case/platform/info/{pluginId}`** — 用例管理-选择平台获取平台信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `pluginId` | `String` | 路径 |

**返回值**: `Object`

#### **`PostMapping /project/application/update/case/related/{projectId}`** — 用例管理-关联需求

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `configs` | `Map<String, String>` | Body |

**返回值**: `void`

#### **`GetMapping /project/application/case/related/info/{projectId}`** — 用例管理-获取关联需求信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `Map<String, String>`

#### **`PostMapping /project/application/update/bug`** — 缺陷管理-配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `application` | `ProjectApplication` | Body |

**返回值**: `void`

#### **`PostMapping /project/application/bug`** — 缺陷管理-获取配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectApplicationRequest` | Body |

**返回值**: `Map<String, Object>`

#### **`GetMapping /project/application/bug/platform/{organizationId}`** — 缺陷管理-获取平台下拉框列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `List<OptionDTO>`

#### **`GetMapping /project/application/bug/platform/info/{pluginId}`** — 缺陷管理-选择平台获取平台信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `pluginId` | `String` | 路径 |

**返回值**: `Object`

#### **`PostMapping /project/application/update/bug/sync/{projectId}`** — 缺陷管理-同步缺陷配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `configs` | `Map<String, Object>` | Body |

**返回值**: `void`

#### **`GetMapping /project/application/bug/sync/info/{projectId}`** — 缺陷管理-获取同步缺陷信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `Map<String, String>`

#### **`GetMapping /project/application/module-setting/{projectId}`** — 获取菜单列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<ModuleDTO>`

#### **`PostMapping /project/application/validate/{pluginId}`** — 插件key校验

| 参数 | 类型 | 来源 |
|------|------|------|
| `pluginId` | `String` | 路径 |
| `configs` | `Map` | Body |

**返回值**: `void`


### ProjectController
**业务标签**: 项目管理

#### **`GetMapping /project/get/{id}`** — 项目管理-基本信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ProjectDTO`

#### **`GetMapping /project/list/options/{organizationId}`** — 根据组织ID获取所有有权限的项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `List<Project>`

#### **`GetMapping /project/list/options/{organizationId}/{module}`** — 根据组织ID获取所有开启某个模块的所有有权限的项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `module` | `String` | 路径 |

**返回值**: `List<Project>`

#### **`PostMapping /project/switch`** — 切换项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectSwitchRequest` | Body |

**返回值**: `UserDTO`

#### **`PostMapping /project/update`** — 项目管理-更新项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectRequest` | Body |

**ProjectRequest 字段明细**:
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{project.organization_id.length_range}", groups = {Created.class, Updated.class});*
  - `name`: `String` **[必填]** 项目名称 *约束: @Size(min = 1, max = 255, message = "{project.name.length_range}", groups = {Created.class, Updated.class});*
  - `description`: `String` 项目描述 *约束: @Size(min = 0, max = 1000, message = "{project.description.length_range}", groups = {Created.class, Updated.class});*
  - `enable`: `Boolean` 是否启用
  - `id`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project.id.length_range}", groups = {Updated.class});*

**返回值**: `ProjectDTO`

#### **`GetMapping /project/pool-options/{type}/{projectId}`** — 项目管理-获取项目下的资源池

| 参数 | 类型 | 来源 |
|------|------|------|
| `type` | `String` | 路径 |
| `projectId` | `String` | 路径 |

**返回值**: `List<OptionDTO>`

#### **`GetMapping /project/has-permission/{id}`** — 项目管理-获取当前用户是否有当前项目的权限

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `boolean`

#### **`GetMapping /project/get-member/option/{projectId}`** — 项目管理-获取成员下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserExtendDTO>`


### ProjectCustomFieldController
**业务标签**: 项目管理-自定义字段

#### **`GetMapping /project/custom/field/list/{projectId}/{scene}`** — 获取自定义字段列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "项目ID"` | 参数 |
| `projectId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `FUNCTIONAL` | `(description = "模板的使用场景（` | 参数 |
| `BUG` | `` | 参数 |
| `API` | `` | 参数 |
| `UI` | `` | 参数 |
| `` | `TEST_PLAN）"` | 参数 |
| `scene` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |

**返回值**: `List<CustomFieldDTO>`

#### **`GetMapping /project/custom/field/get/{id}`** — 获取自定义字段详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `CustomFieldDTO`

#### **`PostMapping /project/custom/field/add`** — 创建自定义字段

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CustomFieldUpdateRequest` | Body |

**CustomFieldUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 自定义字段ID *约束: @Size(min = 1, max = 50, message = "{custom_field.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 自定义字段名称 *约束: @Size(min = 1, max = 255, message = "{custom_field.name.length_range}", groups = {Created.class, Updated.class});*
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class, groups = {Created.class}); @Size(min = 1, max = 30, message = "{custom_field.scene.length_range}", groups = {Created.class});*
  - `type`: `String` **[必填]** 自定义字段类型 *约束: @EnumValue(enumClass = CustomFieldType.class, groups = {Created.class, Updated.class}); @Size(min = 1, max = 30, message = "{custom_field.type.length_range}", groups = {Created.class, Updated.class});*
  - `remark`: `String` 自定义字段备注 *约束: @Size(max = 1000, message = "{custom_field.remark.length_range}", groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 组织或项目ID *约束: @Size(min = 1, max = 50, message = "{custom_field.scope_id.length_range}", groups = {Created.class});*
  - `enableOptionKey`: `Boolean` 是否需要手动输入选项key
  - `options`: `List<CustomFieldOptionRequest>` 自定义字段选项 *约束: @Valid;*

**返回值**: `CustomField`

#### **`PostMapping /project/custom/field/update`** — 更新自定义字段

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CustomFieldUpdateRequest` | Body |

**CustomFieldUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 自定义字段ID *约束: @Size(min = 1, max = 50, message = "{custom_field.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 自定义字段名称 *约束: @Size(min = 1, max = 255, message = "{custom_field.name.length_range}", groups = {Created.class, Updated.class});*
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class, groups = {Created.class}); @Size(min = 1, max = 30, message = "{custom_field.scene.length_range}", groups = {Created.class});*
  - `type`: `String` **[必填]** 自定义字段类型 *约束: @EnumValue(enumClass = CustomFieldType.class, groups = {Created.class, Updated.class}); @Size(min = 1, max = 30, message = "{custom_field.type.length_range}", groups = {Created.class, Updated.class});*
  - `remark`: `String` 自定义字段备注 *约束: @Size(max = 1000, message = "{custom_field.remark.length_range}", groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 组织或项目ID *约束: @Size(min = 1, max = 50, message = "{custom_field.scope_id.length_range}", groups = {Created.class});*
  - `enableOptionKey`: `Boolean` 是否需要手动输入选项key
  - `options`: `List<CustomFieldOptionRequest>` 自定义字段选项 *约束: @Valid;*

**返回值**: `CustomField`

#### **`GetMapping /project/custom/field/delete/{id}`** — 删除自定义字段

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`


### ProjectLogController
**业务标签**: 项目管理-日志

#### **`GetMapping /project/log/user/list/{projectId}`** — 项目管理-日志-获取用户列表-支持远程搜索

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<User>`

#### **`PostMapping /project/log/list`** — 项目管理-日志--操作日志列表查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProOperationLogRequest` | Body |

**返回值**: `Pager<List<OperationLogResponse>>`


### ProjectMemberController
**业务标签**: 项目管理-成员

#### **`PostMapping /project/member/list`** — 项目管理-成员-列表查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectMemberRequest` | Body |

**ProjectMemberRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<ProjectUserDTO>>`

#### **`GetMapping /project/member/get-member/option/{projectId}`** — 项目管理-成员-获取成员下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserExtendDTO>`

#### **`GetMapping /project/member/get-role/option/{projectId}`** — 项目管理-成员-获取用户组下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<OptionDTO>`

#### **`PostMapping /project/member/add`** — 项目管理-成员-添加成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectMemberAddRequest` | Body |

**返回值**: `void`

#### **`PostMapping /project/member/invite`** — 系统设置-组织-成员-邀请用户注册

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserInviteRequest` | Body |

**UserInviteRequest 字段明细**:
  - `organizationId`: `String` 组织ID
  - `projectId`: `String` 项目ID

**返回值**: `UserInviteResponse`

#### **`PostMapping /project/member/update`** — 项目管理-成员-编辑成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectMemberEditRequest` | Body |

**返回值**: `void`

#### **`GetMapping /project/member/remove/{projectId}/{userId}`** — 项目管理-成员-移除成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `userId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/member/add-role`** — 项目管理-成员-批量添加至用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectMemberAddRoleRequest` | Body |

**返回值**: `void`

#### **`PostMapping /project/member/batch/remove`** — 项目管理-成员-批量从项目移除

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectMemberBatchDeleteRequest` | Body |

**返回值**: `void`

#### **`GetMapping /project/member/comment/user-option/{projectId}`** — 项目管理-成员-获取评论用户@下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<CommentUserInfo>`

#### **`PostMapping /project/member/update-member`** — 系统设置-系统-组织与项-项目-更新成员用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectMemberEditRequest` | Body |

**返回值**: `void`


### ProjectRobotController
**业务标签**: 项目管理-消息管理-机器人

#### **`GetMapping /project/robot/list/{projectId}`** — 项目管理-消息管理-获取机器人列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `List<ProjectRobot>`

#### **`PostMapping /project/robot/add`** — 项目管理-消息管理-新增机器人

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectRobotDTO` | `ProjectRobotDTO` | Body |

**ProjectRobotDTO 字段明细**:
  - `id`: `String` **[必填]** id
  - `name`: `String` **[必填]** 名称
  - `platform`: `String` 所属平台（飞书:LARK，钉钉:DING_TALK，企业微信:WE_COM，自定义:CUSTOM, 站内信:IN_SITE, 邮件:MAIL）
  - `webhook`: `String` webhook
  - `type`: `String` 钉钉机器人的种类: 自定义:CUSTOM, 企业内部:ENTERPRISE
  - `appKey`: `String` 钉钉AppKey
  - `appSecret`: `String` 钉钉AppSecret
  - `enable`: `Boolean` 是否启用
  - `description`: `String` 描述
  - `projectId`: `String` **[必填]** 项目id

**返回值**: `ProjectRobot`

#### **`PostMapping /project/robot/update`** — 项目管理-消息管理-更新机器人

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectRobotDTO` | `ProjectRobotDTO` | Body |

**ProjectRobotDTO 字段明细**:
  - `id`: `String` **[必填]** id
  - `name`: `String` **[必填]** 名称
  - `platform`: `String` 所属平台（飞书:LARK，钉钉:DING_TALK，企业微信:WE_COM，自定义:CUSTOM, 站内信:IN_SITE, 邮件:MAIL）
  - `webhook`: `String` webhook
  - `type`: `String` 钉钉机器人的种类: 自定义:CUSTOM, 企业内部:ENTERPRISE
  - `appKey`: `String` 钉钉AppKey
  - `appSecret`: `String` 钉钉AppSecret
  - `enable`: `Boolean` 是否启用
  - `description`: `String` 描述
  - `projectId`: `String` **[必填]** 项目id

**返回值**: `void`

#### **`GetMapping /project/robot/get/{id}`** — 项目管理-消息管理-获取机器人详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ProjectRobotDTO`

#### **`GetMapping /project/robot/delete/{id}`** — 项目管理-消息管理-删除机器人

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /project/robot/enable/{id}`** — 项目管理-消息管理-启禁用机器人

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`


### ProjectStatusFlowSettingController
**业务标签**: 项目管理-模板-状态流设置

#### **`GetMapping /project/status/flow/setting/get/{projectId}/{scene}`** — 项目管理-模板-状态流设置-获取状态流设置

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "组织ID"` | 参数 |
| `projectId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `FUNCTIONAL` | `(description = "模板的使用场景（` | 参数 |
| `BUG` | `` | 参数 |
| `API` | `` | 参数 |
| `UI` | `` | 参数 |
| `` | `TEST_PLAN）"` | 参数 |
| `scene` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |

**返回值**: `List<StatusItemDTO>`

#### **`PostMapping /project/status/flow/setting/status/definition/update`** — 项目管理-模板-状态流设置-设置状态定义，即起始状态，结束状态

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `StatusDefinitionUpdateRequest` | Body |

**StatusDefinitionUpdateRequest 字段明细**:
  - `statusId`: `String` **[必填]** 状态ID *约束: @Size(min = 1, max = 50, message = "{status_definition.status_id.length_range}");*
  - `definitionId`: `String` **[必填]** 状态定义ID(在代码中定义) *约束: @Size(min = 1, max = 100, message = "{status_definition.definition_id.length_range}");*
  - `enable`: `Boolean` **[必填]** 启用或者禁用

**返回值**: `void`

#### **`PostMapping /project/status/flow/setting/status/sort/{projectId}/{scene}`** — 系统设置-组织-状态流设置-状态项排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `` | 路径 |
| `scene` | `` | 路径 |
| `statusIds` | `<String>` | Body |

**返回值**: `void`

#### **`PostMapping /project/status/flow/setting/status/add`** — 项目管理-模板-状态流设置-添加状态项

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `StatusItemAddRequest` | Body |

**StatusItemAddRequest 字段明细**:
  - `scopeId`: `String` **[必填]** 组织ID或项目ID *约束: @Size(min = 1, max = 50);*
  - `name`: `String` **[必填]** 状态名称 *约束: @Size(min = 1, max = 255, message = "{status_item.name.length_range}");*
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class);*
  - `remark`: `String` 状态说明 *约束: @Size(max = 1000);*
  - `allTransferTo`: `Boolean` 所有状态都可以流转到该状态

**返回值**: `StatusItem`

#### **`PostMapping /project/status/flow/setting/status/update`** — 项目管理-模板-状态流设置-修改状态项

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `StatusItemUpdateRequest` | Body |

**StatusItemUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 状态ID *约束: @Size(min = 1, max = 50, message = "{status_item.id.length_range}");*
  - `name`: `String` 状态名称 *约束: @Size(min = 1, max = 255, message = "{status_item.name.length_range}");*
  - `remark`: `String` 状态说明 *约束: @Size(max = 1000);*

**返回值**: `StatusItem`

#### **`GetMapping /project/status/flow/setting/status/delete/{id}`** — 项目管理-模板-状态流设置-删除状态项

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/status/flow/setting/status/flow/update`** — 项目管理-模板-状态流设置-设置状态流转

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `StatusFlowUpdateRequest` | Body |

**StatusFlowUpdateRequest 字段明细**:
  - `fromId`: `String` **[必填]** 起始状态ID *约束: @Size(min = 1, max = 50, message = "{status_flow.from_id.length_range}");*
  - `toId`: `String` **[必填]** 目的状态ID *约束: @Size(min = 1, max = 50, message = "{status_flow.to_id.length_range}");*
  - `enable`: `Boolean` **[必填]** 启用或者禁用

**返回值**: `void`


### ProjectTaskHubController
**业务标签**: 项目任务中心

#### **`PostMapping /project/task-center/exec-task/page`** — 项目-任务中心-执行任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BasePageRequest` | Body |

**BasePageRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `current`: `int` 当前页码 *约束: @Min(value = 1, message = "当前页码必须大于0");*
  - `pageSize`: `int` 每页显示条数 *约束: @Min(value = 5, message = "每页显示条数必须不小于5"); @Max(value = 500, message = "每页显示条数不能大于500");*

**返回值**: `Pager<List<TaskHubDTO>>`

#### **`PostMapping /project/task-center/schedule/page`** — 项目-任务中心-后台执行任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BasePageRequest` | Body |

**BasePageRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `current`: `int` 当前页码 *约束: @Min(value = 1, message = "当前页码必须大于0");*
  - `pageSize`: `int` 每页显示条数 *约束: @Min(value = 5, message = "每页显示条数必须不小于5"); @Max(value = 500, message = "每页显示条数不能大于500");*

**返回值**: `Pager<List<TaskHubScheduleDTO>>`

#### **`PostMapping /project/task-center/exec-task/item/page`** — 项目-任务中心-用例执行任务详情列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskHubItemRequest` | Body |

**TaskHubItemRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `taskId`: `String` 任务id
  - `resourcePoolIds`: `List<String>` 资源池id
  - `resourcePoolNodes`: `List<String>` 资源池节点

**返回值**: `Pager<List<TaskHubItemDTO>>`

#### **`PostMapping /project/task-center/exec-task/statistics`** — 项目-任务中心-获取任务统计{通过率}接口

| 参数 | 类型 | 来源 |
|------|------|------|
| `ids` | `List<String>` | Body |

**返回值**: `List<TaskStatisticsResponse>`

#### **`GetMapping /project/task-center/resource-pool/options`** — 项目-任务中心-获取资源池下拉选项

**无入参**

**返回值**: `List<ResourcePoolOptionsDTO>`

#### **`GetMapping /project/task-center/exec-task/stop/{id}`** — 项目-任务中心-用例执行任务-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /project/task-center/exec-task/rerun/{id}`** — 项目-任务中心-用例执行任务-重跑任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/task-center/exec-task/batch-stop`** — 项目-任务中心-用例执行任务-批量停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /project/task-center/exec-task/item/order`** — 系统-任务中心-用例执行任务-获取任务项的排队信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskIdItemIds` | `List<String>` | Body |

**返回值**: `Map<String, Integer>`

#### **`GetMapping /project/task-center/exec-task/delete/{id}`** — 项目-任务中心-用例执行任务-删除任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/task-center/exec-task/batch-delete`** — 项目-任务中心-用例执行任务-批量删除任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`GetMapping /project/task-center/exec-task/item/stop/{id}`** — 项目-任务中心-用例任务详情-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/task-center/exec-task/item/batch-stop`** — 项目-任务中心-用例任务详情-批量停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskHubItemBatchRequest` | Body |

**TaskHubItemBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `taskId`: `String` 任务id
  - `resourcePoolIds`: `List<String>` 资源池id
  - `resourcePoolNodes`: `List<String>` 资源池节点

**返回值**: `void`

#### **`GetMapping /project/task-center/schedule/delete/{id}`** — 项目-任务中心-系统后台任务-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /project/task-center/schedule/switch/{id}`** — 项目-任务中心-后台任务开启关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /project/task-center/schedule/batch-enable`** — 项目-任务中心-后台任务-批量开启

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /project/task-center/schedule/batch-disable`** — 项目-任务中心-后台任务-批量关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /project/task-center/schedule/update-cron`** — 项目-任务中心-后台任务更新cron表达式

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ScheduleRequest` | Body |

**ScheduleRequest 字段明细**:
  - `id`: `String` 列表id
  - `cron`: `String` cron表达式

**返回值**: `void`

#### **`PostMapping /project/task-center/exec-task/batch/page`** — 项目-任务中心-用例执行任务-批量任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BatchExecTaskPageRequest` | Body |

**BatchExecTaskPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `taskId`: `String` 任务ID
  - `batchType`: `String`

**返回值**: `Pager<List<BatchExecTaskReportDTO>>`


### ProjectTemplateController
**业务标签**: 项目管理-模版

#### **`GetMapping /project/template/list/{projectId}/{scene}`** — 获取模版列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "项目ID"` | 参数 |
| `projectId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `FUNCTIONAL` | `(description = "模板的使用场景（` | 参数 |
| `BUG` | `` | 参数 |
| `API` | `` | 参数 |
| `UI` | `` | 参数 |
| `` | `TEST_PLAN）"` | 参数 |
| `scene` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |

**返回值**: `List<ProjectTemplateDTO>`

#### **`GetMapping /project/template/get/{id}`** — 获取模版详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `TemplateDTO`

#### **`PostMapping /project/template/add`** — 创建模版

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TemplateUpdateRequest` | Body |

**TemplateUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** ID *约束: @Size(min = 1, max = 50, message = "{template.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 名称 *约束: @Size(min = 1, max = 255, message = "{template.name.length_range}", groups = {Created.class, Updated.class});*
  - `remark`: `String` 备注 *约束: @Size(max = 1000, groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 组织或项目ID *约束: @Size(min = 1, max = 50, message = "{template.scope_id.length_range}", groups = {Created.class, Updated.class});*
  - `enableThirdPart`: `Boolean` 是否开启api字段名配置
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class, groups = {Created.class}); @Size(min = 1, max = 30, message = "{template.scene.length_range}", groups = {Created.class});*
  - `customFields`: `List<TemplateCustomFieldRequest>` 自定义字段Id列表 *约束: @Valid;*
  - `systemFields`: `List<TemplateSystemCustomFieldRequest>` 系统字段列表 *约束: @Valid;*
  - `uploadImgFileIds`: `List<String>` 模板中新上传的文件ID列表

**返回值**: `Template`

#### **`PostMapping /project/template/update`** — 更新模版

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TemplateUpdateRequest` | Body |

**TemplateUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** ID *约束: @Size(min = 1, max = 50, message = "{template.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 名称 *约束: @Size(min = 1, max = 255, message = "{template.name.length_range}", groups = {Created.class, Updated.class});*
  - `remark`: `String` 备注 *约束: @Size(max = 1000, groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 组织或项目ID *约束: @Size(min = 1, max = 50, message = "{template.scope_id.length_range}", groups = {Created.class, Updated.class});*
  - `enableThirdPart`: `Boolean` 是否开启api字段名配置
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class, groups = {Created.class}); @Size(min = 1, max = 30, message = "{template.scene.length_range}", groups = {Created.class});*
  - `customFields`: `List<TemplateCustomFieldRequest>` 自定义字段Id列表 *约束: @Valid;*
  - `systemFields`: `List<TemplateSystemCustomFieldRequest>` 系统字段列表 *约束: @Valid;*
  - `uploadImgFileIds`: `List<String>` 模板中新上传的文件ID列表

**返回值**: `Template`

#### **`GetMapping /project/template/delete/{id}`** — 删除模版

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /project/template/set-default/{projectId}/{id}`** — 设置默认模板

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /project/template/enable/config/{projectId}`** — 是否启用组织模版

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `Map<String, Boolean>`

#### **`PostMapping /project/template/upload/temp/img`** — 上传富文本图片，并返回文件ID

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`GetMapping /project/template/img/preview/{projectId}/{fileId}/{compressed}`** — 富文本图片-预览

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `fileId` | `String` | 路径 |
| `compressed` | `boolean` | 路径 |

**返回值**: `ResponseEntity<byte[]>`


### ProjectUserRoleController
**业务标签**: 项目管理-项目与权限-用户组

#### **`PostMapping /user/role/project/list`** — 项目管理-项目与权限-用户组-获取用户组列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectUserRoleRequest` | Body |

**返回值**: `Pager<List<ProjectUserRoleDTO>>`

#### **`PostMapping /user/role/project/add`** — 项目管理-项目与权限-用户组-添加用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectUserRoleEditRequest` | Body |

**返回值**: `UserRole`

#### **`PostMapping /user/role/project/update`** — 项目管理-项目与权限-用户组-修改用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectUserRoleEditRequest` | Body |

**返回值**: `UserRole`

#### **`GetMapping /user/role/project/delete/{id}`** — 项目管理-项目与权限-用户组-删除用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /user/role/project/permission/setting/{id}`** — 项目管理-项目与权限-用户组-获取用户组对应的权限配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `List<PermissionDefinitionItem>`

#### **`PostMapping /user/role/project/permission/update`** — 项目管理-项目与权限-用户组-修改用户组对应的权限配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PermissionSettingUpdateRequest` | Body |

**PermissionSettingUpdateRequest 字段明细**:
  - `userRoleId`: `String` **[必填]** 用户组ID
  - `permissions`: `List<PermissionUpdateRequest>` **[必填]** 菜单下的权限列表 *约束: @Valid;*
  - `id`: `String` **[必填]** 权限ID

**返回值**: `void`

#### **`GetMapping /user/role/project/get-member/option/{projectId}/{roleId}`** — 项目管理-项目与权限-用户组-获取成员下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `roleId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserExtendDTO>`

#### **`PostMapping /user/role/project/list-member`** — 项目管理-项目与权限-用户组-获取成员列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectUserRoleMemberRequest` | Body |

**返回值**: `Pager<List<User>>`

#### **`PostMapping /user/role/project/add-member`** — 项目管理-项目与权限-用户组-添加用户组成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectUserRoleMemberEditRequest` | Body |

**返回值**: `void`

#### **`PostMapping /user/role/project/remove-member`** — 项目管理-项目与权限-用户组-删除用户组成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectUserRoleMemberEditRequest` | Body |

**返回值**: `void`


## system-setting 模块

共 32 个 Controller，277 个接口


### AiConversationController
**业务标签**: AI对话

#### **`GetMapping /ai/conversation/list`** — 对话列表

**无入参**

**返回值**: `List<AiConversation>`

#### **`GetMapping /ai/conversation/chat/list/{conversationId}`** — 对话内容列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `conversationId` | `String` | 路径 |

**返回值**: `List<AiConversationContent>`

#### **`PostMapping /ai/conversation/add`** — 添加对话

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AIChatRequest` | Body |

**AIChatRequest 字段明细**:
  - `prompt`: `String` **[必填]** 提示词
  - `chatModelId`: `String` **[必填]** 模型ID
  - `conversationId`: `String` **[必填]** 对话ID
  - `organizationId`: `String` **[必填]** 组织ID

**返回值**: `AiConversation`

#### **`PostMapping /ai/conversation/update`** — 修改对话标题

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AIConversationUpdateRequest` | Body |

**AIConversationUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** ID
  - `title`: `String` 标题

**返回值**: `AiConversation`

#### **`PostMapping /ai/conversation/chat`** — 聊天

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AIChatRequest` | Body |

**AIChatRequest 字段明细**:
  - `prompt`: `String` **[必填]** 提示词
  - `chatModelId`: `String` **[必填]** 模型ID
  - `conversationId`: `String` **[必填]** 对话ID
  - `organizationId`: `String` **[必填]** 组织ID

**返回值**: `String`

#### **`GetMapping /ai/conversation/delete/{conversationId}`** — 删除对话

| 参数 | 类型 | 来源 |
|------|------|------|
| `conversationId` | `String` | 路径 |

**返回值**: `void`


### BaseDisplayController
**业务标签**: 首页图片

#### **`GetMapping /base-display/get/icon`**

**无入参**

**返回值**: `ResponseEntity<byte[]>`

#### **`GetMapping /base-display/get/login-image`**

**无入参**

**返回值**: `ResponseEntity<byte[]>`

#### **`GetMapping /base-display/get/login-logo`**

**无入参**

**返回值**: `ResponseEntity<byte[]>`

#### **`GetMapping /base-display/get/logo-platform`**

**无入参**

**返回值**: `ResponseEntity<byte[]>`


### GlobalUserRoleController
**业务标签**: 系统设置-系统-用户组

#### **`GetMapping /user/role/global/list`** — 系统设置-系统-用户组-获取全局用户组列表

**无入参**

**返回值**: `List<UserRole>`

#### **`GetMapping /user/role/global/permission/setting/{id}`** — 系统设置-系统-用户组-获取全局用户组对应的权限配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `List<PermissionDefinitionItem>`

#### **`PostMapping /user/role/global/permission/update`** — 系统设置-系统-用户组-编辑全局用户组对应的权限配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PermissionSettingUpdateRequest` | Body |

**PermissionSettingUpdateRequest 字段明细**:
  - `userRoleId`: `String` **[必填]** 用户组ID
  - `permissions`: `List<PermissionUpdateRequest>` **[必填]** 菜单下的权限列表 *约束: @Valid;*
  - `id`: `String` **[必填]** 权限ID

**返回值**: `void`

#### **`PostMapping /user/role/global/add`** — 系统设置-系统-用户组-添加自定义全局用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserRoleUpdateRequest` | Body |

**UserRoleUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 组ID *约束: @Size(min = 1, max = 50, message = "{user_role.id.length_range}", groups = {Created.class, Updated.class});*
  - `name`: `String` **[必填]** 组名称 *约束: @Size(min = 1, max = 255, message = "{user_role.name.length_range}", groups = {Created.class, Updated.class});*
  - `description`: `String` 描述 *约束: @Size(max = 1000, groups = {Created.class, Updated.class});*
  - `type`: `String` **[必填]** 所属类型 SYSTEM ORGANIZATION PROJECT *约束: @EnumValue(enumClass = UserRoleType.class, groups = {Created.class, Updated.class}); @Size(min = 1, max = 20, message = "{user_role.type.length_range}", groups = {Created.class, Updated.class});*

**返回值**: `UserRole`

#### **`PostMapping /user/role/global/update`** — 系统设置-系统-用户组-更新自定义全局用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserRoleUpdateRequest` | Body |

**UserRoleUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 组ID *约束: @Size(min = 1, max = 50, message = "{user_role.id.length_range}", groups = {Created.class, Updated.class});*
  - `name`: `String` **[必填]** 组名称 *约束: @Size(min = 1, max = 255, message = "{user_role.name.length_range}", groups = {Created.class, Updated.class});*
  - `description`: `String` 描述 *约束: @Size(max = 1000, groups = {Created.class, Updated.class});*
  - `type`: `String` **[必填]** 所属类型 SYSTEM ORGANIZATION PROJECT *约束: @EnumValue(enumClass = UserRoleType.class, groups = {Created.class, Updated.class}); @Size(min = 1, max = 20, message = "{user_role.type.length_range}", groups = {Created.class, Updated.class});*

**返回值**: `UserRole`

#### **`GetMapping /user/role/global/delete/{id}`** — 系统设置-系统-用户组-删除自定义全局用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`


### GlobalUserRoleRelationController
**业务标签**: 系统设置-系统-用户组-用户关联关系

#### **`PostMapping /user/role/relation/global/list`** — 系统设置-系统-用户组-用户关联关系-获取全局用户组对应的用户列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `GlobalUserRoleRelationQueryRequest` | Body |

**GlobalUserRoleRelationQueryRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `roleId`: `String` **[必填]** 用户组ID

**返回值**: `Pager<List<UserRoleRelationUserDTO>>`

#### **`PostMapping /user/role/relation/global/add`** — 系统设置-系统-用户组-用户关联关系-创建全局用户组和用户的关联关系

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `GlobalUserRoleRelationUpdateRequest` | Body |

**GlobalUserRoleRelationUpdateRequest 字段明细**:
  - `roleId`: `String` **[必填]** 组ID *约束: @Size(min = 1, max = 50, message = "{user_role_relation.role_id.length_range}", groups = {Created.class, Updated.class});*
  - `createUser`: `String`

**返回值**: `void`

#### **`GetMapping /user/role/relation/global/delete/{id}`** — 系统设置-系统-用户组-用户关联关系-删除全局用户组和用户的关联关系

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /user/role/relation/global/user/option/{roleId}`** — 系统设置-系统-用户组-用户关联关系-获取需要关联的用户选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "用户组ID"` | 参数 |
| `roleId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `` | `(description = "查询关键字，根据邮箱和用户名查询"` | 参数 |
| `` | `requiredMode = Schema.RequiredMode.REQUIRED)(value = "keyword"` | Query |
| `keyword` | `required = false) String` | 参数 |

**返回值**: `List<UserExcludeOptionDTO>`


### LicenseController
**业务标签**: 系统设置-系统-授权管理

#### **`GetMapping /license/validate`** — license校验

**无入参**

**返回值**: `LicenseDTO`

#### **`PostMapping /license/add`** — 添加有效的License

| 参数 | 类型 | 来源 |
|------|------|------|
| `licenseCode` | `TextNode` | Body |

**返回值**: `LicenseDTO`


### LoginController
**业务标签**: 登录

#### **`GetMapping /is-login`** — 是否登录

| 参数 | 类型 | 来源 |
|------|------|------|
| `response` | `HttpServletResponse` | 参数 |

**返回值**: `ResultHolder`

#### **`GetMapping /get-key`** — 获取公钥

**无入参**

**返回值**: `ResultHolder`

#### **`PostMapping /login`** — 登录

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `LoginRequest` | Body |

**LoginRequest 字段明细**:
  - `username`: `String` **[必填]** *约束: @Size(max = 256, message = "{user_name_length_too_long}");*
  - `password`: `String` **[必填]** *约束: @Size(max = 256, message = "{password_length_too_long}");*
  - `authenticate`: `String`

**返回值**: `ResultHolder`

#### **`GetMapping /signout`** — 退出登录

**无入参**

**返回值**: `ResultHolder`


### NotificationController
**业务标签**: 消息中心

#### **`PostMapping notification/list/all/page`** — 消息中心-获取消息中心所有消息列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `notificationRequest` | `NotificationRequest` | Body |

**NotificationRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `id`: `Long` ID
  - `type`: `String` 通知类型
  - `receiver`: `String` 接收人
  - `title`: `String` 标题
  - `status`: `String` 状态
  - `resourceType`: `String` 资源类型: TEST_PLAN/BUG/CASE/API/UI/LOAD/JENKINS/SCHEDULE
  - `createTime`: `Long` 创建时间
  - `operator`: `String` 操作人
  - `operation`: `String` 操作

**返回值**: `Pager<List<NotificationDTO>>`

#### **`GetMapping notification/read/{id}`** — 消息中心-将消息设置为已读

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `long` | 路径 |

**返回值**: `Integer`

#### **`GetMapping notification/read/all`** — 消息中心-将消息中心所有信息设置为已读消息

| 参数 | 类型 | 来源 |
|------|------|------|
| `resourceType` | `String` | Query |

**返回值**: `Integer`

#### **`GetMapping notification/un-read/{projectId}`** — 消息中心-获取未读的消息

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |

**返回值**: `Integer`

#### **`PostMapping notification/count`** — 消息中心-获取消息中心消息具体类型具体状态的数量

| 参数 | 类型 | 来源 |
|------|------|------|
| `notificationRequest` | `NotificationRequest` | Body |

**NotificationRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `id`: `Long` ID
  - `type`: `String` 通知类型
  - `receiver`: `String` 接收人
  - `title`: `String` 标题
  - `status`: `String` 状态
  - `resourceType`: `String` 资源类型: TEST_PLAN/BUG/CASE/API/UI/LOAD/JENKINS/SCHEDULE
  - `createTime`: `Long` 创建时间
  - `operator`: `String` 操作人
  - `operation`: `String` 操作

**返回值**: `List<OptionDTO>`


### OperationLogController
**业务标签**: 系统设置-系统-日志

#### **`GetMapping /operation/log/get/options`** — 系统设置-系统-日志-获取组织/项目级联下拉框选项

**无入参**

**返回值**: `OrganizationProjectOptionsResponse`

#### **`PostMapping /operation/log/list`** — 系统设置-系统-日志-系统操作日志列表查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `SystemOperationLogRequest` | Body |

**返回值**: `Pager<List<OperationLogResponse>>`

#### **`GetMapping /operation/log/user/list`** — 系统设置-系统-日志-系统日志页面，获取用户列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `keyword` | `String` | Query |

**返回值**: `List<User>`


### OrganizationController
**业务标签**: 系统设置-组织-成员

#### **`PostMapping /organization/member/list`** — 系统设置-组织-成员-获取组织成员列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationRequest` | `OrganizationRequest` | Body |

**OrganizationRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `organizationId`: `String` 组织ID

**返回值**: `Pager<List<OrgUserExtend>>`

#### **`PostMapping /organization/add-member`** — 系统设置-组织-成员-添加组织成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationMemberExtendRequest` | `OrganizationMemberExtendRequest` | Body |

**OrganizationMemberExtendRequest 字段明细**:
  > **继承**: `OrganizationMemberRequestByOrg`
  - `userRoleIds`: `List<String>` **[必填]** 用户组ID集合

**返回值**: `void`

#### **`PostMapping /organization/user/invite`** — 系统设置-组织-成员-邀请用户注册

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserInviteRequest` | Body |

**UserInviteRequest 字段明细**:
  - `organizationId`: `String` 组织ID
  - `projectId`: `String` 项目ID

**返回值**: `UserInviteResponse`

#### **`PostMapping /organization/role/update-member`** — 系统设置-组织-成员-添加组织成员至用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationMemberExtendRequest` | `OrganizationMemberExtendRequest` | Body |

**OrganizationMemberExtendRequest 字段明细**:
  > **继承**: `OrganizationMemberRequestByOrg`
  - `userRoleIds`: `List<String>` **[必填]** 用户组ID集合

**返回值**: `void`

#### **`PostMapping /organization/update-member`** — 系统设置-组织-成员-更新用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationMemberExtendRequest` | `OrganizationMemberUpdateRequest` | Body |

**OrganizationMemberUpdateRequest 字段明细**:
  - `organizationId`: `String` **[必填]** 组织ID
  - `memberId`: `String` **[必填]** 成员ID
  - `userRoleIds`: `List<String>` **[必填]** 用户组ID集合
  - `projectIds`: `List<String>` 项目ID集合

**返回值**: `void`

#### **`PostMapping /organization/project/add-member`** — 系统设置-组织-成员-添加组织成员至项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `orgMemberExtendProjectRequest` | `OrgMemberExtendProjectRequest` | Body |

**OrgMemberExtendProjectRequest 字段明细**:
  > **继承**: `OrganizationMemberRequestByOrg`
  - `projectIds`: `List<String>` **[必填]** 项目ID集合

**返回值**: `void`

#### **`GetMapping /organization/remove-member/{organizationId}/{userId}`** — 系统设置-组织-成员-删除组织成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `userId` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /organization/project/list/{organizationId}`** — 系统设置-组织-成员-获取当前组织下的所有项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `` | `(description = "查询关键字，根据项目名查询"` | 参数 |
| `` | `requiredMode = Schema.RequiredMode.REQUIRED) (value = "keyword"` | Query |
| `keyword` | `required = false) String` | 参数 |

**返回值**: `List<OptionDTO>`

#### **`GetMapping /organization/user/role/list/{organizationId}`** — 系统设置-组织-成员-获取当前组织下的所有自定义用户组以及组织级别的用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `List<OptionDTO>`

#### **`GetMapping /organization/not-exist/user/list/{organizationId}`** — 系统设置-组织-成员-获取不在当前组织的所有用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `` | `(description = "查询关键字，根据用户名查询"` | 参数 |
| `` | `requiredMode = Schema.RequiredMode.REQUIRED)(value = "keyword"` | Query |
| `keyword` | `required = false) String` | 参数 |

**返回值**: `List<OptionDisabledDTO>`


### OrganizationCustomFieldController
**业务标签**: 系统设置-组织-自定义字段

#### **`GetMapping /organization/custom/field/list/{organizationId}/{scene}`** — 获取自定义字段列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "组织ID"` | 参数 |
| `organizationId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `FUNCTIONAL` | `(description = "模板的使用场景（` | 参数 |
| `BUG` | `` | 参数 |
| `API` | `` | 参数 |
| `UI` | `` | 参数 |
| `` | `TEST_PLAN）"` | 参数 |
| `scene` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |

**返回值**: `List<CustomFieldDTO>`

#### **`GetMapping /organization/custom/field/get/{id}`** — 获取自定义字段详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `CustomFieldDTO`

#### **`PostMapping /organization/custom/field/add`** — 创建自定义字段

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CustomFieldUpdateRequest` | Body |

**CustomFieldUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 自定义字段ID *约束: @Size(min = 1, max = 50, message = "{custom_field.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 自定义字段名称 *约束: @Size(min = 1, max = 255, message = "{custom_field.name.length_range}", groups = {Created.class, Updated.class});*
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class, groups = {Created.class}); @Size(min = 1, max = 30, message = "{custom_field.scene.length_range}", groups = {Created.class});*
  - `type`: `String` **[必填]** 自定义字段类型 *约束: @EnumValue(enumClass = CustomFieldType.class, groups = {Created.class, Updated.class}); @Size(min = 1, max = 30, message = "{custom_field.type.length_range}", groups = {Created.class, Updated.class});*
  - `remark`: `String` 自定义字段备注 *约束: @Size(max = 1000, message = "{custom_field.remark.length_range}", groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 组织或项目ID *约束: @Size(min = 1, max = 50, message = "{custom_field.scope_id.length_range}", groups = {Created.class});*
  - `enableOptionKey`: `Boolean` 是否需要手动输入选项key
  - `options`: `List<CustomFieldOptionRequest>` 自定义字段选项 *约束: @Valid;*

**返回值**: `CustomField`

#### **`PostMapping /organization/custom/field/update`** — 更新自定义字段

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `CustomFieldUpdateRequest` | Body |

**CustomFieldUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 自定义字段ID *约束: @Size(min = 1, max = 50, message = "{custom_field.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 自定义字段名称 *约束: @Size(min = 1, max = 255, message = "{custom_field.name.length_range}", groups = {Created.class, Updated.class});*
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class, groups = {Created.class}); @Size(min = 1, max = 30, message = "{custom_field.scene.length_range}", groups = {Created.class});*
  - `type`: `String` **[必填]** 自定义字段类型 *约束: @EnumValue(enumClass = CustomFieldType.class, groups = {Created.class, Updated.class}); @Size(min = 1, max = 30, message = "{custom_field.type.length_range}", groups = {Created.class, Updated.class});*
  - `remark`: `String` 自定义字段备注 *约束: @Size(max = 1000, message = "{custom_field.remark.length_range}", groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 组织或项目ID *约束: @Size(min = 1, max = 50, message = "{custom_field.scope_id.length_range}", groups = {Created.class});*
  - `enableOptionKey`: `Boolean` 是否需要手动输入选项key
  - `options`: `List<CustomFieldOptionRequest>` 自定义字段选项 *约束: @Valid;*

**返回值**: `CustomField`

#### **`GetMapping /organization/custom/field/delete/{id}`** — 删除自定义字段

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`


### OrganizationLogController
**业务标签**: 系统设置-组织-日志

#### **`GetMapping /organization/log/get/options/{organizationId}`** — 系统设置-组织-日志-获取项目级联下拉框选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `OrganizationProjectOptionsResponse`

#### **`GetMapping /organization/log/user/list/{organizationId}`** — 系统设置-组织-日志-获取用户列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<User>`

#### **`PostMapping /organization/log/list`** — 系统设置-组织-日志-组织菜单下操作日志列表查询

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrgOperationLogRequest` | Body |

**返回值**: `Pager<List<OperationLogResponse>>`


### OrganizationProjectController
**业务标签**: 系统设置-组织-项目

#### **`PostMapping /organization/project/add`** — 系统设置-组织-项目-创建项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AddProjectRequest` | Body |

**AddProjectRequest 字段明细**:
  > **继承**: `ProjectBaseRequest`
  - `id`: `String` 项目ID *约束: @Size(min = 1, max = 50, message = "{project.id.length_range}");*

**返回值**: `ProjectDTO`

#### **`GetMapping /organization/project/get/{id}`** — 系统设置-组织-项目-根据ID获取项目信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ProjectDTO`

#### **`PostMapping /organization/project/page`** — 系统设置-组织-项目-获取项目列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationProjectRequest` | Body |

**OrganizationProjectRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{project.organization_id.length_range}");*

**返回值**: `Pager<List<ProjectDTO>>`

#### **`PostMapping /organization/project/update`** — 系统设置-组织-项目-编辑

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UpdateProjectRequest` | Body |

**UpdateProjectRequest 字段明细**:
  > **继承**: `ProjectBaseRequest`
  - `id`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project.id.length_range}", groups = {Updated.class});*

**返回值**: `ProjectDTO`

#### **`GetMapping /organization/project/delete/{id}`** — 系统设置-组织-项目-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `int`

#### **`GetMapping /organization/project/revoke/{id}`** — 系统设置-组织-项目-撤销删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `int`

#### **`GetMapping /organization/project/enable/{id}`** — 系统设置-组织-项目-启用

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /organization/project/disable/{id}`** — 系统设置-组织-项目-禁用

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /organization/project/member-list`** — 系统设置-组织-项目-成员列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectMemberRequest` | Body |

**ProjectMemberRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<UserExtendDTO>>`

#### **`PostMapping /organization/project/add-members`** — 系统设置-组织-项目-添加成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectAddMemberRequest` | Body |

**ProjectAddMemberRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID
  - `userRoleIds`: `List<String>` 用户组ID集合

**返回值**: `void`

#### **`GetMapping /organization/project/remove-member/{projectId}/{userId}`** — 系统设置-组织-项目-移除成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `userId` | `String` | 路径 |

**返回值**: `int`

#### **`GetMapping /organization/project/user-admin-list/{organizationId}`** — 系统设置-组织-项目-获取项目管理员下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserExtendDTO>`

#### **`GetMapping /organization/project/user-member-list/{organizationId}/{projectId}`** — 系统设置-组织-项目-获取成员列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `projectId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserExtendDTO>`

#### **`PostMapping /organization/project/pool-options`** — 系统设置-组织-项目-获取资源池下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectPoolRequest` | Body |

**ProjectPoolRequest 字段明细**:
  - `organizationId`: `String` 组织id *约束: @Size(min = 0, max = 50, message = "project.organization_id.length_range");*
  - `modulesIds`: `List<String>` **[必填]** 项目开启的模块id集合

**返回值**: `List<OptionDTO>`

#### **`PostMapping /organization/project/rename`** — 系统设置-组织-项目-修改项目名称

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UpdateProjectNameRequest` | Body |

**UpdateProjectNameRequest 字段明细**:
  - `id`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project.id.length_range}", groups = {Updated.class});*
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{project.organization_id.length_range}", groups = {Created.class, Updated.class});*
  - `name`: `String` **[必填]** 项目名称 *约束: @Size(min = 1, max = 255, message = "{project.name.length_range}", groups = {Created.class, Updated.class});*

**返回值**: `void`

#### **`PostMapping /organization/project/user-list`** — 系统设置-组织-项目-分页获取成员列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectUserRequest` | Body |

**ProjectUserRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `organizationId`: `String` **[必填]** 组织ID
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<UserExtendDTO>>`


### OrganizationStatusFlowSettingController
**业务标签**: 系统设置-组织-状态流设置

#### **`GetMapping /organization/status/flow/setting/get/{organizationId}/{scene}`** — 系统设置-组织-状态流设置-获取状态流设置

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "组织ID"` | 参数 |
| `organizationId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `FUNCTIONAL` | `(description = "模板的使用场景（` | 参数 |
| `BUG` | `` | 参数 |
| `API` | `` | 参数 |
| `UI` | `` | 参数 |
| `` | `TEST_PLAN）"` | 参数 |
| `scene` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |

**返回值**: `List<StatusItemDTO>`

#### **`PostMapping /organization/status/flow/setting/status/definition/update`** — 系统设置-组织-状态流设置-设置状态定义，即起始状态，结束状态

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `StatusDefinitionUpdateRequest` | Body |

**StatusDefinitionUpdateRequest 字段明细**:
  - `statusId`: `String` **[必填]** 状态ID *约束: @Size(min = 1, max = 50, message = "{status_definition.status_id.length_range}");*
  - `definitionId`: `String` **[必填]** 状态定义ID(在代码中定义) *约束: @Size(min = 1, max = 100, message = "{status_definition.definition_id.length_range}");*
  - `enable`: `Boolean` **[必填]** 启用或者禁用

**返回值**: `void`

#### **`PostMapping /organization/status/flow/setting/status/add`** — 系统设置-组织-状态流设置-添加状态项

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `StatusItemAddRequest` | Body |

**StatusItemAddRequest 字段明细**:
  - `scopeId`: `String` **[必填]** 组织ID或项目ID *约束: @Size(min = 1, max = 50);*
  - `name`: `String` **[必填]** 状态名称 *约束: @Size(min = 1, max = 255, message = "{status_item.name.length_range}");*
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class);*
  - `remark`: `String` 状态说明 *约束: @Size(max = 1000);*
  - `allTransferTo`: `Boolean` 所有状态都可以流转到该状态

**返回值**: `StatusItem`

#### **`PostMapping /organization/status/flow/setting/status/update`** — 系统设置-组织-状态流设置-修改状态项

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `StatusItemUpdateRequest` | Body |

**StatusItemUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 状态ID *约束: @Size(min = 1, max = 50, message = "{status_item.id.length_range}");*
  - `name`: `String` 状态名称 *约束: @Size(min = 1, max = 255, message = "{status_item.name.length_range}");*
  - `remark`: `String` 状态说明 *约束: @Size(max = 1000);*

**返回值**: `StatusItem`

#### **`PostMapping /organization/status/flow/setting/status/sort/{organizationId}/{scene}`** — 系统设置-组织-状态流设置-状态项排序

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `` | 路径 |
| `scene` | `String` | 路径 |
| `statusIds` | `<String>` | Body |

**返回值**: `void`

#### **`GetMapping /organization/status/flow/setting/status/delete/{id}`** — 系统设置-组织-状态流设置-删除状态项

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /organization/status/flow/setting/status/flow/update`** — 系统设置-组织-状态流设置-设置状态流转

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `StatusFlowUpdateRequest` | Body |

**StatusFlowUpdateRequest 字段明细**:
  - `fromId`: `String` **[必填]** 起始状态ID *约束: @Size(min = 1, max = 50, message = "{status_flow.from_id.length_range}");*
  - `toId`: `String` **[必填]** 目的状态ID *约束: @Size(min = 1, max = 50, message = "{status_flow.to_id.length_range}");*
  - `enable`: `Boolean` **[必填]** 启用或者禁用

**返回值**: `void`


### OrganizationTaskHubController
**业务标签**: 组织任务中心

#### **`PostMapping /organization/task-center/exec-task/page`** — 组织-任务中心-执行任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BasePageRequest` | Body |

**BasePageRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `current`: `int` 当前页码 *约束: @Min(value = 1, message = "当前页码必须大于0");*
  - `pageSize`: `int` 每页显示条数 *约束: @Min(value = 5, message = "每页显示条数必须不小于5"); @Max(value = 500, message = "每页显示条数不能大于500");*

**返回值**: `Pager<List<TaskHubDTO>>`

#### **`PostMapping /organization/task-center/schedule/page`** — 组织-任务中心-后台执行任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BasePageRequest` | Body |

**BasePageRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `current`: `int` 当前页码 *约束: @Min(value = 1, message = "当前页码必须大于0");*
  - `pageSize`: `int` 每页显示条数 *约束: @Min(value = 5, message = "每页显示条数必须不小于5"); @Max(value = 500, message = "每页显示条数不能大于500");*

**返回值**: `Pager<List<TaskHubScheduleDTO>>`

#### **`PostMapping /organization/task-center/exec-task/item/page`** — 组织-任务中心-用例执行任务详情列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskHubItemRequest` | Body |

**TaskHubItemRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `taskId`: `String` 任务id
  - `resourcePoolIds`: `List<String>` 资源池id
  - `resourcePoolNodes`: `List<String>` 资源池节点

**返回值**: `Pager<List<TaskHubItemDTO>>`

#### **`PostMapping /organization/task-center/exec-task/statistics`** — 组织-任务中心-获取任务统计{通过率}接口

| 参数 | 类型 | 来源 |
|------|------|------|
| `ids` | `List<String>` | Body |

**返回值**: `List<TaskStatisticsResponse>`

#### **`GetMapping /organization/task-center/resource-pool/options`** — 组织-任务中心-获取资源池下拉选项

**无入参**

**返回值**: `List<ResourcePoolOptionsDTO>`

#### **`GetMapping /organization/task-center/exec-task/stop/{id}`** — 组织-任务中心-用例执行任务-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /organization/task-center/exec-task/rerun/{id}`** — 组织-任务中心-用例执行任务-重跑任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /organization/task-center/exec-task/batch-stop`** — 组织-任务中心-用例执行任务-批量停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /organization/task-center/exec-task/item/order`** — 系统-任务中心-用例执行任务-获取任务项的排队信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskIdItemIds` | `List<String>` | Body |

**返回值**: `Map<String, Integer>`

#### **`GetMapping /organization/task-center/exec-task/delete/{id}`** — 组织-任务中心-用例执行任务-删除任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /organization/task-center/exec-task/batch-delete`** — 组织-任务中心-用例执行任务-批量删除任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`GetMapping /organization/task-center/exec-task/item/stop/{id}`** — 组织-任务中心-用例任务详情-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /organization/task-center/exec-task/item/batch-stop`** — 组织-任务中心-用例任务详情-批量停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskHubItemBatchRequest` | Body |

**TaskHubItemBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `taskId`: `String` 任务id
  - `resourcePoolIds`: `List<String>` 资源池id
  - `resourcePoolNodes`: `List<String>` 资源池节点

**返回值**: `void`

#### **`GetMapping /organization/task-center/schedule/delete/{id}`** — 组织-任务中心-系统后台任务-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /organization/task-center/schedule/switch/{id}`** — 组织-任务中心-后台任务开启关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /organization/task-center/schedule/batch-enable`** — 组织-任务中心-后台任务-批量开启

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /organization/task-center/schedule/batch-disable`** — 组织-任务中心-后台任务-批量关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /organization/task-center/schedule/update-cron`** — 组织-任务中心-后台任务更新cron表达式

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ScheduleRequest` | Body |

**ScheduleRequest 字段明细**:
  - `id`: `String` 列表id
  - `cron`: `String` cron表达式

**返回值**: `void`

#### **`PostMapping /organization/task-center/exec-task/batch/page`** — 组织-任务中心-用例执行任务-批量任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BatchExecTaskPageRequest` | Body |

**BatchExecTaskPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `taskId`: `String` 任务ID
  - `batchType`: `String`

**返回值**: `Pager<List<BatchExecTaskReportDTO>>`

#### **`GetMapping /organization/task-center/project/options`** — 系统-任务中心-获取组织下全部项目下拉选项

**无入参**

**返回值**: `List<OrganizationProjectOptionsDTO>`


### OrganizationTemplateController
**业务标签**: 系统设置-组织-模版

#### **`GetMapping /organization/template/list/{organizationId}/{scene}`** — 获取模版列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "组织ID"` | 参数 |
| `organizationId` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |
| `FUNCTIONAL` | `(description = "模板的使用场景（` | 参数 |
| `BUG` | `` | 参数 |
| `API` | `` | 参数 |
| `UI` | `` | 参数 |
| `` | `TEST_PLAN）"` | 参数 |
| `scene` | `requiredMode = Schema.RequiredMode.REQUIRED) String` | 路径 |

**返回值**: `List<Template>`

#### **`GetMapping /organization/template/get/{id}`** — 获取模版详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `TemplateDTO`

#### **`PostMapping /organization/template/add`** — 创建模版

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TemplateUpdateRequest` | Body |

**TemplateUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** ID *约束: @Size(min = 1, max = 50, message = "{template.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 名称 *约束: @Size(min = 1, max = 255, message = "{template.name.length_range}", groups = {Created.class, Updated.class});*
  - `remark`: `String` 备注 *约束: @Size(max = 1000, groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 组织或项目ID *约束: @Size(min = 1, max = 50, message = "{template.scope_id.length_range}", groups = {Created.class, Updated.class});*
  - `enableThirdPart`: `Boolean` 是否开启api字段名配置
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class, groups = {Created.class}); @Size(min = 1, max = 30, message = "{template.scene.length_range}", groups = {Created.class});*
  - `customFields`: `List<TemplateCustomFieldRequest>` 自定义字段Id列表 *约束: @Valid;*
  - `systemFields`: `List<TemplateSystemCustomFieldRequest>` 系统字段列表 *约束: @Valid;*
  - `uploadImgFileIds`: `List<String>` 模板中新上传的文件ID列表

**返回值**: `Template`

#### **`PostMapping /organization/template/update`** — 更新模版

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TemplateUpdateRequest` | Body |

**TemplateUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** ID *约束: @Size(min = 1, max = 50, message = "{template.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 名称 *约束: @Size(min = 1, max = 255, message = "{template.name.length_range}", groups = {Created.class, Updated.class});*
  - `remark`: `String` 备注 *约束: @Size(max = 1000, groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 组织或项目ID *约束: @Size(min = 1, max = 50, message = "{template.scope_id.length_range}", groups = {Created.class, Updated.class});*
  - `enableThirdPart`: `Boolean` 是否开启api字段名配置
  - `scene`: `String` **[必填]** 使用场景 *约束: @EnumValue(enumClass = TemplateScene.class, groups = {Created.class}); @Size(min = 1, max = 30, message = "{template.scene.length_range}", groups = {Created.class});*
  - `customFields`: `List<TemplateCustomFieldRequest>` 自定义字段Id列表 *约束: @Valid;*
  - `systemFields`: `List<TemplateSystemCustomFieldRequest>` 系统字段列表 *约束: @Valid;*
  - `uploadImgFileIds`: `List<String>` 模板中新上传的文件ID列表

**返回值**: `Template`

#### **`GetMapping /organization/template/delete/{id}`** — 删除模版

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /organization/template/disable/{organizationId}/{scene}`** — 关闭组织模板，开启项目模板

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `scene` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /organization/template/enable/config/{organizationId}`** — 是否启用组织模版

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `Map<String, Boolean>`

#### **`PostMapping /organization/template/upload/temp/img`** — 上传富文本图片，并返回文件ID

| 参数 | 类型 | 来源 |
|------|------|------|
| `file` | `MultipartFile` | Query |

**返回值**: `String`

#### **`GetMapping /organization/template/img/preview/{organizationId}/{fileId}/{compressed}`** — 富文本图片-预览

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `fileId` | `String` | 路径 |
| `` | `(description = "查看压缩图片"` | 参数 |
| `compressed` | `requiredMode = Schema.RequiredMode.REQUIRED) boolean` | 路径 |

**返回值**: `ResponseEntity<byte[]>`


### OrganizationUserRoleController
**业务标签**: 系统设置-组织-用户组

#### **`GetMapping /user/role/organization/list/{organizationId}`** — 系统设置-组织-用户组-获取用户组列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `List<UserRole>`

#### **`PostMapping /user/role/organization/add`** — 系统设置-组织-用户组-添加用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationUserRoleEditRequest` | Body |

**OrganizationUserRoleEditRequest 字段明细**:
  - `id`: `String` **[必填]** 组ID *约束: @Size(min = 1, max = 50, message = "{user_role.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 组名称 *约束: @Size(min = 1, max = 255, message = "{user_role.name.length_range}", groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 应用范围 *约束: @Size(min = 1, max = 50, message = "{user_role.scope_id.length_range}", groups = {Created.class, Updated.class});*

**返回值**: `UserRole`

#### **`PostMapping /user/role/organization/update`** — 系统设置-组织-用户组-修改用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationUserRoleEditRequest` | Body |

**OrganizationUserRoleEditRequest 字段明细**:
  - `id`: `String` **[必填]** 组ID *约束: @Size(min = 1, max = 50, message = "{user_role.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 组名称 *约束: @Size(min = 1, max = 255, message = "{user_role.name.length_range}", groups = {Created.class, Updated.class});*
  - `scopeId`: `String` **[必填]** 应用范围 *约束: @Size(min = 1, max = 50, message = "{user_role.scope_id.length_range}", groups = {Created.class, Updated.class});*

**返回值**: `UserRole`

#### **`GetMapping /user/role/organization/delete/{id}`** — 系统设置-组织-用户组-删除用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /user/role/organization/permission/setting/{id}`** — 系统设置-组织-用户组-获取用户组对应的权限配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `List<PermissionDefinitionItem>`

#### **`PostMapping /user/role/organization/permission/update`** — 系统设置-组织-用户组-修改用户组对应的权限配置

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PermissionSettingUpdateRequest` | Body |

**PermissionSettingUpdateRequest 字段明细**:
  - `userRoleId`: `String` **[必填]** 用户组ID
  - `permissions`: `List<PermissionUpdateRequest>` **[必填]** 菜单下的权限列表 *约束: @Valid;*
  - `id`: `String` **[必填]** 权限ID

**返回值**: `void`

#### **`GetMapping /user/role/organization/get-member/option/{organizationId}/{roleId}`** — 系统设置-组织-用户组-获取成员下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `roleId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserExtendDTO>`

#### **`PostMapping /user/role/organization/list-member`** — 系统设置-组织-用户组-获取成员列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationUserRoleMemberRequest` | Body |

**OrganizationUserRoleMemberRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `userRoleId`: `String` **[必填]** 组ID *约束: @Size(min = 1, max = 50, message = "{user_role.id.length_range}");*
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{organization.id.length_range}");*

**返回值**: `Pager<List<User>>`

#### **`PostMapping /user/role/organization/add-member`** — 系统设置-组织-用户组-添加用户组成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationUserRoleMemberEditRequest` | Body |

**OrganizationUserRoleMemberEditRequest 字段明细**:
  - `userRoleId`: `String` **[必填]** 组ID *约束: @Size(min = 1, max = 50, message = "{user_role.id.length_range}");*
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{organization.id.length_range}");*
  - `userIds`: `List<String>` **[必填]** 成员ID集合

**返回值**: `void`

#### **`PostMapping /user/role/organization/remove-member`** — 系统设置-组织-用户组-删除用户组成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationUserRoleMemberEditRequest` | Body |

**OrganizationUserRoleMemberEditRequest 字段明细**:
  - `userRoleId`: `String` **[必填]** 组ID *约束: @Size(min = 1, max = 50, message = "{user_role.id.length_range}");*
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{organization.id.length_range}");*
  - `userIds`: `List<String>` **[必填]** 成员ID集合

**返回值**: `void`


### PersonalCenterController
**业务标签**: 个人中心

#### **`GetMapping /personal/get/{id}`** — 个人中心-获取信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `PersonalDTO`

#### **`PostMapping /personal/update-info`** — 个人中心-修改信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PersonalUpdateRequest` | Body |

**PersonalUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** 用户ID
  - `avatar`: `String` 头像
  - `username`: `String` **[必填]** 用户名
  - `phone`: `String` 手机号
  - `email`: `String` **[必填]** 邮箱 *约束: @Size(min = 1, max = 64, message = "{user.email.length_range}"); @Email(message = "{user.email.invalid}");*

**返回值**: `boolean`

#### **`PostMapping /personal/update-locale`** — 个人中心-修改信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PersonalLocaleRequest` | Body |

**PersonalLocaleRequest 字段明细**:
  - `language`: `String` **[必填]** 国际化

**返回值**: `void`

#### **`PostMapping /personal/update-password`** — 个人中心-修改密码

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PersonalUpdatePasswordRequest` | Body |

**PersonalUpdatePasswordRequest 字段明细**:
  - `id`: `String` **[必填]** 用户ID
  - `oldPassword`: `String` **[必填]** 旧密码
  - `newPassword`: `String` **[必填]** 新密码

**返回值**: `String`

#### **`PostMapping /personal/model/edit-source`** — 系统设置-编辑模型设置

| 参数 | 类型 | 来源 |
|------|------|------|
| `aiModelSourceDTO` | `AiModelSourceDTO` | Body |

**AiModelSourceDTO 字段明细**:
  - `id`: `String`
  - `name`: `String` **[必填]** 模型名称 *约束: @Size(min = 1, max = 255, message = "{model_source.name.length_range}", groups = {Created.class, Updated.class});*
  - `type`: `String` **[必填]** 模型类型（大语言/视觉/音频） *约束: @Size(min = 1, max = 255, message = "{model_source.type.length_range}", groups = {Created.class, Updated.class});*
  - `providerName`: `String` **[必填]** 模型供应商 *约束: @Size(min = 1, max = 255, message = "{model_source.provider.length_range}", groups = {Created.class, Updated.class});*
  - `permissionType`: `String` **[必填]** 模型类型（公有/私有） *约束: @Size(min = 1, max = 255, message = "{model_source.permission_type.length_range}", groups = {Created.class, Updated.class});*
  - `status`: `Boolean` **[必填]** 模型链接状态
  - `owner`: `String` 模型拥有者(system/用户id)
  - `ownerType`: `String` **[必填]** 模型拥有者类型（个人/企业） *约束: @Size(min = 1, max = 255, message = "{model_source.owner_type.length_range}", groups = {Created.class, Updated.class});*
  - `baseName`: `String` **[必填]** 基础名称（deepseek-0.5)
  - `appKey`: `String` **[必填]** 模型key
  - `apiUrl`: `String` **[必填]** 模型url
  - `createUserName`: `String` 创建人名称
  - `createTime`: `Long` 创建时间
  - `createUser`: `String` 创建人(操作人）
  - `advSettingDTOList`: `List<AdvSettingDTO>` 模型参数配置

**返回值**: `void`

#### **`PostMapping /personal/model/source/list`** — 系统设置-查看模型集合

| 参数 | 类型 | 来源 |
|------|------|------|
| `aiModelSourceRequest` | `AiModelSourceRequest` | Body |

**AiModelSourceRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `owner`: `String` 组织id/个人id
  - `providerName`: `String` 供应商名称

**返回值**: `Pager<List<AiModelSourceDTO>>`

#### **`GetMapping /personal/model/get/{id}`** — 获取模型信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `AiModelSourceDTO`

#### **`GetMapping /personal/model/delete/{id}`** — 删除模型

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`


### PluginController
**业务标签**: 系统设置-系统-插件管理

#### **`GetMapping /plugin/list`** — 系统设置-系统-插件管理-获取插件列表

**无入参**

**返回值**: `List<PluginDTO>`

#### **`PostMapping /plugin/add`** — 系统设置-系统-插件管理-创建插件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PluginUpdateRequest` | Form |
| `file` | `MultipartFile` | Form |

**返回值**: `Plugin`

#### **`PostMapping /plugin/update`** — 系统设置-系统-插件管理-更新插件

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PluginUpdateRequest` | Body |

**PluginUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** ID *约束: @Size(min = 1, max = 50, message = "{plugin.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 插件名称 *约束: @Size(min = 1, max = 255, message = "{plugin.name.length_range}", groups = {Created.class, Updated.class});*
  - `enable`: `Boolean` 是否启用插件, 默认启用
  - `global`: `Boolean` 是否是全局插件, 默认全局
  - `description`: `String` 插件描述 *约束: @Size(max = 1000, message = "{plugin.scenario.length_range}", groups = {Created.class, Updated.class});*
  - `createUser`: `String`
  - `organizationIds`: `List<String>` 关联的组织ID

**返回值**: `Plugin`

#### **`GetMapping /plugin/delete/{id}`** — 系统设置-系统-插件管理-删除插件

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /plugin/script/get/{pluginId}/{scriptId}`** — 系统设置-系统-插件管理-获取插件对应表单的脚本内容

| 参数 | 类型 | 来源 |
|------|------|------|
| `pluginId` | `String` | 路径 |
| `scriptId` | `String` | 路径 |

**返回值**: `String`

#### **`GetMapping /plugin/image/{pluginId}`** — 系统设置-系统-插件管理-获取插件的图片资源

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description =  "插件ID"` | 参数 |
| `pluginId` | `requiredMode = Schema.RequiredMode.REQUIRED)String` | 路径 |
| `` | `(description =  "图片路径"` | 参数 |
| `imagePath` | `requiredMode = Schema.RequiredMode.REQUIRED)String` | Query |
| `response` | `HttpServletResponse` | 参数 |

**返回值**: `void`

#### **`PostMapping /plugin/options`** — 获取插件下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `PlatformOptionRequest` | Body |

**PlatformOptionRequest 字段明细**:
  - `pluginId`: `String` 插件id
  - `organizationId`: `String` 组织id
  - `optionMethod`: `String` 方法
  - `projectConfig`: `String` 输入参数

**返回值**: `List<SelectOption>`


### ServiceIntegrationController
**业务标签**: 系统设置-组织-服务集成

#### **`GetMapping /service/integration/list/{organizationId}`** — 系统设置-组织-服务集成-获取服务集成列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |

**返回值**: `List<ServiceIntegrationDTO>`

#### **`PostMapping /service/integration/add`** — 系统设置-组织-服务集成-创建服务集成

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ServiceIntegrationUpdateRequest` | Body |

**ServiceIntegrationUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** ID *约束: @Size(min = 1, max = 50, message = "{service_integration.id.length_range}", groups = {Updated.class});*
  - `pluginId`: `String` **[必填]** 插件的ID *约束: @Size(min = 1, max = 50, message = "{service_integration.plugin_id.length_range}", groups = {Created.class, Updated.class});*
  - `enable`: `Boolean` 是否启用
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{service_integration.organization_id.length_range}", groups = {Created.class, Updated.class});*
  - `configuration`: `Map<String, Object>` **[必填]** 配置的表单键值对

**返回值**: `ServiceIntegration`

#### **`PostMapping /service/integration/update`** — 系统设置-组织-服务集成-更新服务集成

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ServiceIntegrationUpdateRequest` | Body |

**ServiceIntegrationUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** ID *约束: @Size(min = 1, max = 50, message = "{service_integration.id.length_range}", groups = {Updated.class});*
  - `pluginId`: `String` **[必填]** 插件的ID *约束: @Size(min = 1, max = 50, message = "{service_integration.plugin_id.length_range}", groups = {Created.class, Updated.class});*
  - `enable`: `Boolean` 是否启用
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{service_integration.organization_id.length_range}", groups = {Created.class, Updated.class});*
  - `configuration`: `Map<String, Object>` **[必填]** 配置的表单键值对

**返回值**: `ServiceIntegration`

#### **`GetMapping /service/integration/delete/{id}`** — 系统设置-组织-服务集成-删除服务集成

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /service/integration/validate/{pluginId}/{orgId}`** — 系统设置-组织-服务集成-校验服务集成信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `pluginId` | `String` | 路径 |
| `orgId` | `String` | 路径 |
| `` | `(description = "配置的表单键值对"` | Body |
| `serviceIntegrationInfo` | `requiredMode = Schema.RequiredMode.REQUIRED)HashMap<String, String>` | 参数 |

**返回值**: `void`

#### **`GetMapping /service/integration/validate/{id}`** — 系统设置-组织-服务集成-校验服务集成信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /service/integration/script/{pluginId}`** — 系统设置-组织-服务集成-获取前端配置脚本

| 参数 | 类型 | 来源 |
|------|------|------|
| `pluginId` | `String` | 路径 |

**返回值**: `Object`


### SystemAIConfigController
**业务标签**: 系统设置-AI-模型配置

#### **`PostMapping /ai/config/edit-source`** — 系统设置-编辑模型设置

| 参数 | 类型 | 来源 |
|------|------|------|
| `aiModelSourceDTO` | `AiModelSourceDTO` | Body |

**AiModelSourceDTO 字段明细**:
  - `id`: `String`
  - `name`: `String` **[必填]** 模型名称 *约束: @Size(min = 1, max = 255, message = "{model_source.name.length_range}", groups = {Created.class, Updated.class});*
  - `type`: `String` **[必填]** 模型类型（大语言/视觉/音频） *约束: @Size(min = 1, max = 255, message = "{model_source.type.length_range}", groups = {Created.class, Updated.class});*
  - `providerName`: `String` **[必填]** 模型供应商 *约束: @Size(min = 1, max = 255, message = "{model_source.provider.length_range}", groups = {Created.class, Updated.class});*
  - `permissionType`: `String` **[必填]** 模型类型（公有/私有） *约束: @Size(min = 1, max = 255, message = "{model_source.permission_type.length_range}", groups = {Created.class, Updated.class});*
  - `status`: `Boolean` **[必填]** 模型链接状态
  - `owner`: `String` 模型拥有者(system/用户id)
  - `ownerType`: `String` **[必填]** 模型拥有者类型（个人/企业） *约束: @Size(min = 1, max = 255, message = "{model_source.owner_type.length_range}", groups = {Created.class, Updated.class});*
  - `baseName`: `String` **[必填]** 基础名称（deepseek-0.5)
  - `appKey`: `String` **[必填]** 模型key
  - `apiUrl`: `String` **[必填]** 模型url
  - `createUserName`: `String` 创建人名称
  - `createTime`: `Long` 创建时间
  - `createUser`: `String` 创建人(操作人）
  - `advSettingDTOList`: `List<AdvSettingDTO>` 模型参数配置

**返回值**: `void`

#### **`GetMapping /ai/config/delete/{id}`** — 删除模型

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /ai/config/source/list`** — 系统设置-查看模型集合

| 参数 | 类型 | 来源 |
|------|------|------|
| `aiModelSourceRequest` | `AiModelSourceRequest` | Body |

**AiModelSourceRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `owner`: `String` 组织id/个人id
  - `providerName`: `String` 供应商名称

**返回值**: `Pager<List<AiModelSourceDTO>>`

#### **`GetMapping /ai/config/get/{id}`** — 获取模型信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `AiModelSourceDTO`

#### **`GetMapping /ai/config/source/name/list`** — 系统设置-查看模型名称集合

**无入参**

**返回值**: `List<OptionDTO>`


### SystemOrganizationController
**业务标签**: 系统设置-系统-组织与项目-组织

#### **`PostMapping /system/organization/list`** — 系统设置-系统-组织与项目-组织-获取组织列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationRequest` | Body |

**OrganizationRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `organizationId`: `String` 组织ID

**返回值**: `Pager<List<OrganizationDTO>>`

#### **`PostMapping /system/organization/update`** — 系统设置-系统-组织与项目-组织-修改组织

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationEditRequest` | `OrganizationEditRequest` | Body |

**OrganizationEditRequest 字段明细**:
  - `id`: `String` 组织ID
  - `name`: `String` **[必填]** 组织名称 *约束: @Size(min = 1, max = 255, message = "{organization.name.length_range}", groups = {Created.class, Updated.class});*
  - `description`: `String` 描述 *约束: @Size(max = 1000, groups = {Created.class, Updated.class});*
  - `userIds`: `List<String>` **[必填]** 成员ID集合

**返回值**: `void`

#### **`PostMapping /system/organization/rename`** — 系统设置-系统-组织与项目-组织-修改组织名称

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationEditRequest` | `OrganizationNameEditRequest` | Body |

**OrganizationNameEditRequest 字段明细**:
  - `id`: `String` 组织ID
  - `name`: `String` **[必填]** 组织名称 *约束: @Size(min = 1, max = 255, message = "{organization.name.length_range}", groups = {Created.class, Updated.class});*

**返回值**: `void`

#### **`GetMapping /system/organization/delete/{id}`** — 系统设置-系统-组织与项目-组织-删除组织

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /system/organization/recover/{id}`** — 系统设置-系统-组织与项目-组织-恢复组织

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /system/organization/enable/{id}`** — 系统设置-系统-组织与项目-组织-启用组织

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /system/organization/disable/{id}`** — 系统设置-系统-组织与项目-组织-结束组织

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /system/organization/option/all`** — 系统设置-系统-组织与项目-组织-获取系统所有组织下拉选项

**无入参**

**返回值**: `List<OptionDTO>`

#### **`PostMapping /system/organization/list-member`** — 系统设置-系统-组织与项目-组织-获取组织成员列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationRequest` | Body |

**OrganizationRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `organizationId`: `String` 组织ID

**返回值**: `Pager<List<UserExtendDTO>>`

#### **`PostMapping /system/organization/add-member`** — 系统设置-系统-组织与项目-组织-添加组织成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationMemberRequest` | Body |

**OrganizationMemberRequest 字段明细**:
  - `organizationId`: `String` **[必填]** 组织ID
  - `userIds`: `List<String>` **[必填]** 成员ID集合
  - `userRoleIds`: `List<String>` 用户组ID集合

**返回值**: `void`

#### **`GetMapping /system/organization/remove-member/{organizationId}/{userId}`** — 系统设置-系统-组织与项目-组织-删除组织成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | 路径 |
| `userId` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /system/organization/default`** — 系统设置-系统-组织与项目-组织-获取系统默认组织

**无入参**

**返回值**: `OrganizationDTO`

#### **`PostMapping /system/organization/list-project`** — 系统设置-系统-组织与项目-组织-获取组织下的项目列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `OrganizationProjectRequest` | Body |

**OrganizationProjectRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{project.organization_id.length_range}");*

**返回值**: `Pager<List<ProjectDTO>>`

#### **`GetMapping /system/organization/total`** — 系统设置-系统-组织与项目-组织-获取组织和项目总数

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationId` | `String` | Query |

**返回值**: `Map<String, Long>`

#### **`GetMapping /system/organization/get-option/{sourceId}`** — 系统设置-系统-组织与项目-获取成员下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `sourceId` | `String` | 路径 |
| `keyword` | `String` | Query |

**返回值**: `List<UserExtendDTO>`

#### **`PostMapping /system/organization/member-list`** — 系统设置-系统-组织与项目-获取添加成员列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `MemberRequest` | Body |

**MemberRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `sourceId`: `String` 组织ID或项目ID

**返回值**: `Pager<List<UserExtendDTO>>`

#### **`PostMapping /system/organization/update-member`** — 系统设置-系统-组织与项目-组织-成员-更新成员用户组

| 参数 | 类型 | 来源 |
|------|------|------|
| `organizationMemberExtendRequest` | `OrganizationMemberUpdateRequest` | Body |

**OrganizationMemberUpdateRequest 字段明细**:
  - `organizationId`: `String` **[必填]** 组织ID
  - `memberId`: `String` **[必填]** 成员ID
  - `userRoleIds`: `List<String>` **[必填]** 用户组ID集合
  - `projectIds`: `List<String>` 项目ID集合

**返回值**: `void`


### SystemParameterController
**业务标签**: 系统设置-系统-系统参数-基础设置

#### **`PostMapping /system/parameter/save/base-info`** — 系统设置-系统-系统参数-基础设置-基本信息-保存

| 参数 | 类型 | 来源 |
|------|------|------|
| `systemParameter` | `List<SystemParameter>` | Body |

**返回值**: `void`

#### **`GetMapping /system/parameter/get/base-info`** — 系统设置-系统-系统参数-基本设置-基本信息-获取

**无入参**

**返回值**: `BaseSystemConfigDTO`

#### **`GetMapping /system/parameter/get/email-info`** — 系统设置-系统-系统参数-基本设置-邮件设置-获取邮件信息

**无入参**

**返回值**: `EMailInfoDto`

#### **`PostMapping /system/parameter/edit/email-info`** — 系统设置-系统-系统参数-基本设置-邮件设置-保存邮件信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `systemParameter` | `List<SystemParameter>` | Body |

**返回值**: `void`

#### **`PostMapping /system/parameter/test/email`** — 系统设置-系统-系统参数-基本设置-邮件设置-测试连接

| 参数 | 类型 | 来源 |
|------|------|------|
| `hashMap` | `HashMap<String, String>` | Body |

**返回值**: `void`

#### **`GetMapping /system/parameter/save/base-url`** — 系统设置-系统-系统参数-默认站点替换接口

| 参数 | 类型 | 来源 |
|------|------|------|
| `baseUrl` | `String` | Query |

**返回值**: `void`

#### **`PostMapping /system/parameter/edit/clean-config`** — 系统设置-系统-系统参数-内存清理-保存

| 参数 | 类型 | 来源 |
|------|------|------|
| `systemParameter` | `List<SystemParameter>` | Body |

**返回值**: `void`

#### **`GetMapping /system/parameter/get/clean-config`** — 系统设置-系统-系统参数-基本设置-内存清理-获取

**无入参**

**返回值**: `BaseCleanConfigDTO`

#### **`GetMapping /system/parameter/get/api-concurrent-config`** — 系统设置-系统-系统参数-单接口任务并发数-获取

**无入参**

**返回值**: `String`

#### **`PostMapping /system/parameter/edit/upload-config`** — 系统设置-系统-系统参数-基本设置-文件限制-保存

| 参数 | 类型 | 来源 |
|------|------|------|
| `systemParameter` | `List<SystemParameter>` | Body |

**返回值**: `void`


### SystemProjectController
**业务标签**: 系统设置-系统-组织与项目-项目

#### **`PostMapping /system/project/add`** — 系统设置-系统-组织与项目-项目-创建项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `AddProjectRequest` | Body |

**AddProjectRequest 字段明细**:
  > **继承**: `ProjectBaseRequest`
  - `id`: `String` 项目ID *约束: @Size(min = 1, max = 50, message = "{project.id.length_range}");*

**返回值**: `ProjectDTO`

#### **`GetMapping /system/project/get/{id}`** — 系统设置-系统-组织与项目-项目-根据ID获取项目信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `ProjectDTO`

#### **`PostMapping /system/project/page`** — 系统设置-系统-组织与项目-项目-获取项目列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectRequest` | Body |

**ProjectRequest 字段明细**:
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{project.organization_id.length_range}", groups = {Created.class, Updated.class});*
  - `name`: `String` **[必填]** 项目名称 *约束: @Size(min = 1, max = 255, message = "{project.name.length_range}", groups = {Created.class, Updated.class});*
  - `description`: `String` 项目描述 *约束: @Size(min = 0, max = 1000, message = "{project.description.length_range}", groups = {Created.class, Updated.class});*
  - `enable`: `Boolean` 是否启用
  - `id`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project.id.length_range}", groups = {Updated.class});*

**返回值**: `Pager<List<ProjectDTO>>`

#### **`PostMapping /system/project/update`** — 系统设置-系统-组织与项目-项目-编辑

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UpdateProjectRequest` | Body |

**UpdateProjectRequest 字段明细**:
  > **继承**: `ProjectBaseRequest`
  - `id`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project.id.length_range}", groups = {Updated.class});*

**返回值**: `ProjectDTO`

#### **`GetMapping /system/project/delete/{id}`** — 系统设置-系统-组织与项目-项目-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `int`

#### **`GetMapping /system/project/revoke/{id}`** — 系统设置-系统-组织与项目-项目-撤销删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `int`

#### **`GetMapping /system/project/enable/{id}`** — 系统设置-系统-组织与项目-项目-启用

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /system/project/disable/{id}`** — 系统设置-系统-组织与项目-项目-禁用

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /system/project/member-list`** — 系统设置-系统-组织与项目-项目-成员列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectMemberRequest` | Body |

**ProjectMemberRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `projectId`: `String` **[必填]** 项目ID

**返回值**: `Pager<List<UserExtendDTO>>`

#### **`PostMapping /system/project/add-member`** — 系统设置-系统-组织与项目-项目-添加成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectAddMemberRequest` | Body |

**ProjectAddMemberRequest 字段明细**:
  - `projectId`: `String` **[必填]** 项目ID
  - `userRoleIds`: `List<String>` 用户组ID集合

**返回值**: `void`

#### **`GetMapping /system/project/remove-member/{projectId}/{userId}`** — 系统设置-系统-组织与项目-项目-移除成员

| 参数 | 类型 | 来源 |
|------|------|------|
| `projectId` | `String` | 路径 |
| `userId` | `String` | 路径 |

**返回值**: `int`

#### **`GetMapping /system/project/user-list`** — 系统设置-系统-组织与项目-项目-系统-组织及项目, 获取管理员下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `keyword` | `String` | Query |

**返回值**: `List<User>`

#### **`PostMapping /system/project/pool-options`** — 系统设置-系统-组织与项目-项目-获取资源池下拉选项

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ProjectPoolRequest` | Body |

**ProjectPoolRequest 字段明细**:
  - `organizationId`: `String` 组织id *约束: @Size(min = 0, max = 50, message = "project.organization_id.length_range");*
  - `modulesIds`: `List<String>` **[必填]** 项目开启的模块id集合

**返回值**: `List<OptionDTO>`

#### **`PostMapping /system/project/rename`** — 系统设置-系统-组织与项目-项目-修改项目名称

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UpdateProjectNameRequest` | Body |

**UpdateProjectNameRequest 字段明细**:
  - `id`: `String` **[必填]** 项目ID *约束: @Size(min = 1, max = 50, message = "{project.id.length_range}", groups = {Updated.class});*
  - `organizationId`: `String` **[必填]** 组织ID *约束: @Size(min = 1, max = 50, message = "{project.organization_id.length_range}", groups = {Created.class, Updated.class});*
  - `name`: `String` **[必填]** 项目名称 *约束: @Size(min = 1, max = 255, message = "{project.name.length_range}", groups = {Created.class, Updated.class});*

**返回值**: `void`

#### **`GetMapping /system/project/list`** — 系统设置-系统-组织与项目-项目-获取所有项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(description = "查询关键字，根据项目名查询"` | 参数 |
| `` | `requiredMode = Schema.RequiredMode.REQUIRED) (value = "keyword"` | Query |
| `keyword` | `required = false) String` | 参数 |

**返回值**: `List<OptionDTO>`


### SystemTaskHubController
**业务标签**: 系统任务中心

#### **`PostMapping /system/task-center/exec-task/page`** — 系统-任务中心-执行任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BasePageRequest` | Body |

**BasePageRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `current`: `int` 当前页码 *约束: @Min(value = 1, message = "当前页码必须大于0");*
  - `pageSize`: `int` 每页显示条数 *约束: @Min(value = 5, message = "每页显示条数必须不小于5"); @Max(value = 500, message = "每页显示条数不能大于500");*

**返回值**: `Pager<List<TaskHubDTO>>`

#### **`PostMapping /system/task-center/schedule/page`** — 系统-任务中心-后台执行任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BasePageRequest` | Body |

**BasePageRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `current`: `int` 当前页码 *约束: @Min(value = 1, message = "当前页码必须大于0");*
  - `pageSize`: `int` 每页显示条数 *约束: @Min(value = 5, message = "每页显示条数必须不小于5"); @Max(value = 500, message = "每页显示条数不能大于500");*

**返回值**: `Pager<List<TaskHubScheduleDTO>>`

#### **`PostMapping /system/task-center/exec-task/item/page`** — 系统-任务中心-用例执行任务详情列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskHubItemRequest` | Body |

**TaskHubItemRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `taskId`: `String` 任务id
  - `resourcePoolIds`: `List<String>` 资源池id
  - `resourcePoolNodes`: `List<String>` 资源池节点

**返回值**: `Pager<List<TaskHubItemDTO>>`

#### **`PostMapping /system/task-center/exec-task/statistics`** — 系统-任务中心-获取任务统计{通过率}接口

| 参数 | 类型 | 来源 |
|------|------|------|
| `ids` | `List<String>` | Body |

**返回值**: `List<TaskStatisticsResponse>`

#### **`GetMapping /system/task-center/resource-pool/options`** — 系统-任务中心-获取资源池下拉选项

**无入参**

**返回值**: `List<ResourcePoolOptionsDTO>`

#### **`PostMapping /system/task-center/resource-pool/status`** — 任务详情节点状态接口

| 参数 | 类型 | 来源 |
|------|------|------|
| `ids` | `List<String>` | Body |

**返回值**: `List<ResourcePoolStatusDTO>`

#### **`GetMapping /system/task-center/exec-task/stop/{id}`** — 系统-任务中心-用例执行任务-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /system/task-center/exec-task/rerun/{id}`** — 系统-任务中心-用例执行任务-重跑任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /system/task-center/exec-task/batch-stop`** — 系统-任务中心-用例执行任务-批量停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /system/task-center/exec-task/item/order`** — 系统-任务中心-用例执行任务-获取任务项的排队信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `taskIdItemIds` | `List<String>` | Body |

**返回值**: `Map<String, Integer>`

#### **`GetMapping /system/task-center/exec-task/delete/{id}`** — 系统-任务中心-用例执行任务-删除任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /system/task-center/exec-task/batch-delete`** — 系统-任务中心-用例执行任务-批量删除任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /system/task-center/exec-task/batch/page`** — 组织-任务中心-用例执行任务-批量任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BatchExecTaskPageRequest` | Body |

**BatchExecTaskPageRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `taskId`: `String` 任务ID
  - `batchType`: `String`

**返回值**: `Pager<List<BatchExecTaskReportDTO>>`

#### **`GetMapping /system/task-center/exec-task/item/stop/{id}`** — 系统-任务中心-用例任务详情-停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /system/task-center/exec-task/item/batch-stop`** — 系统-任务中心-用例任务详情-批量停止任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskHubItemBatchRequest` | Body |

**TaskHubItemBatchRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `taskId`: `String` 任务id
  - `resourcePoolIds`: `List<String>` 资源池id
  - `resourcePoolNodes`: `List<String>` 资源池节点

**返回值**: `void`

#### **`GetMapping /system/task-center/schedule/delete/{id}`** — 系统-任务中心-系统后台任务-删除

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /system/task-center/schedule/switch/{id}`** — 系统-任务中心-后台任务开启关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /system/task-center/schedule/batch-enable`** — 系统-任务中心-后台任务-批量开启

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /system/task-center/schedule/batch-disable`** — 系统-任务中心-后台任务-批量关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `void`

#### **`PostMapping /system/task-center/schedule/update-cron`** — 系统-任务中心-后台任务更新cron表达式

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ScheduleRequest` | Body |

**ScheduleRequest 字段明细**:
  - `id`: `String` 列表id
  - `cron`: `String` cron表达式

**返回值**: `void`

#### **`GetMapping /system/task-center/project/options`** — 系统-任务中心-获取全部项目下拉选项

**无入参**

**返回值**: `List<OrganizationProjectOptionsDTO>`

#### **`GetMapping /system/task-center/organization/options`** — 系统-任务中心-获取全部组织下拉选项

**无入参**

**返回值**: `List<OrganizationProjectOptionsDTO>`


### SystemVersionController
**业务标签**: 系统版本

#### **`GetMapping /system/version/current`** — 获取当前系统版本

**无入参**

**返回值**: `String`

#### **`GetMapping /system/version/package-type`** — 获取当前系统类型

**无入参**

**返回值**: `String`


### TaskCenterController
**业务标签**: 任务中心-定时任务

#### **`PostMapping /task/center/project/schedule/page`** — 项目-任务中心-定时任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterSchedulePageRequest` | Body |

**返回值**: `Pager<List<TaskCenterScheduleDTO>>`

#### **`PostMapping /task/center/org/schedule/page`** — 组织-任务中心-定时任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterSchedulePageRequest` | Body |

**返回值**: `Pager<List<TaskCenterScheduleDTO>>`

#### **`PostMapping /task/center/system/schedule/page`** — 系统-任务中心-定时任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterSchedulePageRequest` | Body |

**返回值**: `Pager<List<TaskCenterScheduleDTO>>`

#### **`GetMapping /task/center/system/schedule/delete/{moduleType}/{id}`** — 系统-任务中心-删除定时任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /task/center/org/schedule/delete/{moduleType}/{id}`** — 组织-任务中心-删除定时任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /task/center/project/schedule/delete/{moduleType}/{id}`** — 项目-任务中心-删除定时任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /task/center/system/schedule/switch/{moduleType}/{id}`** — 系统-任务中心-定时任务开启关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /task/center/org/schedule/switch/{moduleType}/{id}`** — 组织-任务中心-定时任务开启关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /task/center/project/schedule/switch/{moduleType}/{id}`** — 项目-任务中心-定时任务开启关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /task/center/system/schedule/update/{moduleType}/{id}`** — 系统-任务中心-修改定时任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |
| `cron` | `Object` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/org/schedule/update/{moduleType}/{id}`** — 组织-任务中心-修改定时任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |
| `cron` | `Object` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/project/schedule/update/{moduleType}/{id}`** — 项目-任务中心-修改定时任务

| 参数 | 类型 | 来源 |
|------|------|------|
| `moduleType` | `String` | 路径 |
| `id` | `String` | 路径 |
| `cron` | `Object` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/system/schedule/batch-enable`** — 系统-任务中心-定时任务批量开启

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterScheduleBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/org/schedule/batch-enable`** — 组织-任务中心-定时任务批量开启

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterScheduleBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/project/schedule/batch-enable`** — 项目-任务中心-定时任务批量开启

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterScheduleBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/system/schedule/batch-disable`** — 系统-任务中心-定时任务批量关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterScheduleBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/org/schedule/batch-disable`** — 组织-任务中心-定时任务批量关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterScheduleBatchRequest` | Body |

**返回值**: `void`

#### **`PostMapping /task/center/project/schedule/batch-disable`** — 项目-任务中心-定时任务批量关闭

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TaskCenterScheduleBatchRequest` | Body |

**返回值**: `void`

#### **`GetMapping /task/center/system/schedule/total`** — 系统-任务中心-定时任务总数

**无入参**

**返回值**: `int`

#### **`GetMapping /task/center/org/schedule/total`** — 组织-任务中心-定时任务总数

**无入参**

**返回值**: `int`

#### **`GetMapping /task/center/project/schedule/total`** — 项目-任务中心-定时任务总数

**无入参**

**返回值**: `int`

#### **`GetMapping /task/center/system/real/total`** — 系统-任务中心-实时任务总数

**无入参**

**返回值**: `int`

#### **`GetMapping /task/center/org/real/total`** — 组织-任务中心-实时任务总数

**无入参**

**返回值**: `int`

#### **`GetMapping /task/center/project/real/total`** — 项目-任务中心-实时任务总数

**无入参**

**返回值**: `int`


### TestResourcePoolController
**业务标签**: 系统设置-系统-资源池

#### **`PostMapping /test/resource/pool/update`** — 系统设置-系统-资源池-更新资源池

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestResourcePoolRequest` | Body |

**TestResourcePoolRequest 字段明细**:
  - `id`: `String` **[必填]** 资源池ID *约束: @Size(min = 1, max = 50, message = "{test_resource_pool.id.length_range}", groups = {Updated.class});*
  - `name`: `String` **[必填]** 名称 *约束: @Size(min = 1, max = 255, message = "{test_resource_pool.name.length_range}", groups = {Created.class, Updated.class});*
  - `description`: `String` 描述
  - `type`: `String` **[必填]** 类型 *约束: @Size(min = 1, max = 30, message = "{test_resource_pool.type.length_range}", groups = {Created.class, Updated.class});*
  - `enable`: `Boolean` 是否启用
  - `apiTest`: `Boolean` 是否用于接口测试
  - `loadTest`: `Boolean` 是否用于性能测试
  - `uiTest`: `Boolean` 是否用于ui测试
  - `serverUrl`: `String` ms部署地址
  - `allOrg`: `Boolean` **[必填]** 资源池应用类型（组织/全部）
  - `testResourceDTO`: `TestResourceDTO` 其余配置

**返回值**: `void`

#### **`PostMapping /test/resource/pool/page`** — 系统设置-系统-资源池-获取资源池列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `QueryResourcePoolRequest` | Body |

**QueryResourcePoolRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `enable`: `Boolean` 是否禁用

**返回值**: `Pager<List<TestResourcePoolDTO>>`

#### **`GetMapping /test/resource/pool/detail/{poolId}`** — 系统-资源池-查看资源池详细

| 参数 | 类型 | 来源 |
|------|------|------|
| `testResourcePoolId` | `String` | 路径 |

**返回值**: `TestResourcePoolReturnDTO`

#### **`PostMapping /test/resource/pool/capacity/detail`** — 系统-资源池-查看资源池容量内存详细

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestResourcePoolCapacityRequest` | Body |

**TestResourcePoolCapacityRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `poolId`: `String` **[必填]** 资源池id
  - `ip`: `String` 节点IP
  - `port`: `String` 节点端口

**返回值**: `ResourcePoolNodeMetric`

#### **`PostMapping /test/resource/pool/capacity/task/list`** — 系统-资源池-查看资源池节点任务列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TestResourcePoolCapacityRequest` | Body |

**TestResourcePoolCapacityRequest 字段明细**:
  > **继承**: `BasePageRequest`
  - `poolId`: `String` **[必填]** 资源池id
  - `ip`: `String` 节点IP
  - `port`: `String` 节点端口

**返回值**: `Pager<List<TaskHubItemDTO>>`


### UserApiKeysController
**业务标签**: 系统设置-个人中心-我的设置-Api Keys

#### **`GetMapping /user/api/key/list`** — 系统设置-个人中心-我的设置-Api Keys-获取Api Keys列表

**无入参**

**返回值**: `List<UserKey>`

#### **`GetMapping /user/api/key/validate`** — 系统设置-个人中心-我的设置-Api Keys-验证Api Keys

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `ServletRequest` | 参数 |

**返回值**: `String`

#### **`GetMapping /user/api/key/add`** — 系统设置-个人中心-我的设置-Api Keys-生成Api Keys

**无入参**

**返回值**: `void`

#### **`GetMapping /user/api/key/delete/{id}`** — 系统设置-个人中心-我的设置-Api Keys-删除Api Keys

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /user/api/key/update`** — 系统设置-个人中心-我的设置-Api Keys-修改Api Keys

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserKeyDTO` | Body |

**UserKeyDTO 字段明细**:
  - `id`: `String` **[必填]** user_key ID
  - `forever`: `Boolean` 是否永久有效
  - `expireTime`: `Long` 到期时间
  - `description`: `String` 描述

**返回值**: `void`

#### **`GetMapping /user/api/key/enable/{id}`** — 系统设置-个人中心-我的设置-Api Keys-开启Api Keys

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /user/api/key/disable/{id}`** — 系统设置-个人中心-我的设置-Api Keys-关闭Api Keys

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`


### UserController
**业务标签**: 系统设置-系统-用户

#### **`GetMapping /system/user/get/{keyword}`** — 通过email或id查找用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `keyword` | `String` | 路径 |

**返回值**: `UserDTO`

#### **`PostMapping /system/user/add`** — 系统设置-系统-用户-添加用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `userCreateDTO` | `UserBatchCreateRequest` | Body |

**返回值**: `UserBatchCreateResponse`

#### **`PostMapping /system/user/update`** — 系统设置-系统-用户-修改用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserEditRequest` | Body |

**返回值**: `UserEditRequest`

#### **`PostMapping /system/user/page`** — 系统设置-系统-用户-分页查找用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `BasePageRequest` | Body |

**BasePageRequest 字段明细**:
  > **继承**: `BaseCondition`
  - `current`: `int` 当前页码 *约束: @Min(value = 1, message = "当前页码必须大于0");*
  - `pageSize`: `int` 每页显示条数 *约束: @Min(value = 5, message = "每页显示条数必须不小于5"); @Max(value = 500, message = "每页显示条数不能大于500");*

**返回值**: `Pager<List<UserTableResponse>>`

#### **`PostMapping /system/user/update/enable`** — 系统设置-系统-用户-启用/禁用用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserChangeEnableRequest` | Body |

**返回值**: `TableBatchProcessResponse`

#### **`PostMapping /system/user/import`** — 系统设置-系统-用户-导入用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `` | `(value = "file"` | Form |
| `excelFile` | `required = false) MultipartFile` | 参数 |

**返回值**: `UserImportResponse`

#### **`PostMapping /system/user/delete`** — 系统设置-系统-用户-删除用户

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `TableBatchProcessResponse`

#### **`PostMapping /system/user/reset/password`** — 系统设置-系统-用户-重置用户密码

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `TableBatchProcessDTO` | Body |

**TableBatchProcessDTO 字段明细**:
  - `selectAll`: `boolean` 是否选择所有数据

**返回值**: `TableBatchProcessResponse`

#### **`GetMapping /system/user/get/global/system/role`** — 系统设置-系统-用户-查找系统级用户组

**无入参**

**返回值**: `List<UserSelectOption>`

#### **`GetMapping /system/user/get/organization`** — 系统设置-系统-用户-用户批量操作-查找组织

**无入参**

**返回值**: `List<OptionDTO>`

#### **`GetMapping /system/user/get/project`** — 系统设置-系统-用户-用户批量操作-查找项目

**无入参**

**返回值**: `List<BaseTreeNode>`

#### **`PostMapping /system/user/add/batch/user-role`** — 系统设置-系统-用户-批量添加用户到多个用户组中

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserRoleBatchRelationRequest` | Body |

**UserRoleBatchRelationRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `roleIds`: `List<String>` **[必填]** 权限ID集合

**返回值**: `TableBatchProcessResponse`

#### **`PostMapping /system/user/add-project-member`** — 系统设置-系统-用户-批量添加用户到项目

| 参数 | 类型 | 来源 |
|------|------|------|
| `userRoleBatchRelationRequest` | `UserRoleBatchRelationRequest` | Body |

**UserRoleBatchRelationRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `roleIds`: `List<String>` **[必填]** 权限ID集合

**返回值**: `TableBatchProcessResponse`

#### **`PostMapping /system/user/add-org-member`** — 系统设置-系统-用户-批量添加用户到组织

| 参数 | 类型 | 来源 |
|------|------|------|
| `userRoleBatchRelationRequest` | `UserRoleBatchRelationRequest` | Body |

**UserRoleBatchRelationRequest 字段明细**:
  > **继承**: `TableBatchProcessDTO`
  - `roleIds`: `List<String>` **[必填]** 权限ID集合

**返回值**: `TableBatchProcessResponse`

#### **`PostMapping /system/user/invite`** — 系统设置-系统-用户-邀请用户注册

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserInviteRequest` | Body |

**UserInviteRequest 字段明细**:
  - `organizationId`: `String` 组织ID
  - `projectId`: `String` 项目ID

**返回值**: `UserInviteResponse`

#### **`GetMapping /system/user/check-invite/{inviteId}`** — 系统设置-系统-用户-用户接受注册邀请并创建账户

| 参数 | 类型 | 来源 |
|------|------|------|
| `inviteId` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /system/user/register-by-invite`** — 系统设置-系统-用户-用户接受注册邀请并创建账户

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserRegisterRequest` | Body |

**UserRegisterRequest 字段明细**:
  - `inviteId`: `String` **[必填]** 被邀请ID
  - `name`: `String` **[必填]** 用户名 *约束: @Size(min = 1, max = 255, message = "{user.name.length_range}");*
  - `password`: `String` **[必填]** 用户密码
  - `phone`: `String` 用户手机号

**返回值**: `String`


### UserLocalConfigController
**业务标签**: 系统设置-个人中心-我的设置-本地执行

#### **`PostMapping /user/local/config/add`** — 系统设置-个人中心-我的设置-本地执行-添加本地执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserLocalConfigAddRequest` | Body |

**UserLocalConfigAddRequest 字段明细**:
  - `userUrl`: `String` **[必填]** 本地执行程序url *约束: @Size(min = 1, max = 50, message = "{user_local_config.user_url.length_range}");*

**返回值**: `UserLocalConfig`

#### **`GetMapping /user/local/config/get`** — 系统设置-个人中心-我的设置-本地执行-获取本地执行

**无入参**

**返回值**: `List<UserLocalConfig>`

#### **`GetMapping /user/local/config/enable/{id}`** — 系统设置-个人中心-我的设置-本地执行-启用本地执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`GetMapping /user/local/config/disable/{id}`** — 系统设置-个人中心-我的设置-本地执行-禁用本地执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |

**返回值**: `void`

#### **`PostMapping /user/local/config/update`** — 系统设置-个人中心-我的设置-本地执行-更新本地执行

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserLocalConfigUpdateRequest` | Body |

**UserLocalConfigUpdateRequest 字段明细**:
  - `id`: `String` **[必填]** ID
  - `userUrl`: `String` 本地执行程序url *约束: @Size( max = 50, message = "{user_local_config.user_url.length_range}");*

**返回值**: `void`

#### **`GetMapping /user/local/config/default-locale`**

**无入参**

**返回值**: `String`


### UserPlatformAccountController
**业务标签**: 系统设置-个人中心-三方平台账号

#### **`GetMapping /user/platform/account/info`** — 系统设置-个人中心-获取三方平台账号信息(插件信息)

**无入参**

**返回值**: `Map<String, Object>`

#### **`PostMapping /user/platform/validate/{pluginId}/{orgId}`** — 系统设置-个人中心-校验用户集成信息

| 参数 | 类型 | 来源 |
|------|------|------|
| `pluginId` | `String` | 路径 |
| `orgId` | `String` | 路径 |
| `` | `(description = "用户配置集成信息"` | Body |
| `userPlatformConfig` | `requiredMode = Schema.RequiredMode.REQUIRED)Map<String, String>` | 参数 |

**返回值**: `void`

#### **`PostMapping /user/platform/save`** — 系统设置-个人中心-保存三方平台账号(这里的应该是插件信息加账号值)

| 参数 | 类型 | 来源 |
|------|------|------|
| `platformInfo` | `Map<String, Object>` | Body |

**返回值**: `void`

#### **`GetMapping /user/platform/get/{orgId}`** — 系统设置-个人中心-获取个人三方平台账号

| 参数 | 类型 | 来源 |
|------|------|------|
| `orgId` | `String` | 路径 |

**返回值**: `Map<String, Object>`

#### **`GetMapping /user/platform/switch-option`** — 个人中心-三方平台-组织下拉选项

**无入参**

**返回值**: `List<OptionDTO>`


### UserViewController
**业务标签**: 视图

#### **`GetMapping /user-view/{viewType}/list`** — 视图列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `scopeId` | `String` | Query |
| `viewType` | `String` | 路径 |

**返回值**: `List<UserView>`

#### **`GetMapping /user-view/{viewType}/grouped/list`** — 视图列表

| 参数 | 类型 | 来源 |
|------|------|------|
| `scopeId` | `String` | Query |
| `viewType` | `String` | 路径 |

**返回值**: `UserViewListGroupedDTO`

#### **`GetMapping /user-view/{viewType}/get/{id}`** — 视图详情

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `viewType` | `String` | 路径 |

**返回值**: `UserViewDTO`

#### **`PostMapping /user-view/{viewType}/add`** — 新增视图

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserViewAddRequest` | Body |
| `viewType` | `String` | 路径 |

**UserViewAddRequest 字段明细**:
  > **继承**: `CombineSearch`
  - `scopeId`: `String` **[必填]** 视图的应用范围，一般为项目ID
  - `name`: `String` **[必填]** 视图名称

**返回值**: `UserViewDTO`

#### **`PostMapping /user-view/{viewType}/update`** — 编辑视图

| 参数 | 类型 | 来源 |
|------|------|------|
| `request` | `UserViewUpdateRequest` | Body |
| `viewType` | `String` | 路径 |

**UserViewUpdateRequest 字段明细**:
  > **继承**: `CombineSearch`
  - `id`: `String` **[必填]** 视图ID
  - `name`: `String` **[必填]** 视图名称

**返回值**: `UserViewDTO`

#### **`GetMapping /user-view/{viewType}/delete/{id}`** — 删除视图

| 参数 | 类型 | 来源 |
|------|------|------|
| `id` | `String` | 路径 |
| `viewType` | `String` | 路径 |

**返回值**: `void`
