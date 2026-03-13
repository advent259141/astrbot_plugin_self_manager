"""人格管理工具：列出所有人格、查看当前人格、切换当前对话人格。"""

from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 列出所有人格 ──────────────────────────────────────────


@dataclass
class ListPersonasTool(FunctionTool):
    name: str = "list_personas"
    description: str = "列出所有已配置的 AI 人格（Persona），包括 ID 和系统提示词摘要。"
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent):
        if err := _check_admin(event):
            return err
        persona_mgr = self._ctx.persona_manager
        personas = await persona_mgr.get_all_personas()
        if not personas:
            return "没有配置任何人格。"
        lines = []
        for p in personas:
            prompt_preview = (p.system_prompt or "")[:80]
            if len(p.system_prompt or "") > 80:
                prompt_preview += "..."
            lines.append(f"- **{p.persona_id}**: {prompt_preview}")
        return "\n".join(lines)


# ── 查看当前默认人格 ──────────────────────────────────────


@dataclass
class GetCurrentPersonaTool(FunctionTool):
    name: str = "get_current_persona"
    description: str = "查看当前会话正在使用的默认 AI 人格。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "umo": {
                    "type": "string",
                    "description": "会话的 unified_msg_origin，可通过 get_session_umo 工具获取",
                },
            },
            "required": ["umo"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, umo: str):
        if err := _check_admin(event):
            return err
        persona_mgr = self._ctx.persona_manager
        persona = await persona_mgr.get_default_persona_v3(umo=umo)
        if not persona:
            return "当前会话没有设置人格。"
        name = persona.get("name", "未知")
        prompt = persona.get("prompt", "无")
        prompt_preview = prompt[:200]
        if len(prompt) > 200:
            prompt_preview += "..."
        return f"当前人格: {name}\n系统提示词: {prompt_preview}"


# ── 切换当前对话的人格 ────────────────────────────────────


@dataclass
class SwitchPersonaTool(FunctionTool):
    name: str = "switch_persona"
    description: str = (
        "切换当前对话使用的 AI 人格。仅管理员可用。"
        "切换后当前对话将使用新人格进行回复。"
        "可通过 list_personas 查看所有可用的人格 ID。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "persona_id": {
                    "type": "string",
                    "description": "要切换到的人格 ID（名称），可通过 list_personas 查看",
                },
            },
            "required": ["persona_id"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, persona_id: str):
        if err := _check_admin(event):
            return err
        # 检查人格是否存在
        persona_mgr = self._ctx.persona_manager
        available = [p["name"] for p in persona_mgr.personas_v3]
        if persona_id not in available and persona_id != "default":
            return f"⚠️ 人格「{persona_id}」不存在。可用人格：{', '.join(available)}"
        # 更新当前对话的人格
        umo = event.unified_msg_origin
        conv_mgr = self._ctx.conversation_manager
        try:
            await conv_mgr.update_conversation_persona_id(umo, persona_id)
            return f"✅ 当前对话已切换到人格「{persona_id}」。"
        except Exception as e:
            return f"❌ 切换失败：{e}"


