"""系统状态工具：获取 AstrBot 运行状态概览。"""

import sys
import time
from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context
from astrbot.core.config.default import VERSION
from astrbot.core.star.star import star_registry


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None

_start_time = time.time()


# ── 获取系统状态 ──────────────────────────────────────────


@dataclass
class GetSystemStatusTool(FunctionTool):
    name: str = "get_system_status"
    description: str = (
        "获取 AstrBot 系统运行状态概览，包括版本号、运行时长、"
        "已加载的插件数/提供商数/工具数/平台数等信息。"
    )
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent):
        if err := _check_admin(event):
            return err
        # 运行时长
        uptime_secs = int(time.time() - _start_time)
        hours, remainder = divmod(uptime_secs, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            uptime_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            uptime_str = f"{minutes}m {seconds}s"
        else:
            uptime_str = f"{seconds}s"

        # 各模块数量
        num_plugins = len(star_registry)
        num_providers = len(self._ctx.get_all_providers())
        num_tools = len(self._ctx.get_llm_tool_manager().func_list)
        num_platforms = len(self._ctx.platform_manager.platform_insts)
        python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        lines = [
            f"🤖 **AstrBot v{VERSION}**",
            f"⏱️ 运行时长: {uptime_str}",
            f"🐍 Python: {python_ver}",
            f"🧩 已加载插件: {num_plugins}",
            f"🤖 LLM 提供商: {num_providers}",
            f"🔧 已注册工具: {num_tools}",
            f"📡 消息平台: {num_platforms}",
        ]
        return "\n".join(lines)
