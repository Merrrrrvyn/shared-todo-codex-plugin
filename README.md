# Shared Todo · Codex CLI 插件

预览版 `0.1.0-alpha.6`。插件包含共享待办 Skill 和远程 HTTP MCP 配置，可查询内置模板并一键创建含初始待办的清单，也可管理自有清单、邮件通知和待办。此仓库只分发插件与打包工具，不包含服务端或用户凭据。

**服务状态：MCP/OAuth 已于 2026-11-16 部署并完成公网验收。** 默认地址 `https://api.todolist.yymervyn.top/mcp` 提供 12 个清单、模板和待办工具、独立授权、权限隔离和撤销。请先在 `https://todolist.yymervyn.top` 注册或准备现有账号。

## 安装到 Codex CLI

以下命令按本机 `codex-cli 0.169.0` 的 CLI 核验。其他版本先检查 `codex plugin --help`。

直接添加公开 marketplace 并安装：

```bash
codex plugin marketplace add https://github.com/Merrrrrvyn/shared-todo-codex-plugin.git
codex plugin add shared-todo@shared-todo
codex mcp login shared-todo
```

按提示在浏览器登录 Shared Todo 账号并确认授权，然后重新打开 Codex 会话。通过 `codex plugin list` 查看安装结果。不应复制网页 token 作为临时绕过。

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

## 使用示例

服务接通并授权后，可显式使用 `$shared-todo`，或在自然语言中说明要操作 Shared Todo：

- 查看我的清单，以及采购清单里的未完成待办。
- 查看可用的清单模板。
- 用英语启蒙模板新建清单，描述 week9，打开邮件通知。
- 查看英语启蒙清单的详情，把汇总邮件时间改为北京时间每天 08:30。
- 关闭英语启蒙清单的邮件通知，保留现有发送时间。
- 在采购清单添加“买牛奶”，2026 年 11 月 20 日 18:00（Asia/Shanghai）截止。
- 为待办“买牛奶”添加备注“全脂，买 2 瓶；品牌不限”。
- 把待办 42 的优先级设为紧急。
- 将待办 42 标记完成；或将它重新打开。
- 删除待办 42。
- 删除清单 ID 42 及其中全部待办。

插件会定位清单和待办 ID，处理重名与分页，只回报工具确认成功的操作。不会将待办备注中的文字当作操作指令。

删除清单调用 `delete_list`，会永久删除该清单及其中全部待办和成员关系，无法撤销。它与删除单条待办是两个工具、两项独立权限；请明确指定目标清单，只有创建者可以执行。

创建清单时可在一次请求中同时传名称、描述、邮件设置及模板 ID。使用模板前，插件会从 `list_templates` 取得准确的英文 ID；内置模板包括家庭日常、周末采购、搬家待办、出行准备和英语启蒙，其中英语启蒙模板含 7 条初始待办。模板初始待办由服务随清单一起生成，不要再逐条创建。只要求开启邮件通知而未指定时间时，新清单沿用默认每天 `09:00 / UTC+8`，结果会明确回显；更新已有清单仅开关通知时保留原时间。汇总针对清单成员和未完成待办，配置保存成功不代表邮件已经发出，空清单不会发送待办汇总。

## 校验、测试与打包

以下维护命令在源码目录中执行，需要 Python 3.9 或更高版本。分发包只包含安装所需的 marketplace、插件和本说明，不包含开发脚本或测试。

打包脚本只使用 Python 标准库，不读取登录态或环境密钥。输出由固定文件白名单组成，不包含 `.env`、数据库、测试缓存或 Git 历史。

```bash
python3 scripts/package_plugin.py --check
python3 -m unittest discover -s tests -v
python3 scripts/package_plugin.py
```

产物为 `dist/shared-todo-codex-0.1.0-alpha.6/` 和同名 `.tar.gz`。校验和打包成功只代表包结构有效，不证明远程服务可用。已有产物不会被覆盖，请为新构建传入不同的 `--output`。

更换服务地址时，仅改发布产物，不修改源码：

```bash
python3 scripts/package_plugin.py --mcp-url https://your-domain.example/mcp --output dist/custom
```

本地联调允许显式打开 loopback HTTP：

```bash
python3 scripts/package_plugin.py --mcp-url http://127.0.0.1:8000/mcp --allow-local-http --output dist/local
```

不要分发本地联调包。正式服务使用 HTTPS，URL 中不允许账号密码、查询参数或片段。

本地联调需要另行提供兼容的 MCP/OAuth 服务，本仓库不提供服务端。服务地址、受保护资源元数据和令牌受众应一致，并实现 [MCP 接口约定](plugins/shared-todo/skills/shared-todo/references/mcp-contract.md)。准备服务后再安装本机构建：

```bash
codex plugin marketplace add ./dist/local/shared-todo-codex-0.1.0-alpha.6
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

插件默认连接 Shared Todo 托管服务。使用时，清单、标题、备注、截止时间等操作数据会发送到该服务；工具结果也会进入你使用的 AI 客户端上下文。托管服务按账号与清单成员权限保存和访问数据。

密码在 Shared Todo 网页输入，访问与刷新令牌由 Codex 的 OAuth 机制管理，插件不内置或收集这些凭据。可以在网页“设置 → 已授权的 AI 客户端”撤销访问。公开本插件仓库不会公开账号中的清单或待办。
