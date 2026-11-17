# Shared Todo for WorkBuddy

此目录提供 WorkBuddy 的本地自定义 MCP 配置和专用技能。适配包版本为 `1.0.0`，独立于 Codex 插件版本。

## 安装顺序

先添加并连接 Shared Todo MCP，再导入并启用技能。技能只告诉 WorkBuddy 如何使用工具，不会替用户建立连接或登录；若工具尚未出现在会话中，技能不能代替连接器完成操作。

### 1. 添加自定义 MCP 连接

在 WorkBuddy 左侧打开“专家·技能·连接器”，进入“连接器”，点击“自定义连接器”打开 MCP 服务管理，再点击“添加 MCP”。经 WorkBuddy 5.9.3 本机确认，配置文件路径为 `~/.workbuddy/mcp.json`。将 [`connector.json`](connector.json) 中 `mcpServers.shared-todo` 对象合并到编辑器中现有的 `mcpServers` 中：

```json
{
  "mcpServers": {
    "shared-todo": {
      "type": "http",
      "url": "https://api.todolist.yymervyn.top/mcp"
    }
  }
}
```

若配置文件已有其他 MCP 服务器，只添加 `shared-todo` 项，不要覆盖其他条目。保存后返回 MCP 列表，并在首次连接提示中信任该连接器。WorkBuddy 5.9.3 已验证能发现并启用 Shared Todo 的 12/12 个工具。需要授权时，通过 WorkBuddy 提供的浏览器流程登录 Shared Todo 并选择权限，不要把密码或令牌粘贴到配置文件、聊天或技能中。此前已完成 WorkBuddy 独立授权时，无需为了安装技能再次登录。

这份配置用于 WorkBuddy 的本地自定义 MCP，不是 WorkBuddy 市场连接器包，也不包含 `scopes`、自定义请求头、客户端密钥或用户令牌。请以本机 WorkBuddy 显示的配置格式为准。

### 2. 导入技能 ZIP

在 WorkBuddy 左侧打开“专家·技能·连接器”，选择顶部“技能”页，再依次点击“添加技能”→“上传技能”→“选择 ZIP 文件”，选择发布包中的 `shared-todo-skill.zip`。等待客户端安全检测，查看结果后按页面提示继续安装；不要跳过检测。进入“已安装”确认 `shared-todo` 的开关为启用状态。

本项目生成的 ZIP 内部路径为 `shared-todo/SKILL.md`，无需手工重排，也不要直接导入整个源码仓库。WorkBuddy 5.9.3 实测通过安全检测（结果为“安全”），安装后文件位于 `~/.workbuddy/skills/shared-todo/SKILL.md`，与源码逐字节一致。其他客户端版本以实际导入提示为准。

导入完成后，在新对话中验证技能已启用且 Shared Todo 工具可用。可以先用“列出我能访问的待办清单”做只读检查，再进行用户明确要求的写入操作。

### 3. 在对话中使用

无需切换为专门的专家，也无需在终端运行 Codex 命令。在 WorkBuddy 新建任务中输入自然语言即可，例如：

```text
请使用 shared-todo 共享待办技能，查看内置模板，列出模板名称和英文 ID，只查询不修改。
```

```text
查看我的共享待办清单，列出清单名称和 ID。
```

```text
用英语启蒙模板创建“英语启蒙 week9”，描述为“第九周计划”，开启邮件通知。
```

```text
把清单“英语启蒙 week9”中第一项待办的处理结果记录为“已练习”，保留备注，先不要标记完成。
```

清单或待办重名时先选定 ID；实际工具调用成功后，技能才会报告完成。备注 `note` 与处理结果 `result` 都可留空，修改时省略保留、显式 null 清空；填写结果不会自动完成待办。

## 能力范围

技能使用 Shared Todo MCP 提供的 12 类工具：模板、清单、成员和待办的查询；清单和待办创建、编辑、完成、重新打开及删除。它也指导 WorkBuddy 保留备注与处理结果的区别、按模板一次创建、遵守分页和权限、处理级联删除，并在请求超时后先查证再决定下一步。具体工具名和参数以服务端在 WorkBuddy 会话中动态提供的 schema 为准。

清单和待办数据由 Shared Todo 服务按已授权账号及成员权限隔离。`todo:read`、`todo:write`、`todo:delete`、`list:write`、`list:delete` 分别控制读取、待办写入、待办删除、清单创建/编辑和清单删除；清单设置修改和清单删除还要求创建者身份。只有写入权限时，服务可能只返回对象 ID，技能不会绕过权限补读数据。

## OAuth 与自建服务说明

配置文件只声明 MCP URL，OAuth 由 WorkBuddy 管理，不携带账号凭据。本机已有独立的 WorkBuddy Connector 授权，服务端记录使用 loopback HTTP 回调、申请现有五项业务范围；本次沿用该授权完成真实只读查询，没有读取或迁移 Codex 凭据。账号授权仍由每位用户在自己的客户端完成，安装技能不会自动授予账号权限。

2026-11-17 本机 WorkBuddy 5.9.3 验收：连接器发现 12 个工具、ZIP 安全检测通过、技能安装启用、`list_templates` 返回 5 个模板、`list_lists` 返回当前账号 4 份可访问清单。后两个数量是当时账号/服务的查询结果，不是固定配额。本次未在真实账号执行写入验收，也未重新申请授权或强制触发令牌刷新；这几项不应表述为本次已完成的端到端测试。

自建 Shared Todo 服务也需要正确实现 MCP 与 OAuth，并允许当前 WorkBuddy 客户端的授权回调及资源受众。只改配置中的 URL 并不能保证自建环境可用；自建服务与 WorkBuddy OAuth 的兼容性需单独验证。

## 校验与打包

在仓库根目录运行，需要 Python 3.9 或更高版本：

```bash
python3 scripts/package_workbuddy.py --check
python3 -m unittest discover -s tests -q
python3 scripts/package_workbuddy.py
```

默认输出在 `dist/workbuddy/shared-todo-workbuddy-1.0.0/`：

```text
shared-todo-workbuddy-1.0.0/
├── README.md
├── connector.json
├── shared-todo-skill.zip       # 在 WorkBuddy 中选择这个文件
├── skills/shared-todo/SKILL.md
└── SHA256SUMS.json
```

源码和 ZIP 都不含用户配置、凭据、数据库或 Codex 插件元数据。打包器使用固定白名单，拒绝凭据字段、符号链接及覆盖已有发布目录，输出 SHA-256 校验清单。已有同名产物时使用不同输出目录，例如 `--output dist/workbuddy-new-build`，不会原地覆盖旧包。

自建服务仅替换生成的连接器 URL，不修改源文件：

```bash
python3 scripts/package_workbuddy.py --mcp-url https://your-domain.example/mcp --output dist/workbuddy-custom
```

本地 HTTP 联调必须显式使用 `--allow-local-http`，且仅允许 loopback 地址；不要把本地联调配置作为公网服务发布。离线打包校验成功只证明包结构有效，不代表目标服务已连接或账号已授权。

## 更新与卸载

更新技能时先用新的发布 ZIP 导入，并按 WorkBuddy 的冲突提示处理已有同名技能；本项目不自动覆盖用户修改过的技能文件。临时不用时在“已安装”中关闭技能，需要移除时使用 WorkBuddy 的卸载入口。连接器和技能分别管理，停用技能不会自动断开 MCP 连接。

如需撤销服务端访问，前往 Shared Todo 网页“设置 → 已授权的 AI 客户端”，撤销对应 WorkBuddy 授权。不要仅凭删除本地技能就认为服务端授权已撤销。

## 依据与兼容范围

- [WorkBuddy 官方技能文档](https://www.workbuddy.ai/docs/zh/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills)：上传与启用技能。
- [WorkBuddy 官方连接器文档](https://www.workbuddy.ai/docs/zh/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Connector)：自定义 MCP 入口。
- 本文具体配置路径、`type: "http"`、ZIP 导入方式及可用状态以 WorkBuddy 5.9.3 本机实测为依据。CodeBuddy CLI 文档中的配置目录不应直接当作 WorkBuddy 桌面配置目录。
- 本目录是可供用户导入的自定义 MCP 和技能适配，不代表已上架 WorkBuddy 官方连接器或技能市场。

## 常见问题

- **技能提示找不到工具：** 检查 `mcp.json` 是否保存、服务器名是否为 `shared-todo`，并确认 WorkBuddy 当前会话已加载连接器。技能不会在连接失败时假称操作成功。
- **授权失败或返回 401：** 通过 WorkBuddy 连接器重新授权。不要把令牌发给模型；现有授权范围不足时，需要在 WorkBuddy 授权流程中重新授予服务要求的权限。
- **只能写入，不能查看结果：** 当前授权可能没有 `todo:read`。只读回对象 ID 时，不能据此确认完整内容或邮件配置。
- **清单无法修改或删除：** 相关权限之外，修改或删除自有清单还要求当前账号是清单创建者。
- **邮件提醒已开启但没有邮件：** 保存成功表示配置已启用，不表示邮件已经发送；邮件由服务根据未完成待办和发送时间处理。

## 源码布局

- `connector.json`：可合并到 WorkBuddy 本地 `mcp.json` 的配置片段。
- `skills/shared-todo/SKILL.md`：WorkBuddy 专用技能源文件。
- 发布 ZIP 根目录：`shared-todo/SKILL.md`。
