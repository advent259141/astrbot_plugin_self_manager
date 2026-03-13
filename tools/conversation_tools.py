"""对话管理工具：列出对话、清除当前对话、切换对话、删除对话。"""

from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 列出对话 ──────────────────────────────────────────────


@dataclass
class ListConversationsTool(FunctionTool):
    name: str = "list_conversations"
    description: str = (
        "列出指定会话来源的所有 LLM 对话记录，包括对话 ID 和标题。"
    )
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
        conv_mgr = self._ctx.conversation_manager
        convs = await conv_mgr.get_conversations(umo)
        if not convs:
            return "该会话没有任何对话记录。"
        curr_id = await conv_mgr.get_curr_conversation_id(umo)
        lines = []
        for c in convs:
            marker = "👉" if c.cid == curr_id else "  "
            title = c.title or "无标题"
            lines.append(f"{marker} [{c.cid[:8]}...] {title}")
        return f"当前对话 ID: {curr_id or '无'}\n\n" + "\n".join(lines)


# ── 清除当前对话（新建对话） ──────────────────────────────


@dataclass
class ClearConversationTool(FunctionTool):
    name: str = "clear_conversation"
    description: str = (
        "清除当前对话的历史记录，创建一个新的空白对话并自动切换过去。相当于重置 AI 记忆。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "umo": {
                    "type": "string",
                    "description": "会话的 unified_msg_origin",
                },
            },
            "required": ["umo"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, umo: str):
        if err := _check_admin(event):
            return err
        conv_mgr = self._ctx.conversation_manager
        try:
            new_cid = await conv_mgr.new_conversation(umo)
            return f"✅ 已创建新对话并切换，新对话 ID: {new_cid}"
        except Exception as e:
            return f"❌ 操作失败：{e}"


# ── 切换对话 ──────────────────────────────────────────────


@dataclass
class SwitchConversationTool(FunctionTool):
    name: str = "switch_conversation"
    description: str = "切换到指定的对话。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "umo": {
                    "type": "string",
                    "description": "会话的 unified_msg_origin",
                },
                "conversation_id": {
                    "type": "string",
                    "description": "要切换到的对话 ID",
                },
            },
            "required": ["umo", "conversation_id"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, umo: str, conversation_id: str):
        if err := _check_admin(event):
            return err
        conv_mgr = self._ctx.conversation_manager
        try:
            await conv_mgr.switch_conversation(umo, conversation_id)
            return f"✅ 已切换到对话 {conversation_id}。"
        except Exception as e:
            return f"❌ 切换失败：{e}"


# ── 删除对话 ──────────────────────────────────────────────


@dataclass
class DeleteConversationTool(FunctionTool):
    name: str = "delete_conversation"
    description: str = "删除一个指定的对话。如果不指定 conversation_id 则删除当前对话。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "umo": {
                    "type": "string",
                    "description": "会话的 unified_msg_origin",
                },
                "conversation_id": {
                    "type": "string",
                    "description": "要删除的对话 ID，不提供则删除当前对话",
                },
            },
            "required": ["umo"],
        }
    )
    _ctx: Context | None = None

    async def run(
        self,
        event: AstrMessageEvent,
        umo: str,
        conversation_id: str = "",
    ):
        if err := _check_admin(event):
            return err
        conv_mgr = self._ctx.conversation_manager
        try:
            await conv_mgr.delete_conversation(umo, conversation_id or None)
            target = conversation_id or "当前对话"
            return f"✅ 已删除对话 {target}。"
        except Exception as e:
            return f"❌ 删除失败：{e}"
