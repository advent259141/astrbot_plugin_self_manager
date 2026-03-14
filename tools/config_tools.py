"""系统配置管理工具：读取、搜索和修改 AstrBot 配置。"""

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


# ── 搜索配置 ──────────────────────────────────────────────


@dataclass
class SearchConfigTool(FunctionTool):
    name: str = "search_config"
    description: str = (
        "根据关键字搜索 AstrBot 的配置项。"
        "会在所有配置 key 路径中模糊匹配关键字，返回匹配的 key 路径及其当前值。"
        "适合在不确定配置项名称时使用。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "要搜索的关键字，不区分大小写",
                },
            },
            "required": ["keyword"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, keyword: str):
        if err := _check_admin(event):
            return err
        config = self._ctx.get_config()
        keyword_lower = keyword.lower()
        matches = []
        self._search_recursive(config, "", keyword_lower, matches)

        if not matches:
            return f"未找到与「{keyword}」匹配的配置项。"

        lines = []
        for key_path, value in matches[:30]:  # 限制输出数量
            val_str = json.dumps(value, ensure_ascii=False, default=str)
            if len(val_str) > 80:
                val_str = val_str[:77] + "..."
            lines.append(f"- {key_path} = {val_str}")

        result = f"搜索「{keyword}」匹配到 {len(matches)} 个配置项"
        if len(matches) > 30:
            result += f"（仅显示前 30 个）"
        result += "：\n" + "\n".join(lines)
        return result

    def _search_recursive(
        self, obj: dict, prefix: str, keyword: str, results: list
    ):
        """递归搜索配置树，匹配 key 名称。"""
        for k, v in obj.items():
            key_path = f"{prefix}.{k}" if prefix else k
            if keyword in key_path.lower():
                if isinstance(v, dict):
                    # 对字典只显示子 key 列表
                    results.append((key_path, f"{{...}} ({len(v)} 个子项)"))
                else:
                    results.append((key_path, v))
            if isinstance(v, dict):
                self._search_recursive(v, key_path, keyword, results)


# ── 修改配置（Diff 式） ──────────────────────────────────


@dataclass
class SetConfigTool(FunctionTool):
    name: str = "set_config"
    description: str = (
        "批量修改 AstrBot 的系统配置项并保存（Diff 式更新）。仅管理员可用。\n"
        "传入一个 JSON 对象，键为配置 key 路径（点号分隔），值为新值。\n"
        "示例: {\"provider_settings.wake_prefix\": \"/\", \"provider_settings.enable_wake\": true}\n"
        "⚠️ 谨慎使用：错误的配置可能导致 AstrBot 异常。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "changes": {
                    "type": "string",
                    "description": (
                        "JSON 对象字符串，键为 key 路径（点号分隔），值为新值。"
                        '例: {"provider_settings.wake_prefix": "/"}'
                    ),
                },
            },
            "required": ["changes"],
        }
    )
    _ctx: Context | None = None

    async def run(self, event: AstrMessageEvent, changes: str):
        if err := _check_admin(event):
            return err

        # 解析 diff
        try:
            diff = json.loads(changes)
        except json.JSONDecodeError as e:
            return f"❌ JSON 解析失败：{e}"

        if not isinstance(diff, dict) or not diff:
            return "❌ changes 必须是一个非空的 JSON 对象。"

        config = self._ctx.get_config()
        results = []
        rollbacks = []

        for key, raw_value in diff.items():
            parts = key.split(".")
            # 导航到父级
            target = config
            valid = True
            for part in parts[:-1]:
                if isinstance(target, dict) and part in target:
                    target = target[part]
                else:
                    results.append(f"⚠️ 「{key}」路径不存在，跳过。")
                    valid = False
                    break

            if not valid:
                continue

            last_key = parts[-1]
            if not isinstance(target, dict) or last_key not in target:
                results.append(f"⚠️ 「{key}」不存在，跳过。")
                continue

            old_value = target[last_key]
            try:
                new_value = self._parse_value(raw_value, old_value)
            except Exception as e:
                results.append(f"⚠️ 「{key}」值解析失败：{e}，跳过。")
                continue

            rollbacks.append((target, last_key, old_value))
            target[last_key] = new_value
            old_str = json.dumps(old_value, ensure_ascii=False, default=str)
            new_str = json.dumps(new_value, ensure_ascii=False, default=str)
            results.append(f"✅ 「{key}」: {old_str} → {new_str}")

        if not rollbacks:
            return "没有成功修改任何配置项。\n" + "\n".join(results)

        try:
            config.save_config()
            return "配置已保存。\n" + "\n".join(results)
        except Exception as e:
            # 回滚所有更改
            for target, last_key, old_value in rollbacks:
                target[last_key] = old_value
            return f"❌ 保存配置失败（已回滚）：{e}\n" + "\n".join(results)

    @staticmethod
    def _parse_value(raw, reference):
        """根据参考值的类型来解析新值。如果 raw 已经是正确类型则直接使用。"""
        # 如果 raw 已经是正确类型，直接返回
        if type(raw) is type(reference):
            return raw
        # 如果 raw 是字符串，按参考类型解析
        if isinstance(raw, str):
            if isinstance(reference, bool):
                return raw.strip().lower() in ("true", "1", "yes")
            if isinstance(reference, int):
                return int(raw)
            if isinstance(reference, float):
                return float(raw)
            if isinstance(reference, (list, dict)):
                return json.loads(raw)
            return raw
        # 数值类型之间的兼容转换
        if isinstance(reference, bool) and isinstance(raw, (int, float)):
            return bool(raw)
        if isinstance(reference, int) and isinstance(raw, (float, bool)):
            return int(raw)
        if isinstance(reference, float) and isinstance(raw, (int, bool)):
            return float(raw)
        # 其他情况直接赋值
        return raw
