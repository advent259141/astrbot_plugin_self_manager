"""Skill 管理工具：列出、启停、删除、从 URL 安装 Skill。"""

import os
import tempfile
from dataclasses import dataclass, field

import aiohttp

from astrbot.api import FunctionTool
from astrbot.api.event import AstrMessageEvent
from astrbot.core.skills.skill_manager import SkillManager


def _check_admin(event: AstrMessageEvent) -> str | None:
    if not event.is_admin():
        return "错误：仅管理员可执行此操作。"
    return None


# ── 列出 Skills ───────────────────────────────────────────


@dataclass
class ListSkillsTool(FunctionTool):
    name: str = "list_skills"
    description: str = "列出当前已安装的所有 AstrBot Skills（Agent 指令包），包括名称、描述、启用状态。"
    parameters: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    async def run(self, event: AstrMessageEvent):
        if err := _check_admin(event):
            return err
        mgr = SkillManager()
        skills = mgr.list_skills(active_only=False)
        if not skills:
            return "没有安装任何 Skill。"
        lines = []
        for s in skills:
            status = "✅启用" if s.active else "❌禁用"
            desc = s.description or "无描述"
            lines.append(f"- [{status}] {s.name}: {desc}")
        return "\n".join(lines)


# ── 启停 Skill ────────────────────────────────────────────


@dataclass
class ToggleSkillTool(FunctionTool):
    name: str = "toggle_skill"
    description: str = "启用或禁用一个 AstrBot Skill。仅管理员可用。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Skill 名称",
                },
                "enable": {
                    "type": "boolean",
                    "description": "true=启用, false=禁用",
                },
            },
            "required": ["skill_name", "enable"],
        }
    )

    async def run(self, event: AstrMessageEvent, skill_name: str, enable: bool):
        if err := _check_admin(event):
            return err
        mgr = SkillManager()
        try:
            mgr.set_skill_active(skill_name, enable)
            action = "启用" if enable else "禁用"
            return f"✅ 已{action} Skill「{skill_name}」。"
        except Exception as e:
            return f"❌ 操作失败：{e}"


# ── 删除 Skill ────────────────────────────────────────────


@dataclass
class DeleteSkillTool(FunctionTool):
    name: str = "delete_skill"
    description: str = "删除一个已安装的 AstrBot Skill。仅管理员可用。"
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "要删除的 Skill 名称",
                },
            },
            "required": ["skill_name"],
        }
    )

    async def run(self, event: AstrMessageEvent, skill_name: str):
        if err := _check_admin(event):
            return err
        mgr = SkillManager()
        try:
            mgr.delete_skill(skill_name)
            return f"✅ Skill「{skill_name}」已删除。"
        except Exception as e:
            return f"❌ 删除失败：{e}"


# ── 通过 URL 安装 Skill ──────────────────────────────────


def _extract_skill_name_from_frontmatter(text: str) -> str | None:
    """从 SKILL.md 的 YAML frontmatter 中提取 name 字段。"""
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None
    for line in lines[1:end_idx]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() == "name":
            return value.strip().strip("\"'")
    return None


def _guess_skill_name_from_url(url: str) -> str:
    """从 URL 路径中推断 Skill 名称。"""
    from urllib.parse import urlparse
    path = urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    # 去掉文件名（如 SKILL.md 或 skill.md），取其上一级目录名
    if parts:
        last = parts[-1].lower()
        if last.endswith(".md") or last.endswith(".zip"):
            parts = parts[:-1]
    if parts:
        name = parts[-1]
        # 清理名称，只保留合法字符
        import re
        name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        if name:
            return name
    return "downloaded_skill"


@dataclass
class InstallSkillFromUrlTool(FunctionTool):
    name: str = "install_skill_from_url"
    description: str = (
        "通过 URL 下载并安装一个 Skill。仅管理员可用。"
        "支持两种 URL 格式：\n"
        "1. 直接指向 SKILL.md 文件的 URL（如 https://example.com/skill.md）—— 会直接下载并创建 Skill 目录\n"
        "2. 指向 zip 压缩包的 URL —— 会下载 zip 并解压安装\n"
        "可选提供 skill_name 来指定 Skill 名称，否则自动从文件内容或 URL 推断。"
    )
    parameters: dict = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Skill 的下载地址，可以是 .md 文件或 .zip 压缩包的 URL",
                },
                "skill_name": {
                    "type": "string",
                    "description": "可选，指定 Skill 名称。不提供则自动从文件 frontmatter 或 URL 推断。",
                },
            },
            "required": ["url"],
        }
    )

    async def run(self, event: AstrMessageEvent, url: str, skill_name: str = ""):
        if err := _check_admin(event):
            return err

        try:
            # 下载内容
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    if resp.status != 200:
                        return f"❌ 下载失败：HTTP {resp.status}"
                    content_bytes = await resp.read()
                    content_type = resp.headers.get("Content-Type", "")
        except Exception as e:
            return f"❌ 下载失败：{e}"

        is_zip = (
            url.lower().rstrip("/").endswith(".zip")
            or "zip" in content_type.lower()
            or content_bytes[:4] == b"PK\x03\x04"  # zip magic bytes
        )

        if is_zip:
            return await self._install_from_zip(content_bytes, url)
        else:
            return await self._install_from_md(content_bytes, url, skill_name)

    async def _install_from_zip(self, content_bytes: bytes, url: str) -> str:
        """从 zip 内容安装 Skill。"""
        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip")
            os.close(tmp_fd)
            with open(tmp_path, "wb") as f:
                f.write(content_bytes)
            mgr = SkillManager()
            name = mgr.install_skill_from_zip(tmp_path, overwrite=True)
            return f"✅ Skill「{name}」安装成功（来源: {url}）"
        except Exception as e:
            return f"❌ 安装失败：{e}"
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    async def _install_from_md(
        self, content_bytes: bytes, url: str, skill_name: str
    ) -> str:
        """从直接下载的 SKILL.md 内容安装 Skill。"""
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                return "❌ 文件编码无法识别，请确保是 UTF-8 编码的 SKILL.md。"

        # 确定 Skill 名称
        if not skill_name:
            skill_name = _extract_skill_name_from_frontmatter(text) or ""
        if not skill_name:
            skill_name = _guess_skill_name_from_url(url)

        # 名称合法性检查
        import re
        if not re.match(r"^[A-Za-z0-9._-]+$", skill_name):
            skill_name = re.sub(r"[^A-Za-z0-9._-]", "_", skill_name)

        # 创建 Skill 目录并写入 SKILL.md
        mgr = SkillManager()
        skill_dir = os.path.join(mgr.skills_root, skill_name)
        os.makedirs(skill_dir, exist_ok=True)
        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        with open(skill_md_path, "w", encoding="utf-8") as f:
            f.write(text)

        return (
            f"✅ Skill「{skill_name}」安装成功！\n"
            f"- 来源: {url}\n"
            f"- 路径: {skill_dir}"
        )

