"""主动发消息工具 + 获取当前会话 UMO 工具。"""

from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent, MessageChain
from astrbot.api.star import Context


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 获取当前会话 UMO ──────────────────────────────────────


@dataclass
class GetSessionUMOTool(FunctionTool):
    name: str = "get_session_umo"
    description: str = (
        "获取当前消息会话的 unified_msg_origin (UMO)。"
        "UMO 是 AstrBot 中标识一个会话的唯一字符串，格式为 platform_name:message_type:session_id。"
        "许多管理工具要求提供 UMO 参数，你可以先调用此工具获取。"
    )
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    async def run(self, event: AstrMessageEvent):
        if err := _check_admin(event):
            return err
        umo = event.unified_msg_origin
        return (
            f"当前会话 UMO: {umo}\n"
            f"- 发送者 ID: {event.get_sender_id()}\n"
            f"- 发送者昵称: {event.get_sender_name()}\n"
            f"- 群组 ID: {event.get_group_id() or '无（私聊）'}\n"
            f"- 消息 ID: {event.message_obj.message_id}"
        )


# ── 主动发消息 ────────────────────────────────────────────


@dataclass
class SendMessageTool(FunctionTool):
    name: str = "send_message"
    description: str = (
        "向指定的会话主动发送一条文本消息。"
        "需要提供目标会话的 unified_msg_origin (UMO) 和消息内容。"
        "注意：QQ 官方接口不支持主动消息。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "target_umo": {
                    "type": "string",
                    "description": "目标会话的 unified_msg_origin",
                },
                "text": {
                    "type": "string",
                    "description": "要发送的文本消息内容",
                },
            },
            "required": ["target_umo", "text"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, target_umo: str, text: str):
        if err := _check_admin(event):
            return err
        try:
            chain = MessageChain().message(text)
            ok = await self._ctx.send_message(target_umo, chain)
            if ok:
                return f"✅ 消息已发送到 {target_umo}。"
            return f"⚠️ 未找到匹配的平台，消息未发送。目标 UMO: {target_umo}"
        except Exception as e:
            return f"❌ 发送失败：{e}"
