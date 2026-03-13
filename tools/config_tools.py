"""系统配置管理工具：读取和修改 AstrBot 配置。"""

import json
from dataclasses import dataclass, field

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 读取配置 ──────────────────────────────────────────────


@dataclass
class GetConfigTool(FunctionTool):
    name: str = "get_config"
    description: str = (
        "读取 AstrBot 的系统配置。"
        "可以指定配置的 key 路径（如 provider_settings.wake_prefix）来读取特定配置项。"
        "不指定 key 则返回顶级配置项的 key 列表。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "配置 key 路径，用点号分隔层级，如 'provider_settings.wake_prefix'。留空则列出顶级 key。",
                },
            },
            "required": [],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, key: str = ""):
        if err := _check_admin(event):
            return err
        config = self._ctx.get_config()
        if not key:
            keys = list(config.keys())
            return "AstrBot 配置顶级项：\n" + "\n".join(f"- {k}" for k in keys)
        parts = key.split(".")
        value = config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return f"⚠️ 配置项「{key}」不存在。"
        if isinstance(value, dict):
            # 只显示子 key 列表，避免输出过大
            sub_keys = list(value.keys())
            return f"配置项「{key}」的子项：\n" + "\n".join(f"- {k}" for k in sub_keys)
        return f"配置项「{key}」= {json.dumps(value, ensure_ascii=False, default=str)}"


# ── 修改配置 ──────────────────────────────────────────────


@dataclass
class SetConfigTool(FunctionTool):
    name: str = "set_config"
    description: str = (
        "修改 AstrBot 的系统配置项并保存。仅管理员可用。"
        "需要指定 key 路径和新的值。修改后会自动保存到磁盘。"
        "⚠️ 谨慎使用：错误的配置可能导致 AstrBot 异常。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "配置 key 路径，用点号分隔层级",
                },
                "value": {
                    "type": "string",
                    "description": "新的配置值。对于布尔值使用 true/false，数字直接使用数字，字符串直接填写。JSON 对象/数组请使用 JSON 格式。",
                },
            },
            "required": ["key", "value"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, key: str, value: str):
        if err := _check_admin(event):
            return err
        config = self._ctx.get_config()
        parts = key.split(".")
        # 导航到父级
        target = config
        for part in parts[:-1]:
            if isinstance(target, dict) and part in target:
                target = target[part]
            else:
                return f"⚠️ 配置路径「{key}」不存在。"
        last_key = parts[-1]
        if not isinstance(target, dict) or last_key not in target:
            return f"⚠️ 配置项「{key}」不存在。"
        # 类型推断
        old_value = target[last_key]
        try:
            new_value = self._parse_value(value, old_value)
        except Exception as e:
            return f"❌ 值解析失败：{e}"
        target[last_key] = new_value
        try:
            config.save_config()
            return (
                f"✅ 配置项「{key}」已修改。\n"
                f"- 旧值: {json.dumps(old_value, ensure_ascii=False, default=str)}\n"
                f"- 新值: {json.dumps(new_value, ensure_ascii=False, default=str)}"
            )
        except Exception as e:
            # 回滚
            target[last_key] = old_value
            return f"❌ 保存配置失败：{e}"

    @staticmethod
    def _parse_value(raw: str, reference):
        """根据参考值的类型来解析新值。"""
        if isinstance(reference, bool):
            return raw.strip().lower() in ("true", "1", "yes")
        if isinstance(reference, int):
            return int(raw)
        if isinstance(reference, float):
            return float(raw)
        if isinstance(reference, (list, dict)):
            return json.loads(raw)
        return raw
