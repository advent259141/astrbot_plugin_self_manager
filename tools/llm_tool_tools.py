"""LLM 工具管理：列出已注册的 function-calling 工具、启停工具。"""

from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 列出 LLM 工具 ────────────────────────────────────────


@dataclass
class ListLLMToolsTool(FunctionTool):
    name: str = "list_llm_tools"
    description: str = (
        "列出当前所有已注册的 LLM function-calling 工具，包括名称、描述和激活状态。"
    )
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent):
        if err := _check_admin(event):
            return err
        tool_mgr = self._ctx.get_llm_tool_manager()
        tools = tool_mgr.func_list
        if not tools:
            return "没有注册任何 LLM 工具。"
        lines = []
        for t in tools:
            active = "✅" if getattr(t, "active", True) else "❌"
            desc = t.description[:60] + "..." if len(t.description) > 60 else t.description
            lines.append(f"- [{active}] {t.name}: {desc}")
        return "\n".join(lines)


# ── 启停 LLM 工具 ────────────────────────────────────────


@dataclass
class ToggleLLMToolTool(FunctionTool):
    name: str = "toggle_llm_tool"
    description: str = "启用或禁用一个已注册的 LLM function-calling 工具。仅管理员可用。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "工具名称",
                },
                "enable": {
                    "type": "boolean",
                    "description": "true=启用, false=禁用",
                },
            },
            "required": ["tool_name", "enable"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, tool_name: str, enable: bool):
        if err := _check_admin(event):
            return err
        try:
            if enable:
                ok = self._ctx.activate_llm_tool(tool_name)
            else:
                ok = self._ctx.deactivate_llm_tool(tool_name)
            if ok:
                action = "启用" if enable else "禁用"
                return f"✅ 已{action} LLM 工具「{tool_name}」。"
            return f"⚠️ 未找到名为「{tool_name}」的工具。"
        except Exception as e:
            return f"❌ 操作失败：{e}"
