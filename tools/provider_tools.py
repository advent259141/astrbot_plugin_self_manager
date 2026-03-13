"""模型/提供商管理工具：列出所有提供商、查看当前使用的提供商、切换提供商。"""

from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context
from astrbot.core.provider.entities import ProviderType


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 列出所有提供商 ────────────────────────────────────────


@dataclass
class ListProvidersTool(FunctionTool):
    name: str = "list_providers"
    description: str = (
        "列出所有已配置的 LLM 提供商（模型），包括 ID、模型名称和适配器类型。"
    )
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent):
        if err := _check_admin(event):
            return err
        providers = self._ctx.get_all_providers()
        if not providers:
            return "没有配置任何 LLM 提供商。"
        lines = []
        for p in providers:
            meta = p.meta()
            lines.append(
                f"- ID: {meta.id} | 模型: {meta.model or '未指定'} | 适配器: {meta.type}"
            )
        return "\n".join(lines)


# ── 查看当前使用的提供商 ──────────────────────────────────


@dataclass
class GetCurrentProviderTool(FunctionTool):
    name: str = "get_current_provider"
    description: str = (
        "查看当前会话正在使用的 LLM 提供商（模型），需要提供 unified_msg_origin。"
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
        prov = self._ctx.get_using_provider(umo=umo)
        if not prov:
            return "当前会话没有设置 LLM 提供商。"
        meta = prov.meta()
        return (
            f"当前使用的提供商：\n"
            f"- ID: {meta.id}\n"
            f"- 模型: {meta.model or '未指定'}\n"
            f"- 适配器类型: {meta.type}"
        )


# ── 切换提供商 ────────────────────────────────────────────


@dataclass
class SwitchProviderTool(FunctionTool):
    name: str = "switch_provider"
    description: str = (
        "切换当前会话使用的 LLM 提供商（模型）。仅管理员可用。"
        "可通过 list_providers 查看所有可用的提供商 ID。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "provider_id": {
                    "type": "string",
                    "description": "要切换到的提供商 ID",
                },
            },
            "required": ["provider_id"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, provider_id: str):
        if err := _check_admin(event):
            return err
        umo = event.unified_msg_origin
        try:
            await self._ctx.provider_manager.set_provider(
                provider_id, ProviderType.CHAT_COMPLETION, umo
            )
            # 验证切换结果
            prov = self._ctx.get_using_provider(umo=umo)
            if prov and prov.meta().id == provider_id:
                meta = prov.meta()
                return (
                    f"✅ 已切换到提供商 {provider_id}。\n"
                    f"- 模型: {meta.model or '未指定'}\n"
                    f"- 适配器类型: {meta.type}"
                )
            return f"✅ 已设置提供商为 {provider_id}。"
        except ValueError as e:
            return f"❌ 切换失败：{e}"
        except Exception as e:
            return f"❌ 切换失败：{e}"
