"""MCP 服务管理工具：列出、安装、卸载和启停 MCP 服务。"""

from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 列出 MCP 服务 ─────────────────────────────────────────


@dataclass
class ListMCPServersTool(FunctionTool):
    name: str = "list_mcp_servers"
    description: str = "列出所有已配置的 MCP 服务的名称和运行状态概览。如需查看详细信息请使用 get_mcp_server。"
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent):
        if err := _check_admin(event):
            return err
        tool_mgr = self._ctx.get_llm_tool_manager()
        config = tool_mgr.load_mcp_config()
        mcp_servers = config.get("mcpServers", {})

        if not mcp_servers:
            return "没有配置任何 MCP 服务。"

        runtime_view = tool_mgr.mcp_server_runtime_view
        lines = []
        for name, cfg in mcp_servers.items():
            if not isinstance(cfg, dict):
                continue
            active = cfg.get("active", True)
            running = name in runtime_view
            status = "🟢" if running else ("⚪" if not active else "🔴")
            lines.append(f"- {status} {name}")

        return f"MCP 服务（共 {len(lines)} 个）：\n" + "\n".join(lines)


# ── 查看 MCP 服务详情 ─────────────────────────────────────


@dataclass
class GetMCPServerTool(FunctionTool):
    name: str = "get_mcp_server"
    description: str = "查看指定 MCP 服务的详细信息，包括配置、提供的工具列表和错误日志。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "server_name": {
                    "type": "string",
                    "description": "MCP 服务名称",
                },
            },
            "required": ["server_name"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, server_name: str):
        if err := _check_admin(event):
            return err
        import json

        tool_mgr = self._ctx.get_llm_tool_manager()
        config = tool_mgr.load_mcp_config()
        mcp_servers = config.get("mcpServers", {})

        if server_name not in mcp_servers:
            return f"⚠️ 未找到名为「{server_name}」的 MCP 服务。"

        cfg = mcp_servers[server_name]
        if not isinstance(cfg, dict):
            return f"⚠️ 「{server_name}」的配置格式错误。"

        active = cfg.get("active", True)
        runtime_view = tool_mgr.mcp_server_runtime_view
        running = server_name in runtime_view
        status = "🟢 运行中" if running else ("⚪ 已停用" if not active else "🔴 未启动")

        # 基本信息
        cfg_display = {k: v for k, v in cfg.items() if k != "active"}
        lines = [
            f"**{server_name}** [{status}]",
            f"- 配置: {json.dumps(cfg_display, ensure_ascii=False)}",
        ]

        # 工具列表
        if running:
            client = runtime_view[server_name].client
            tool_names = [t.name for t in client.tools]
            lines.append(f"- 工具 ({len(tool_names)}): {', '.join(tool_names) if tool_names else '无'}")
            if client.server_errlogs:
                lines.append(f"- 错误日志: {client.server_errlogs[-3:]}")

        return "\n".join(lines)



# ── 添加 MCP 服务 ─────────────────────────────────────────


@dataclass
class AddMCPServerTool(FunctionTool):
    name: str = "add_mcp_server"
    description: str = (
        "添加并启用一个新的 MCP 服务。传入服务名称和完整的 JSON 配置。"
        "添加前会自动测试连接，测试通过后才会保存配置并启用。\n"
        "支持三种配置格式：\n"
        '1. SSE: {"transport": "sse", "url": "...", "headers": {}, "timeout": 5, "sse_read_timeout": 300}\n'
        '2. Streamable HTTP: {"transport": "streamable_http", "url": "...", "headers": {}, "timeout": 5, "sse_read_timeout": 300}\n'
        '3. Stdio: {"command": "python", "args": ["-m", "your_module"]}'
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "server_name": {
                    "type": "string",
                    "description": "MCP 服务名称（唯一标识）",
                },
                "config": {
                    "type": "string",
                    "description": "MCP 服务的完整 JSON 配置字符串",
                },
            },
            "required": ["server_name", "config"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, server_name: str, config: str):
        if err := _check_admin(event):
            return err

        import json

        try:
            server_cfg = json.loads(config)
        except json.JSONDecodeError as e:
            return f"❌ JSON 解析失败：{e}"

        if not isinstance(server_cfg, dict):
            return "❌ config 必须是一个 JSON 对象。"

        tool_mgr = self._ctx.get_llm_tool_manager()
        mcp_config = tool_mgr.load_mcp_config()

        if server_name in mcp_config.get("mcpServers", {}):
            return f"⚠️ 名为「{server_name}」的 MCP 服务已存在。"

        server_cfg["active"] = True

        # 测试连接
        try:
            tool_names = await tool_mgr.test_mcp_server_connection(server_cfg)
        except Exception as e:
            return f"❌ 连接测试失败：{e}"

        # 保存配置
        if "mcpServers" not in mcp_config:
            mcp_config["mcpServers"] = {}
        mcp_config["mcpServers"][server_name] = server_cfg
        if not tool_mgr.save_mcp_config(mcp_config):
            return "❌ 保存配置失败。"

        # 启用服务
        try:
            await tool_mgr.enable_mcp_server(server_name, server_cfg, timeout=30)
        except TimeoutError:
            mcp_config["mcpServers"].pop(server_name, None)
            tool_mgr.save_mcp_config(mcp_config)
            return f"❌ 启用 MCP 服务「{server_name}」超时，已回滚配置。"
        except Exception as e:
            mcp_config["mcpServers"].pop(server_name, None)
            tool_mgr.save_mcp_config(mcp_config)
            return f"❌ 启用失败（已回滚）：{e}"

        tools_str = ", ".join(tool_names) if tool_names else "无"
        cfg_summary = json.dumps(server_cfg, ensure_ascii=False)
        return (
            f"✅ 已添加并启用 MCP 服务「{server_name}」。\n"
            f"- 配置: {cfg_summary}\n"
            f"- 可用工具: {tools_str}"
        )


# ── 删除 MCP 服务 ─────────────────────────────────────────


@dataclass
class RemoveMCPServerTool(FunctionTool):
    name: str = "remove_mcp_server"
    description: str = "删除一个已配置的 MCP 服务。会自动断开连接并移除配置。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "server_name": {
                    "type": "string",
                    "description": "要删除的 MCP 服务名称",
                },
            },
            "required": ["server_name"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, server_name: str):
        if err := _check_admin(event):
            return err

        tool_mgr = self._ctx.get_llm_tool_manager()
        config = tool_mgr.load_mcp_config()
        mcp_servers = config.get("mcpServers", {})

        if server_name not in mcp_servers:
            return f"⚠️ 未找到名为「{server_name}」的 MCP 服务。"

        # 如果正在运行，先禁用
        if server_name in tool_mgr.mcp_server_runtime_view:
            try:
                await tool_mgr.disable_mcp_server(server_name, timeout=10)
            except TimeoutError:
                return f"❌ 断开 MCP 服务「{server_name}」超时。"
            except Exception as e:
                return f"❌ 断开连接失败：{e}"

        # 删除配置
        del config["mcpServers"][server_name]
        if tool_mgr.save_mcp_config(config):
            return f"✅ 已删除 MCP 服务「{server_name}」。"
        return "❌ 保存配置失败。"


# ── 启停 MCP 服务 ─────────────────────────────────────────


@dataclass
class ToggleMCPServerTool(FunctionTool):
    name: str = "toggle_mcp_server"
    description: str = (
        "启用或禁用一个已配置的 MCP 服务。"
        "启用时会初始化连接并加载工具，禁用时会断开连接并移除工具。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "server_name": {
                    "type": "string",
                    "description": "MCP 服务名称",
                },
                "enable": {
                    "type": "boolean",
                    "description": "true=启用, false=禁用",
                },
            },
            "required": ["server_name", "enable"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, server_name: str, enable: bool):
        if err := _check_admin(event):
            return err
        tool_mgr = self._ctx.get_llm_tool_manager()
        config = tool_mgr.load_mcp_config()
        mcp_servers = config.get("mcpServers", {})

        if server_name not in mcp_servers:
            return f"⚠️ 未找到名为「{server_name}」的 MCP 服务。"

        server_cfg = mcp_servers[server_name]
        if not isinstance(server_cfg, dict):
            return f"⚠️ 「{server_name}」的配置格式错误。"

        try:
            if enable:
                # 更新配置中的 active 字段
                server_cfg["active"] = True
                config["mcpServers"][server_name] = server_cfg
                tool_mgr.save_mcp_config(config)
                # 启动 MCP 服务
                await tool_mgr.enable_mcp_server(
                    server_name, server_cfg, timeout=30
                )
                return f"✅ 已启用 MCP 服务「{server_name}」。"
            else:
                # 禁用 MCP 服务
                server_cfg["active"] = False
                config["mcpServers"][server_name] = server_cfg
                tool_mgr.save_mcp_config(config)
                await tool_mgr.disable_mcp_server(server_name, timeout=10)
                return f"✅ 已禁用 MCP 服务「{server_name}」。"
        except TimeoutError:
            action = "启用" if enable else "禁用"
            return f"❌ {action} MCP 服务「{server_name}」超时。"
        except Exception as e:
            return f"❌ 操作失败：{e}"



