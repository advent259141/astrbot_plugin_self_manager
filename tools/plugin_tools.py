"""插件管理工具：安装、卸载、启停、更新、列出、重载插件。"""

from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context
from astrbot.core.star.star_manager import PluginManager


def _get_star_mgr(ctx: Context) -> PluginManager:
    mgr = ctx._star_manager
    if mgr is None:
        raise RuntimeError("插件管理器尚未初始化。")
    return mgr


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 列出插件 ──────────────────────────────────────────────


@dataclass
class ListPluginsTool(FunctionTool):
    name: str = "list_plugins"
    description: str = "列出当前已安装的所有 AstrBot 插件，包括名称、版本、作者、描述和启用状态。"
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent):
        if err := _check_admin(event):
            return err
        plugins = self._ctx.get_all_stars()
        if not plugins:
            return "没有加载任何插件。"
        lines = []
        for p in plugins:
            status = "✅启用" if p.activated else "❌禁用"
            lines.append(
                f"- [{status}] {p.name} v{p.version} by {p.author}: {p.desc}"
            )
        return "\n".join(lines)


# ── 安装插件 ──────────────────────────────────────────────


@dataclass
class InstallPluginTool(FunctionTool):
    name: str = "install_plugin"
    description: str = (
        "通过 GitHub 仓库地址安装一个 AstrBot 插件。仅管理员可用。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "repo_url": {
                    "type": "string",
                    "description": "插件的 GitHub 仓库地址，如 https://github.com/xxx/astrbot_plugin_xxx",
                },
            },
            "required": ["repo_url"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, repo_url: str):
        if err := _check_admin(event):
            return err
        star_mgr = _get_star_mgr(self._ctx)
        try:
            await star_mgr.install_plugin(repo_url)
            return f"✅ 插件安装成功：{repo_url}"
        except Exception as e:
            return f"❌ 插件安装失败：{e}"


# ── 卸载插件 ──────────────────────────────────────────────


@dataclass
class UninstallPluginTool(FunctionTool):
    name: str = "uninstall_plugin"
    description: str = "卸载一个已安装的 AstrBot 插件。仅管理员可用。注意：不能卸载自管理插件本身。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "plugin_name": {
                    "type": "string",
                    "description": "要卸载的插件名称",
                },
            },
            "required": ["plugin_name"],
        }
    )
    _ctx: Context | None = None
    _self_plugin_name: str = "astrbot_plugin_self_manager"

    async def run(self, event: AstrMessageEvent, plugin_name: str):
        if err := _check_admin(event):
            return err
        if plugin_name == self._self_plugin_name:
            return "⚠️ 不能卸载自管理插件本身，这会导致管理工具全部消失。"
        star_mgr = _get_star_mgr(self._ctx)
        try:
            await star_mgr.uninstall_plugin(plugin_name)
            return f"✅ 插件 {plugin_name} 已卸载。"
        except Exception as e:
            return f"❌ 卸载失败：{e}"


# ── 启停插件 ──────────────────────────────────────────────


@dataclass
class TogglePluginTool(FunctionTool):
    name: str = "toggle_plugin"
    description: str = "启用或禁用一个 AstrBot 插件。仅管理员可用。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "plugin_name": {
                    "type": "string",
                    "description": "插件名称",
                },
                "enable": {
                    "type": "boolean",
                    "description": "true=启用, false=禁用",
                },
            },
            "required": ["plugin_name", "enable"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, plugin_name: str, enable: bool):
        if err := _check_admin(event):
            return err
        star_mgr = _get_star_mgr(self._ctx)
        try:
            if enable:
                await star_mgr.turn_on_plugin(plugin_name)
            else:
                await star_mgr.turn_off_plugin(plugin_name)
            action = "启用" if enable else "禁用"
            return f"✅ 已{action}插件 {plugin_name}。"
        except Exception as e:
            return f"❌ 操作失败：{e}"


# ── 更新插件 ──────────────────────────────────────────────


@dataclass
class UpdatePluginTool(FunctionTool):
    name: str = "update_plugin"
    description: str = "更新一个已安装的 AstrBot 插件到最新版本。仅管理员可用。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "plugin_name": {
                    "type": "string",
                    "description": "要更新的插件名称",
                },
            },
            "required": ["plugin_name"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, plugin_name: str):
        if err := _check_admin(event):
            return err
        star_mgr = _get_star_mgr(self._ctx)
        try:
            await star_mgr.update_plugin(plugin_name, proxy=None)
            await star_mgr.reload(plugin_name)
            return f"✅ 插件 {plugin_name} 已更新并重载。"
        except Exception as e:
            return f"❌ 更新失败：{e}"


# ── 重载插件 ──────────────────────────────────────────────


@dataclass
class ReloadPluginTool(FunctionTool):
    name: str = "reload_plugin"
    description: str = "重载一个已安装的 AstrBot 插件（不更新代码，只重新加载）。仅管理员可用。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "plugin_name": {
                    "type": "string",
                    "description": "要重载的插件名称，留空则重载全部",
                },
            },
            "required": [],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, plugin_name: str = ""):
        if err := _check_admin(event):
            return err
        star_mgr = _get_star_mgr(self._ctx)
        try:
            success, message = await star_mgr.reload(plugin_name or None)
            if success:
                target = plugin_name or "全部插件"
                return f"✅ {target} 重载成功。"
            return f"❌ 重载失败：{message}"
        except Exception as e:
            return f"❌ 重载失败：{e}"
