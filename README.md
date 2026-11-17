# Shared Todo · Codex CLI 插件

预览版 `0.1.0-alpha.7`。插件包含共享待办 Skill 和远程 HTTP MCP 配置，可查询内置模板并一键创建含初始待办的清单，也可管理自有清单、邮件通知和待办处理结果。此仓库只分发插件与打包工具，不包含服务端或用户凭据。

**服务状态：MCP/OAuth 已于 2026-11-16 部署并完成公网验收。** 默认地址 `https://api.todolist.yymervyn.top/mcp` 提供 12 个清单、模板和待办工具、独立授权、权限隔离和撤销。请先在 `https://todolist.yymervyn.top` 注册或准备现有账号。

**处理结果兼容性：** 公网服务已于 2026-11-17 完成 `a94cb2e80d16` 数据库迁移及 MCP 更新，alpha.7 可读写可选的待办 `result` 字段。自建服务须先应用该迁移并更新服务端，再使用此字段。备注 `note` 与处理结果 `result` 是独立字段。

## 阅读导航

- [第一次使用：安装、登录与验证](#安装到-codex-cli)
- [授权范围、成员角色与版本升级](#登录与权限)
- [可以直接复制的使用示例](#使用示例)
- [待办字段与填写规则](#待办字段与填写规则)
- [12 个工具与能力边界](#工具与能力边界)
- [常见问题与排查顺序](#常见问题与排查顺序)
- [自建服务、校验和打包](#校验测试与打包)
- [卸载、更新与数据说明](#分发与更新)

日常使用只需在 Codex 对话中描述需求，无需自己填写 JSON，也不需要部署本项目后端。使用默认托管服务时，请准备一个 Shared Todo 账号；账号中的清单与网页是同一份数据。

## 安装到 Codex CLI

以下命令按本机 `codex-cli 0.169.0` 的 CLI 核验。其他版本先检查 `codex plugin --help`。

### 1. 准备账号与客户端

1. 在 [Shared Todo 网页](https://todolist.yymervyn.top) 注册或登录，确认能看到自己的清单。Shared Todo 的登录和后续授权均在浏览器中完成。
2. 在准备使用插件的本机终端检查 Codex。本文命令应在终端执行；后面的自然语言示例则在 Codex 对话中输入。

```bash
codex --version
codex plugin --help
```

如果提示找不到 `codex`，先按 [OpenAI 官方 Codex CLI 文档](https://developers.openai.com/codex/cli/)安装并完成 Codex 自身登录。如果能运行 Codex、但没有 `plugin` 子命令，请先升级客户端到支持插件的版本；本项目不声明一个未经验证的最低版本。

Codex 自身登录与 Shared Todo 的 OAuth 授权是两件事：前者让你使用 Codex，后者允许插件操作你在 Shared Todo 中有权限访问的清单。本文实测路径为 Codex CLI；其他客户端是否支持同一插件格式和安装入口，需要分别核对。

### 2. 添加 GitHub 来源并安装

以下命令通常只需首次执行，可从任意工作目录运行，无需先克隆仓库：

```bash
codex plugin marketplace add https://github.com/Merrrrrvyn/shared-todo-codex-plugin.git
codex plugin add shared-todo@shared-todo
```

几个名称的含义：

| 名称 | 用途 |
| --- | --- |
| `shared-todo` marketplace | 插件的更新来源，对应本 GitHub 仓库 |
| `shared-todo@shared-todo` | 安装或卸载时使用的插件标识 |
| `shared-todo` MCP server | 登录、退出授权时使用的服务名称 |
| `$shared-todo` | 在对话中明确要求使用此 Skill |

### 3. 在浏览器授权账号

```bash
codex mcp login shared-todo
```

终端会引导打开浏览器。如果尚未登录 Shared Todo，请先登录，再核对授权账号、客户端名称和申请权限。按需要选择权限并确认，回到终端等待登录成功。若安装时已经完成授权，先查看状态，无需为了重复操作而退出登录。

不必在对话中提供密码、网页 token、访问令牌或刷新令牌。插件已有 MCP 配置，不需要另外执行 `codex mcp add` 再注册一份同名服务。

### 4. 核验安装并开始第一次查询

```bash
codex plugin list
codex plugin marketplace list
codex mcp list
```

检查插件 `shared-todo@shared-todo` 为 installed/enabled，版本为本文对应的 `0.1.0-alpha.7` 或你明确安装的更新版本；marketplace 应来自上面的 GitHub URL。MCP 服务应为 enabled，地址为 `https://api.todolist.yymervyn.top/mcp`，认证方式为 OAuth。CLI 不同版本的输出格式可能不同，版本与服务状态应以本机输出为准。

然后**重新开启 Codex 会话**，输入：

```text
$shared-todo
请查看我可以访问的清单，列出清单名称、ID 和我的角色。只查询，不修改。
```

如果账号还没有清单，可以继续说：

```text
帮我新建一份 Shared Todo 清单，名称是“插件使用练习”，描述是“先熟悉新增和查询”，先不要开启邮件通知。
```

Codex 应以实际工具响应确认创建结果，并告诉你清单名称和 ID。安装成功本身不代表已经创建清单。

如果已添加同名本地 marketplace，可先运行 `codex plugin marketplace list` 核对来源，再移除旧插件和旧来源后改用上述公开地址，避免继续加载本地缓存。维护源码时，也可从克隆目录运行 `codex plugin marketplace add .`。

## 登录与权限

1. 安装或首次连接时，按 Codex 的认证提示打开浏览器。
2. 登录现有 Shared Todo 账号，确认授权范围。
3. 由 Codex OAuth 机制管理令牌；每位用户独立授权。

在 Codex CLI 0.169.0 中，MCP 服务器名为 `shared-todo`（插件安装标识为 `shared-todo@shared-todo`）。连接运行中的服务后，手动登录命令为：

```bash
codex mcp login shared-todo
```

其他版本可先用 `codex mcp list` 核对名称。不要额外注册一份重复服务器。

### 从 alpha.6 升级

alpha.7 增加待办处理结果 `result` 的插件指引与接口契约，不增加授权范围。公网服务已完成所需数据库迁移和 MCP 更新；自建服务须先升级。刷新 marketplace、重新安装并开启新会话：

```bash
codex plugin marketplace upgrade shared-todo
codex plugin remove shared-todo@shared-todo
codex plugin add shared-todo@shared-todo
```

### 从 alpha.5 升级

alpha.6 在插件指引和 MCP 接口约定中补充了待办备注操作方式，不增加授权范围。刷新 marketplace、重新安装插件并开启新会话即可：

```bash
codex plugin marketplace upgrade shared-todo
codex plugin remove shared-todo@shared-todo
codex plugin add shared-todo@shared-todo
```

### 从 alpha.4 升级

alpha.5 增加了模板查询工具，沿用现有权限范围，不需要重新登录或授权。刷新 marketplace、重新安装插件并开启新会话即可：

```bash
codex plugin marketplace upgrade shared-todo
codex plugin remove shared-todo@shared-todo
codex plugin add shared-todo@shared-todo
```

新会话会发现 12 个工具。已有 OAuth 登录保持有效。

### 从 alpha.2 / alpha.3 升级

新建和修改清单需要 `list:write`；**永久删除清单及其中全部待办需要新增的 `list:delete`**。旧令牌不会自动获得新权限。先刷新 marketplace、重装插件并清除旧客户端登录缓存，然后在浏览器明确确认所需权限：

```bash
codex plugin marketplace upgrade shared-todo
codex mcp logout shared-todo
codex plugin remove shared-todo@shared-todo
codex plugin add shared-todo@shared-todo
codex mcp login shared-todo --scopes todo:read,todo:write,todo:delete,list:write,list:delete
```

之后开启新的 Codex 会话，重新发现 12 个工具。模板查询使用已有 `todo:read`，模板创建使用已有 `list:write`，不需要新增授权范围。`--scopes` 仅指定申请范围，浏览器中仍需勾选“永久删除自有清单及其中全部待办”。只刷新 access token 不能扩权，`todo:delete` 和 `list:write` 都不包含删除清单权限；旧注册元数据可能拒绝新范围，所以不要跳过退出重连。

### 登录成功但仍提示缺少 list:write / list:delete

`--scopes` 指定的是申请范围，浏览器确认页必须同时勾选你希望授予的清单管理权限。`codex mcp list` 显示 OAuth 也不能证明运行中的对话连接已读取最新令牌。

如果已确认授权但旧会话仍报错，退出当前 CLI 后，使用独立后台启动新进程再试：

```bash
codex --no-daemon
```

该参数只绕过本次启动的共享后台，不会重启其他正在运行的会话。本地曾观察到 CLI 0.169.0 与共享后台 0.163.0 并存；普通退出再打开可能仍连接旧后台。可以用 `codex app-server daemon version` 检查版本。

2026-11-16 服务端已修复“重复确认授权页导致上一份登录提前失效”：只有新授权码成功交换令牌后，才替换同客户端的旧授权。放弃页面、错误 PKCE 或换码失败不会提前注销旧连接。

已使用 Codex CLI 0.169.0 和隔离配置分别完成本地及公网服务 DCR/OAuth 登录验证，连接状态为 OAuth。公网验收覆盖待办操作、成员权限、实时推送及授权撤销，测试账号与凭据已清理。

当前配置不包含固定 `client_id`。配套服务支持公共客户端 DCR 与 S256 PKCE；Codex 可自动注册，不需要在插件中放置客户端密钥。资源发现与令牌受众需与实际 MCP URL 一致。

申请范围为 `todo:read`、`todo:write`、`todo:delete`、`list:write`、`list:delete`，用户可以在授权页缩小范围。owner/editor 可修改待办，viewer 只读；**已有清单的名称、描述、邮件设置与删除仅创建者可操作**。非成员不可访问，服务端逐次校验。只有写权限时，写入结果仅返回 ID，不返回已有描述/备注/通知设置。模板目录读取需要 `todo:read`；按模板创建清单只需 `list:write`，服务器会在同一创建操作中加入模板待办，不额外要求 `todo:write`。

### 怎样选择权限

| OAuth 范围 | 允许的操作 | 不包含的能力 |
| --- | --- | --- |
| `todo:read` | 查询可访问清单、待办、清单成员和内置模板 | 新建、修改或删除 |
| `todo:write` | 新增、修改、完成、重开待办，包括备注和处理结果 | 删除待办、管理清单设置 |
| `todo:delete` | 删除单条待办 | 删除整份清单 |
| `list:write` | 新建清单、按内置模板创建、修改自己的清单名称/描述/邮件设置 | 删除清单，修改其他人创建的清单设置 |
| `list:delete` | 永久删除自己创建的清单及其中全部待办 | 删除其他人创建的清单 |

权限需要同时满足 **OAuth 范围** 和 **清单角色**。例如，给 viewer 授予 `todo:write` 仍不能让他修改待办；创建者未授予 `list:delete` 也不能通过插件删除自己的清单。

| 清单角色 | 查看清单/待办 | 新增、编辑、完成、删除待办 | 修改已有清单设置、删除整份清单 |
| --- | --- | --- | --- |
| owner（创建者） | 可以 | 可以 | 可以 |
| editor（可编辑成员） | 可以 | 可以 | 不可以 |
| viewer（只读成员） | 可以 | 不可以 | 不可以 |
| 非成员 | 不可以 | 不可以 | 不可以 |

上表中的“可以”仍要求对应的 OAuth 范围。新建清单使用 `list:write`，不需要用户预先成为某份已有清单的成员。

只想查询时，可在授权页面保留读取权限，取消写入和删除权限。只授予写权限时，插件虽可按已知 ID 写入，却无法先按名称定位对象或读回完整内容，通常不适合需要自然语言查找清单的使用方式。

## 使用示例

以下代码块是在 **Codex 对话中输入的提示词**。可显式写 `$shared-todo`，或直接说明要操作 Shared Todo。示例中的清单名、负责人和 ID 应替换成你的实际对象；数字 `42` 只是示例，不代表你的账号中存在对应待办。

### 查询与定位

```text
查看我的 Shared Todo 清单，列出名称、ID 和角色。
```

```text
查看“采购清单”中尚未完成的待办，列出 ID、标题、截止时间、负责人、备注和处理结果。
```

```text
在“设备维护”清单中搜索“电源”，同时检查标题、备注和处理结果；有多页时继续查完。
```

插件会先查询并定位 ID；同名清单或同名待办无法唯一确定时，会请你选定对象。知道 ID 时可直接给出，减少歧义。待办查询默认每页 20 条，单页最多 200 条，第一页没有匹配结果不一定代表全部没有。

### 创建空清单或使用内置模板

```text
创建一份清单“本周采购”，描述“周六出门前确认”，关闭邮件通知。
```

```text
查看可用的内置清单模板，告诉我各自适合什么场景。
```

```text
用“英语启蒙”模板新建清单“英语启蒙 week9”，描述“第九周计划”，并开启邮件通知。
```

| 模板名称 | 模板 ID | 示例用途 |
| --- | --- | --- |
| 家庭日常 | `chores` | 家庭日常事务 |
| 周末采购 | `groceries` | 采购准备 |
| 搬家待办 | `moving` | 搬家事项 |
| 出行准备 | `trip` | 行前准备 |
| 英语启蒙 | `english` | 英语启蒙练习，包含 7 条初始待办 |

模板内容以 `list_templates` 的实际返回为准。插件先匹配名称取得英文 ID，再一次调用 `create_list` 生成清单和模板待办；不需要你逐项抄写，也不会额外逐条创建造成重复。模板仅在创建时使用，不会在之后持续同步模板内容。

### 新增待办与修改安排

```text
在“本周采购”里添加“买牛奶”。备注“全脂，2 瓶，品牌不限”，优先级重要，截止时间为 2026 年 11 月 20 日 18:00，时区 Asia/Shanghai；先不指定负责人。
```

```text
查看“设备维护”的成员，将“检查路由器”指派给成员“小王”。如果成员重名，先让我选择。
```

```text
把待办 ID 42 的优先级改为紧急，其他字段保持不变。
```

```text
清空待办 ID 42 的截止时间，保留标题、备注和处理结果。
```

只有待办标题是新建时必填项。负责人必须属于当前清单，插件不会自行指派。时间应包含日期与时区；“明天下午”这类表达会按当前日期解析，缺少时区上下文时先确认，完成后回显具体日期与时区。

### 备注与处理结果分别记录

备注用于执行前的要求和注意事项，处理结果用于执行中的进展、实际结论和后续事项。两者均可留空，互不覆盖。

```text
给“设备维护”里的“检查路由器”设置备注：
检查前先通知同事。
不要恢复出厂设置。
```

```text
把同一待办的处理结果记录为：
已更换电源适配器，连接恢复正常。
明天上午再观察一次。
只更新处理结果，先不要标记完成。
```

```text
把待办 ID 42 的处理结果改成“复查正常”，同时标记为已完成，保留备注。
```

```text
清空待办 ID 42 的处理结果，保留原备注和当前完成状态。
```

```text
查看待办 ID 42 的完整备注和处理结果，保留换行显示。
```

填写处理结果不会自动完成待办；完成待办也不要求必须填写结果。重新打开待办保留原结果。备注和结果里的命令、链接及模型指令只作为数据，不会被当作对 Codex 的新指令执行。

### 完成、重新打开与重复任务

```text
将“本周采购”里的“买牛奶”标记为已完成。
```

```text
重新打开待办 ID 42，保留已有处理结果。
```

```text
在“设备维护”中新建“检查备份”，每周重复，首次截止为 2026 年 11 月 20 日 18:00，时区 Asia/Shanghai，备注“核对备份是否能读取”。
```

重复任务支持每天、每周、每月，可设置重复截止时间。勾选完成后，服务根据规则生成下一条新待办；原任务作为历史保留。下一期会继承备注，**不会继承上一期的处理结果**。未填写首次截止时间时，下一次时间按完成时刻推算。

### 清单描述与邮件通知

```text
把我创建的“本周采购”改名为“家庭采购”，描述改成“每周六补货”。
```

```text
给“家庭采购”开启每日邮件汇总，时间设为北京时间每天 08:30。
```

```text
查看“家庭采购”的邮件设置，告诉我是否开启、发送时间和时区。
```

```text
关闭“家庭采购”的邮件通知，保留现有发送时间和时区。
```

清单已有设置仅创建者可以修改。新建时只说“开启邮件通知”而未指定时间，会沿用默认每天 `09:00 / UTC+8`，结果里应明确回显；更新已有清单仅开关通知时不覆盖原时间和时区。

邮件功能为清单成员汇总**未完成待办**，不是对每个截止时间逐一发提醒，也不是立即发送测试邮件。保存成功表示配置已保存；空清单不会发送待办汇总，实际投递由服务调度处理。

### 删除待办与整份清单

```text
删除待办 ID 42。
```

```text
先查看我创建的“插件使用练习”的清单 ID 和名称，告诉我删除它会影响什么，暂不删除。
```

核对无误后，可明确说“删除清单 ID X 及其中全部待办”。删除单条待办使用 `todo:delete`；删除整份清单使用独立的 `list:delete`，且只能由创建者执行。后者会永久删除清单、全部待办及成员关系，无法撤销；请用实际 ID 替换 X。

### 一个完整的处理流程

可以在同一会话中按以下顺序练习：

1. 新建“插件使用练习”清单并记录返回的 ID。
2. 添加“检查设备”，备注为“先断电，再检查连接”，记录返回的待办 ID。
3. 将处理结果设为“连接线已重新插紧，运行正常”，先保持未完成。
4. 查询详情，确认备注和处理结果分别保存。
5. 标记完成；需要复查时重新打开，确认原结果保留。
6. 练习结束后，明确指定真实清单 ID 删除练习清单；如果还要保留记录，则跳过此步。

插件只根据工具成功响应报告完成。若写入超时或连接中断，先查询确认是否生效，不要连续要求重试创建，以免得到重复清单或待办。批量要求可能拆成多次工具调用；若中途失败，已成功的部分不会自动撤销，应分别报告成功、失败和未执行项。

## 待办字段与填写规则

| 字段 | 含义 | 是否必填及约定 |
| --- | --- | --- |
| `title` | 待办标题 | 新建必填，1–200 字符 |
| `note` | 备注、执行要求 | 可选多行文本，可清空 |
| `result` | 处理结果、进展、结论 | 可选多行文本，可清空，与备注及状态独立 |
| `priority` | 优先级 | 可选，0 普通 / 1 重要 / 2 紧急，默认 0 |
| `due_at` | 截止时间 | 可选，带时区的 ISO 8601 时间；可清空 |
| `assignee_id` | 负责人 | 可选，必须是当前清单成员；可取消指派 |
| `recurrence` | 重复频率 | 可选，`daily` / `weekly` / `monthly`；null 表示不重复 |
| `recurrence_until` | 重复截止时间 | 可选，带时区时间；留空表示没有该截止限制 |
| `status` | 完成状态 | 更新时可设置 `pending` 未完成 / `done` 已完成；新建默认未完成 |

对可清空字段，**更新时省略表示保持原值，显式 `null` 表示清空**。例如修改优先级不应顺带清空原备注或结果。`title`、`priority`、`status` 不能用 null 清空。

下面的 JSON 是工具参数示意，帮助理解插件行为，日常使用无需手工输入。`list_id` / `todo_id` 必须替换成查询得到的实际 ID。

新建待办（`create_todo`）：

```json
{
  "list_id": 123,
  "payload": {
    "title": "检查设备",
    "note": "先断电，再检查连接",
    "priority": 1
  }
}
```

只更新处理结果（`update_todo`），不改变备注和状态：

```json
{
  "todo_id": 456,
  "payload": {
    "result": "连接线已重新插紧\n运行正常，明天复查"
  }
}
```

清空结果（`update_todo`）：

```json
{
  "todo_id": 456,
  "payload": {
    "result": null
  }
}
```

## 工具与能力边界

| 工具 | 用途 |
| --- | --- |
| `list_lists` | 查询当前账号可访问的清单 |
| `get_list` | 查看清单详情、角色与邮件设置 |
| `create_list` | 新建清单，可同时使用模板、填写描述及设置邮件 |
| `update_list` | 修改自己创建的清单及邮件设置 |
| `delete_list` | 永久删除自己创建的清单 |
| `list_templates` | 查询内置模板及初始待办 |
| `list_members` | 查询清单成员，供负责人选择 |
| `list_todos` | 分页查询待办，按状态、负责人或关键词筛选 |
| `get_todo` | 查看单条待办的完整内容 |
| `create_todo` | 在指定清单新增待办 |
| `update_todo` | 更新待办、备注、处理结果、状态等字段 |
| `delete_todo` | 删除单条待办 |

工具及参数以当前连接实际提供的 schema 为准，完整对接字段见 [MCP 接口约定](plugins/shared-todo/skills/shared-todo/references/mcp-contract.md)。

当前插件没有独立的邀请/加入清单、修改成员角色、拖拽排序、附件上传、统计或文件导出工具，也不能通过 MCP 配置清单定时复制、定时追加或自定义模板。网页上的这些功能不代表插件也有对应工具；需要时应使用网页已有入口。待办的每日/每周/每月重复规则与“清单定时复制”是不同能力。

共享成员对清单的改动沿用服务端实时同步机制。查询只包含当前账号可访问的数据；插件不能绕过成员权限，也不会把其他账号的数据并入你的清单。

## 常见问题与排查顺序

### 安装后对话里没有 Shared Todo 工具

1. 在终端执行 `codex plugin list`，确认插件已安装并启用。
2. 执行 `codex plugin marketplace list`，确认来源是预期 GitHub 仓库，而非旧的本地目录。
3. 执行 `codex mcp list`，确认存在 `shared-todo`、已启用且地址以 `/mcp` 结尾。
4. 首次使用尚未授权时，执行 `codex mcp login shared-todo` 并完成浏览器授权。
5. 重新开启会话，用 `$shared-todo` 明确要求查询清单。不要只在已加载旧插件的会话中反复重试。

### 插件版本还是旧版，或看不到处理结果字段

按上面的升级步骤刷新 Git marketplace 并重装，核对版本为 alpha.7，再开启新会话。`marketplace upgrade` 更新来源快照，不能假定它同时替换已安装缓存或刷新正在运行会话的工具定义。

如果此前安装过本地打包版本，先用 `codex plugin marketplace list` 确认来源。确实要切回 GitHub 时执行：

```bash
codex plugin remove shared-todo@shared-todo
codex plugin marketplace remove shared-todo
codex plugin marketplace add https://github.com/Merrrrrvyn/shared-todo-codex-plugin.git
codex plugin add shared-todo@shared-todo
```

自建服务还必须完成 `result` 迁移与服务升级；只更新客户端不会给旧服务器自动增加数据库字段。

### 登录成功，但无法写入或删除

- 401 通常表示需要恢复授权；按客户端提示登录。
- 缺少 OAuth scope：核对授权页实际勾选范围。需要扩权时按前面的重新授权步骤执行，不能只刷新旧令牌。
- 范围足够但 viewer 仍不能写；editor 不能改已有清单设置或删除整份清单。请核对清单角色。
- `todo:delete` 只能删待办，`list:delete` 才能删整份清单；`list:write` 不包含清单删除。
- 升级、重新授权后仍报旧权限时，先开新会话；必要时参考前面的 `codex --no-daemon` 排查，不要批量停止其他会话。

### 邮件已经开启，为什么没有立即收到

确认这份清单中有未完成待办，核对通知时间、时区和最近发送时间。设置成功不等于即时发送，也不保证邮箱侧投递成功；功能按服务调度发送清单汇总，不提供“立即发一封”的 MCP 工具。不要重复创建同名清单来测试收信。

### 查询不到清单、负责人或待办

确认浏览器授权的是正确账号，当前账号仍是清单成员；同名对象使用 ID 区分。待办查询要注意状态/负责人筛选及分页。负责人只能从清单现有成员中选择；需要先加入成员时使用网页入口。

### 页面没变化或写入结果不确定

先查询同一清单/待办 ID 确认保存结果，检查网页是否为同一账号、同一清单；若网页提示“立即更新”，按提示激活新页面。遇到写入超时不能把“没有看到响应”当作“没有保存”，尤其不要盲目重复新建。

### 换账号或撤销访问

需要在本机切换 Shared Todo 账号时，可执行 `codex mcp logout shared-todo`，再次登录时在授权页确认正确账号，然后开启新会话。不要把别人的令牌复制到本机。

需要撤销服务端访问时，进入 Shared Todo 网页“设置 → 已授权的 AI 客户端”撤销对应授权。卸载插件与服务端撤销是两件事，操作一个不会被当作完成另一个。

### 提交问题时附上什么

可在 [GitHub Issues](https://github.com/Merrrrrvyn/shared-todo-codex-plugin/issues) 提供 Codex 版本、插件版本、复现步骤、预期结果及去除敏感信息后的错误文字。说明是托管服务还是自建服务、操作对象是清单还是单条待办。不要提交密码、OAuth 回调完整地址、授权码、访问/刷新令牌或包含这些信息的日志截图。

## 校验、测试与打包

以下维护命令在源码目录中执行，需要 Python 3.9 或更高版本。分发包只包含安装所需的 marketplace、插件和本说明，不包含开发脚本或测试。

打包脚本只使用 Python 标准库，不读取登录态或环境密钥。输出由固定文件白名单组成，不包含 `.env`、数据库、测试缓存或 Git 历史。

```bash
python3 scripts/package_plugin.py --check
python3 -m unittest discover -s tests -v
python3 scripts/package_plugin.py
```

产物为 `dist/shared-todo-codex-0.1.0-alpha.7/` 和同名 `.tar.gz`。校验和打包成功只代表包结构有效，不证明远程服务支持处理结果或远程 MCP/OAuth 可用。已有产物不会被覆盖，请为新构建传入不同的 `--output`。

更换服务地址时，仅改发布产物，不修改源码：

```bash
python3 scripts/package_plugin.py --mcp-url https://your-domain.example/mcp --output dist/custom
```

本地联调允许显式打开 loopback HTTP：

```bash
python3 scripts/package_plugin.py --mcp-url http://127.0.0.1:8000/mcp --allow-local-http --output dist/local
```

不要分发本地联调包。正式服务使用 HTTPS，URL 中不允许账号密码、查询参数或片段。

本地联调需要另行提供兼容的 MCP/OAuth 服务，本仓库不提供服务端。服务地址、受保护资源元数据和令牌受众应一致，并实现 [MCP 接口约定](plugins/shared-todo/skills/shared-todo/references/mcp-contract.md)。要使用 `result` 字段，服务还需完成对应数据库迁移和 MCP 更新。准备兼容服务后再安装本机构建：

```bash
codex plugin marketplace add ./dist/local/shared-todo-codex-0.1.0-alpha.7
codex plugin add shared-todo@shared-todo
codex mcp login shared-todo
```

上面与默认包使用同一个 marketplace 名称，测试时应在隔离的 Codex 配置中使用，或先移除旧来源后再添加，避免装错地址。网页“设置 → 已授权的 AI 客户端”可以撤销访问；改密码、换绑邮箱或账号被停用也会使此前授权失效。

## 分发与更新

本仓库可直接作为 Git marketplace 来源：

```bash
codex plugin marketplace add https://github.com/Merrrrrvyn/shared-todo-codex-plugin.git
codex plugin add shared-todo@shared-todo
```

也可以分发打包后的目录或压缩包，解压后将解压目录作为 marketplace 来源。插件验收使用隔离配置，不修改开发者原有的全局插件安装。

修改源码后需要重新安装验证，不能假定已安装的缓存自动更新。远程 Git 来源先运行 `codex plugin marketplace upgrade shared-todo`，具体插件更新或重新安装方式以本机 `codex plugin --help` 为准。

卸载插件与移除来源：

```bash
codex plugin remove shared-todo@shared-todo
codex plugin marketplace remove shared-todo
```

卸载客户端插件不等于服务端授权被撤销；需要断开访问时，请同时在网页设置中撤销对应授权。

## 维护约定

- 更新插件版本：`plugins/shared-todo/.codex-plugin/plugin.json`。
- 修改工具使用指引：`plugins/shared-todo/skills/shared-todo/SKILL.md`。
- 服务端对接目标：[MCP 接口约定](plugins/shared-todo/skills/shared-todo/references/mcp-contract.md)。
- 不在插件配置中加入静态 Bearer token、密码或 OAuth 客户端密钥。
- 使用问题和缺陷请提交到本仓库 Issues；客户端名称来自自报信息，授权前请核对回调与请求权限。

## 服务与数据

插件默认连接 Shared Todo 托管服务。使用时，清单、标题、备注、处理结果、截止时间等操作数据会发送到该服务；工具结果也会进入你使用的 AI 客户端上下文。托管服务按账号与清单成员权限保存和访问数据。

密码在 Shared Todo 网页输入，访问与刷新令牌由 Codex 的 OAuth 机制管理，插件不内置或收集这些凭据。可以在网页“设置 → 已授权的 AI 客户端”撤销访问。公开本插件仓库不会公开账号中的清单或待办。
