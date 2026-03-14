# 🤖 AstrBot 自管理插件

让 Agent 拥有自我管理能力 —— 通过自然语言对话即可安装/卸载插件、管理 Skill、切换模型、控制工具、管理对话、查看人格、读写配置等。

## ✨ 功能概览

| 分类 | 工具 | 说明 |
|------|------|------|
| 📌 会话 | `get_session_umo` | 获取当前会话标识 (UMO) 🔒 |
| 🧩 插件 | `list_plugins` | 列出已安装插件 🔒 |
| | `install_plugin` | 通过 GitHub 仓库安装插件 🔒 |
| | `uninstall_plugin` | 卸载插件 🔒 |
| | `toggle_plugin` | 启用/禁用插件 🔒 |
| | `update_plugin` | 更新插件到最新版 🔒 |
| | `reload_plugin` | 热重载插件 🔒 |
| 📜 Skill | `list_skills` | 列出已安装 Skill 🔒 |
| | `toggle_skill` | 启用/禁用 Skill 🔒 |
| | `delete_skill` | 删除 Skill 🔒 |
| | `install_skill_from_url` | 通过 URL 下载并安装 Skill（支持 .md 和 .zip）🔒 |
| 🤖 模型 | `list_providers` | 列出所有 LLM 提供商 🔒 |
| | `get_current_provider` | 查看当前使用的模型 🔒 |
| | `switch_provider` | 切换当前会话的 LLM 提供商 🔒 |
| 🔧 工具 | `list_llm_tools` | 列出已注册的 function-calling 工具 🔒 |
| | `toggle_llm_tool` | 启用/禁用工具 🔒 |
| 🌐 MCP | `list_mcp_servers` | 列出 MCP 服务名称和运行状态概览 🔒 |
| | `get_mcp_server` | 查看指定 MCP 服务的详细配置、工具列表和错误日志 🔒 |
| | `add_mcp_server` | 添加新 MCP 服务（传入 JSON 配置，支持 SSE/Streamable HTTP/Stdio）🔒 |
| | `remove_mcp_server` | 删除 MCP 服务（自动断开并移除配置）🔒 |
| | `toggle_mcp_server` | 启用/禁用 MCP 服务 🔒 |
| 📝 指令 | `list_commands` | 列出所有已注册指令 🔒 |
| | `toggle_command` | 启用/禁用指令 🔒 |
| 💬 对话 | `list_conversations` | 列出对话记录 🔒 |
| | `clear_conversation` | 清除记忆（新建对话）🔒 |
| | `switch_conversation` | 切换对话 🔒 |
| | `delete_conversation` | 删除对话 🔒 |
| 🎭 人格 | `list_personas` | 列出所有人格 🔒 |
| | `get_current_persona` | 查看当前人格 🔒 |
| | `switch_persona` | 切换当前对话的人格 🔒 |
| 📨 消息 | `send_message` | 主动向指定会话发消息 🔒 |
| ⚙️ 配置 | `get_config` | 读取系统配置 🔒 |
| | `search_config` | 搜索配置项（模糊匹配 key 路径）🔒 |
| | `set_config` | 批量修改系统配置（Diff 式，支持一次设置多项）🔒 |
| 📊 状态 | `get_system_status` | 查看系统运行状态概览 🔒 |

> 🔒 所有工具均仅管理员可用。

## 📦 安装

将本插件目录放置到 AstrBot 的 `data/plugins/` 下，重启或在 WebUI 中重载插件即可。

```
data/plugins/astrbot_plugin_self_manager/
├── main.py
├── metadata.yaml
└── tools/
    ├── __init__.py
    ├── plugin_tools.py
    ├── skill_tools.py
    ├── provider_tools.py
    ├── llm_tool_tools.py
    ├── mcp_tools.py
    ├── command_tools.py
    ├── conversation_tools.py
    ├── persona_tools.py
    ├── session_tools.py
    ├── config_tools.py
    └── status_tools.py
```


## 💬 使用示例

直接用自然语言和 Agent 对话即可：

- **「帮我安装 https://github.com/xxx/astrbot_plugin_xxx 这个插件」**
  → Agent 调用 `install_plugin`

- **「现在用的什么模型？」**
  → Agent 调用 `get_session_umo` + `get_current_provider`

- **「帮我切换到 deepseek 提供商」**
  → Agent 调用 `switch_provider`

- **「把 xxx 插件关掉」**
  → Agent 调用 `toggle_plugin`

- **「清除对话记录」**
  → Agent 调用 `get_session_umo` + `clear_conversation`

- **「切换到猫娘人格」**
  → Agent 调用 `switch_persona`

- **「把唤醒前缀改成 !」**
  → Agent 调用 `search_config` 找到 key + `set_config` 批量修改

- **「查看系统状态」**
  → Agent 调用 `get_system_status`

- **「MCP 服务都有哪些？」**
  → Agent 调用 `list_mcp_servers`

- **「把 /help 指令关掉」**
  → Agent 调用 `list_commands` + `toggle_command`


## 🔒 安全设计

- **权限控制**：所有写操作（安装/卸载/启停/更新/修改配置等）都需要管理员权限
- **自卸载保护**：`uninstall_plugin` 会拒绝卸载自身，防止管理工具消失
- **配置回滚**：`set_config` 保存失败时会自动回滚到旧值
- **类型安全**：修改配置时根据原有值的类型自动推断新值类型
- **热保存**：`set_config` 修改后自动调用 `save_config()` 持久化到磁盘

## 📋 依赖

无额外依赖，仅使用 AstrBot 内置 API。
