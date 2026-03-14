"""指令管理工具：列出和启停已注册的指令。"""

from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.core.star.command_management import (
    list_commands,
    toggle_command,
)


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 列出指令 ──────────────────────────────────────────────


@dataclass
class ListCommandsTool(FunctionTool):
    name: str = "list_commands"
    description: str = (
        "列出所有已注册的指令，包括指令名、所属插件、启用状态和权限。"
    )
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    async def run(self, event: AstrMessageEvent):
        if err := _check_admin(event):
            return err
        commands = await list_commands()
        if not commands:
            return "没有注册任何指令。"

        lines = []
        for cmd in commands:
            enabled = "✅" if cmd.get("enabled", True) else "❌"
            name = cmd.get("effective_command", cmd.get("handler_name", "?"))
            plugin = cmd.get("plugin_display_name") or cmd.get("plugin", "")
            desc = cmd.get("description", "")
            perm = cmd.get("permission", "everyone")
            cmd_type = cmd.get("type", "command")

            type_tag = ""
            if cmd_type == "group":
                type_tag = " [组]"
            elif cmd_type == "sub_command":
                type_tag = " [子]"

            perm_tag = " 🔒" if perm == "admin" else ""

            line = f"- [{enabled}] /{name}{type_tag}{perm_tag}"
            if plugin:
                line += f" ({plugin})"
            if desc:
                short_desc = desc[:40] + "..." if len(desc) > 40 else desc
                line += f" — {short_desc}"
            lines.append(line)

            # 子指令
            for sub in cmd.get("sub_commands", []):
                sub_enabled = "✅" if sub.get("enabled", True) else "❌"
                sub_name = sub.get("effective_command", sub.get("handler_name", "?"))
                sub_desc = sub.get("description", "")
                sub_line = f"  - [{sub_enabled}] /{sub_name}"
                if sub_desc:
                    short = sub_desc[:30] + "..." if len(sub_desc) > 30 else sub_desc
                    sub_line += f" — {short}"
                lines.append(sub_line)

        return f"指令列表（共 {len(commands)} 个）：\n" + "\n".join(lines)


# ── 启停指令 ──────────────────────────────────────────────


@dataclass
class ToggleCommandTool(FunctionTool):
    name: str = "toggle_command"
    description: str = (
        "启用或禁用一个已注册的指令。"
        "需要提供指令的 handler_full_name（可通过 list_commands 获取）。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "handler_full_name": {
                    "type": "string",
                    "description": "指令的 handler_full_name 标识符",
                },
                "enable": {
                    "type": "boolean",
                    "description": "true=启用, false=禁用",
                },
            },
            "required": ["handler_full_name", "enable"],
        }
    )

    async def run(self, event: AstrMessageEvent, handler_full_name: str, enable: bool):
        if err := _check_admin(event):
            return err
        try:
            descriptor = await toggle_command(handler_full_name, enable)
            action = "启用" if enable else "禁用"
            cmd_name = descriptor.effective_command or descriptor.handler_name
            return f"✅ 已{action}指令「/{cmd_name}」。"
        except ValueError as e:
            return f"⚠️ {e}"
        except Exception as e:
            return f"❌ 操作失败：{e}"
