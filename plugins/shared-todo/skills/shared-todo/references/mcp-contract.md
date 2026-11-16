# 远程 MCP 对接约定

**本仓库不包含服务端**，以下是插件依赖的接口约定。REST `/api/v1` 不能当作 MCP 地址。公网 `https://api.todolist.yymervyn.top/mcp` 已于 2026-11-16 部署并验收；自建服务应实现这里的工具、授权及权限检查。

## 身份与权限

客户端通过浏览器 OAuth 授权码 + PKCE 流程取得面向 MCP 资源的令牌。令牌及刷新由客户端的 OAuth 机制管理。插件中不携带客户端密钥或用户凭据。

当前 `.mcp.json` 未固定 `client_id`。服务端提供授权服务器及受保护资源发现元数据，并支持公共客户端 DCR（`token_endpoint_auth_method=none`）。MCP URL、资源发现和令牌受众必须匹配。不向桌面插件分发 confidential client secret。

范围：`todo:read`（清单、待办及必要成员查询）、`todo:write`（新增、修改、完成、重开）、`todo:delete`（删除）。实际权限为授权范围与当前清单成员权限的交集，每次操作重新检查；viewer 不能写入，非成员不能访问。只有写权限时，新增和修改仅返回 `id` / `list_id`。

## 工具与现有 API

实际调用以 MCP 动态提供的 schema 为准。新增与修改的待办字段放在 `payload` 对象内；工具不接受用于决定操作者的 `user_id`。

| 工具 | 核心参数 | 复用的 REST 路径（相对 `/api/v1`） | 范围 |
| --- | --- | --- | --- |
| `list_lists` | 无 | `GET /lists` | `todo:read` |
| `list_members` | `list_id` | `GET /lists/{list_id}/members` | `todo:read` |
| `list_todos` | `list_id`, `status`, `keyword`, `assignee_id`, `page`, `size` | `GET /lists/{list_id}/todos` | `todo:read` |
| `get_todo` | `todo_id` | `GET /todos/{todo_id}` | `todo:read` |
| `create_todo` | `list_id`, `payload: {title, ...}` | `POST /lists/{list_id}/todos` | `todo:write` |
| `update_todo` | `todo_id`, `payload: {仅需更新的字段}` | `PATCH /todos/{todo_id}` | `todo:write` |
| `delete_todo` | `todo_id` | `DELETE /todos/{todo_id}` | `todo:delete` |

待办字段：`title`、`note`、`priority`（0 普通 / 1 重要 / 2 紧急）、`due_at`（带时区时间）、`assignee_id`、`recurrence`（daily / weekly / monthly）、`recurrence_until`。更新还支持 `status`（pending / done）。时间必须带时区；更新的 `title`、`status`、`priority` 不允许显式 null。其他字段的可空性以服务端 schema 为准。清单查询结果不包含邀请码。

服务端复用已有业务处理，保留实时广播、动态记录、指派提醒与重复任务。操作身份来自已验证的 MCP 令牌，不能由客户端参数决定；MCP 令牌不作为网页 API 令牌透传。

## 联调验收范围

1. 未登录时触发浏览器授权，用户不向模型提供密码或令牌。
2. 两个账号各自授权，清单和凭据互不串用。
3. owner/editor 完成新增、查询、修改、完成、重开、删除，网页收到实时变更。
4. viewer 写入失败，非成员读取失败；被移出清单后立即不能继续访问。
5. 只读授权不能写入；撤销某客户端授权后，该连接不能访问或刷新令牌。
6. 错误的 PKCE、回调地址、资源受众、过期或重复消费的授权码均被拒绝。

配套服务的自动化测试使用隔离数据库检查协议、授权生命周期与角色权限；本地浏览器联调覆盖登录回跳、授权、工具写入及设置页撤销。公网验收已完成真实 Codex CLI OAuth 登录、工具增删改查、角色隔离、WebSocket 推送及授权撤销；其他 AI 客户端和跨设备兼容性仍需分别验证。本仓库的自动化测试验证插件格式、打包边界及安装。
