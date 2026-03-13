"""AstrBot 自管理插件 —— 让 Agent 能够管理自身的插件、Skill、模型、工具、对话、人格、配置等。"""

from astrbot.api import logger
from astrbot.api.star import Context, Star

from .tools.config_tools import GetConfigTool, SetConfigTool
from .tools.conversation_tools import (
    ClearConversationTool,
    DeleteConversationTool,
    ListConversationsTool,
    SwitchConversationTool,
)
from .tools.llm_tool_tools import ListLLMToolsTool, ToggleLLMToolTool
from .tools.persona_tools import (
    GetCurrentPersonaTool,
    ListPersonasTool,
    SwitchPersonaTool,
)
from .tools.plugin_tools import (
    InstallPluginTool,
    ListPluginsTool,
    ReloadPluginTool,
    TogglePluginTool,
    UninstallPluginTool,
    UpdatePluginTool,
)
from .tools.provider_tools import (
    GetCurrentProviderTool,
    ListProvidersTool,
    SwitchProviderTool,
)
from .tools.session_tools import GetSessionUMOTool, SendMessageTool
from .tools.skill_tools import (
    DeleteSkillTool,
    InstallSkillFromUrlTool,
    ListSkillsTool,
    ToggleSkillTool,
)
from .tools.status_tools import GetSystemStatusTool


class SelfManagerPlugin(Star):
    """让 Agent 拥有自我管理能力的插件。

    注册 27 个 FunctionTool，涵盖：
    - 插件管理（安装/卸载/启停/更新/重载/列出）
    - Skill 管理（列出/启停/删除/安装）
    - 模型提供商管理（列出/查看当前/切换）
    - LLM 工具管理（列出/启停）
    - 对话管理（列出/清除/切换/删除）
    - 人格管理（列出/查看当前/切换当前对话人格）
    - 会话信息（获取 UMO）
    - 主动发消息
    - 系统配置读写
    - 系统状态查看
    """

    def __init__(self, context: Context) -> None:
        super().__init__(context)

        # 注册所有 FunctionTools
        self.context.add_llm_tools(
            # ── 会话信息 ──
            GetSessionUMOTool(),
            # ── 插件管理 ──
            ListPluginsTool(_ctx=context),
            InstallPluginTool(_ctx=context),
            UninstallPluginTool(_ctx=context),
            TogglePluginTool(_ctx=context),
            UpdatePluginTool(_ctx=context),
            ReloadPluginTool(_ctx=context),
            # ── Skill 管理 ──
            ListSkillsTool(),
            ToggleSkillTool(),
            DeleteSkillTool(),
            InstallSkillFromUrlTool(),
            # ── 模型提供商 ──
            ListProvidersTool(_ctx=context),
            GetCurrentProviderTool(_ctx=context),
            SwitchProviderTool(_ctx=context),
            # ── LLM 工具 ──
            ListLLMToolsTool(_ctx=context),
            ToggleLLMToolTool(_ctx=context),
            # ── 对话管理 ──
            ListConversationsTool(_ctx=context),
            ClearConversationTool(_ctx=context),
            SwitchConversationTool(_ctx=context),
            DeleteConversationTool(_ctx=context),
            # ── 人格管理 ──
            ListPersonasTool(_ctx=context),
            GetCurrentPersonaTool(_ctx=context),
            SwitchPersonaTool(_ctx=context),
            # ── 消息发送 ──
            SendMessageTool(_ctx=context),
            # ── 系统配置 ──
            GetConfigTool(_ctx=context),
            SetConfigTool(_ctx=context),
            # ── 系统状态 ──
            GetSystemStatusTool(_ctx=context),
        )

        logger.info("✨ 自管理插件已加载，共注册 27 个 FunctionTool。")

    async def terminate(self):
        """插件被卸载/停用时调用。"""
        logger.info("自管理插件已卸载。")

