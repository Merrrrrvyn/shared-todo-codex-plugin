# 远程 MCP 对接约定

**本仓库不包含服务端**，以下是插件依赖的接口约定。REST `/api/v1` 不能当作 MCP 地址。公网 `https://api.todolist.yymervyn.top/mcp` 已于 2026-11-16 部署并验收；自建服务应实现这里的工具、授权及权限检查。

## 身份与权限

客户端通过浏览器 OAuth 授权码 + PKCE 流程取得面向 MCP 资源的令牌。令牌及刷新由客户端的 OAuth 机制管理。插件中不携带客户端密钥或用户凭据。

当前 `.mcp.json` 未固定 `client_id`。服务端提供授权服务器及受保护资源发现元数据，并支持公共客户端 DCR（`token_endpoint_auth_method=none`）。MCP URL、资源发现和令牌受众必须匹配。不向桌面插件分发 confidential client secret。

范围：`todo:read`（清单、待办、必要成员查询及内置模板查询）、`todo:write`（新增、修改、完成、重开待办）、`todo:delete`（删除待办）、`list:write`（新建清单、按模板创建清单及初始待办，修改自有清单与邮件通知）、`list:delete`（永久删除自有清单及全部待办）。模板查询使用 `todo:read`；使用模板创建清单只需 `list:write`，初始待办由创建清单操作一并生成，不额外要求 `todo:write`。模板不会引入新的授权范围。原有令牌不会自动获得新范围。实际权限为授权范围与当前清单成员权限的交集，每次操作重新检查；viewer 不能写待办，非成员不能访问，修改或删除清单需创建者身份。只有写权限时，新增和修改仅返回 `id` / `list_id`。

## 工具与现有 API

实际调用以 MCP 动态提供的 schema 为准。新增与修改的待办字段放在 `payload` 对象内；工具不接受用于决定操作者的 `user_id`。

| 工具 | 核心参数 | 复用的 REST 路径（相对 `/api/v1`） | 范围 |
| --- | --- | --- | --- |
| `list_templates` | 无 | `GET /list-templates` | `todo:read` |
| `list_lists` | 无 | `GET /lists` | `todo:read` |
| `get_list` | `list_id` | `GET /lists/{list_id}` | `todo:read` |
| `create_list` | `payload: {name, description?, template?: string|null, email_notify_enabled?, email_notify_time?, email_notify_tz_offset?}` | `POST /lists` | `list:write` |
| `update_list` | `list_id`, `payload: {仅需更新的清单字段}` | `PATCH /lists/{list_id}` | `list:write` + 创建者 |
| `delete_list` | `list_id` | `DELETE /lists/{list_id}` | `list:delete` + 创建者 |
| `list_members` | `list_id` | `GET /lists/{list_id}/members` | `todo:read` |
| `list_todos` | `list_id`, `status`, `keyword`, `assignee_id`, `page`, `size` | `GET /lists/{list_id}/todos` | `todo:read` |
| `get_todo` | `todo_id` | `GET /todos/{todo_id}` | `todo:read` |
| `create_todo` | `list_id`, `payload: {title, ...}` | `POST /lists/{list_id}/todos` | `todo:write` |
| `update_todo` | `todo_id`, `payload: {仅需更新的字段}` | `PATCH /todos/{todo_id}` | `todo:write` |
| `delete_todo` | `todo_id` | `DELETE /todos/{todo_id}` | `todo:delete` |

`list_templates` 不接收参数，调用 `GET /list-templates` 返回完整的内置模板目录。每个模板包含 `id`、`name`、`description`、`icon` 和 `items`；每个初始待办项包含 `title`、`priority`、`recurrence`、`note`，可选字段可能为 `null`。可用 ID 为 `chores`（家庭日常）、`groceries`（周末采购）、`moving`（搬家待办）、`trip`（出行准备）、`english`（英语启蒙）；ID 是固定英文标识，不能用中文名称代替。`english` 模板包含 7 条初始待办。

按模板新建清单时，先调用 `list_templates` 并按 `name` 找到对应模板，再将其原样 `id` 传给 `create_list` 的 `payload.template`。例如“用英语启蒙模板创建清单，描述 week9 并开启邮件通知”应一次提交 `{"payload":{"name":"英语启蒙","description":"week9","template":"english","email_notify_enabled":true}}`。服务端随该创建请求一并生成模板初始待办；客户端不要再逐项调用 `create_todo`，也不要要求用户提供网页链接或模板内容。用户所指模板无法唯一匹配时，先让用户从模板名称中选择。清单创建超时后先查询确认结果，无法确认时不要重试非幂等创建。

待办字段：`title`、`note`、`priority`（0 普通 / 1 重要 / 2 紧急）、`due_at`（带时区时间）、`assignee_id`、`recurrence`（daily / weekly / monthly）、`recurrence_until`。更新还支持 `status`（pending / done）。时间必须带时区；更新的 `title`、`status`、`priority` 不允许显式 null。其他字段的可空性以服务端 schema 为准。清单查询结果不包含邀请码。

服务端复用已有业务处理，保留实时广播、动态记录、指派提醒与重复任务。操作身份来自已验证的 MCP 令牌，不能由客户端参数决定；MCP 令牌不作为网页 API 令牌透传。

清单字段限 `name`（去除两端空格，不能为空）、`description`（可显式 null 清空）、创建时可选的 `template`（内置英文 ID 或 null）、`email_notify_enabled`、`email_notify_time`（HH:MM）、`email_notify_tz_offset`（-720..840 分钟）。新建默认关闭通知、09:00、UTC+8；更新省略字段保持原值，名称与邮件字段拒绝显式 null。`template` 仅用于创建时选择内置模板；接口不接受 `schedule`、`owner_id` 等额外字段。模板项使用 `priority`（0 普通 / 1 重要 / 2 紧急）、可选 `recurrence`（daily / weekly / monthly）和可选 `note`，不预设截止时间。

`delete_list` 不接收操作者 ID，删除成功仅返回 `{"id":list_id,"deleted":true}`；清单、待办及成员关系通过现有外键级联删除，保留原有实时 `list.deleted` 广播。该工具声明为破坏性、非幂等，旧版四范围授权不能执行。

清单查询和有读取权限的写入响应包含邮件开关、时间、时区和最近发送时间，不包含邀请码。邮件开关设置的是清单未完成待办汇总，配置保存不等于实际投递。

## 联调验收范围

1. 未登录时触发浏览器授权，用户不向模型提供密码或令牌。
2. 两个账号各自授权，清单和凭据互不串用。
3. owner/editor 完成新增、查询、修改、完成、重开、删除，网页收到实时变更。
4. viewer 写入失败，非成员读取失败；被移出清单后立即不能继续访问。
5. 只读授权不能写入；撤销某客户端授权后，该连接不能访问或刷新令牌。
6. 错误的 PKCE、回调地址、资源受众、过期或重复消费的授权码均被拒绝。

配套服务的自动化测试使用隔离数据库检查协议、授权生命周期与角色权限；本地浏览器联调覆盖登录回跳、授权、工具写入及设置页撤销。公网验收已完成真实 Codex CLI OAuth 登录、工具增删改查、角色隔离、WebSocket 推送及授权撤销；其他 AI 客户端和跨设备兼容性仍需分别验证。本仓库的自动化测试验证插件格式、打包边界及安装。
