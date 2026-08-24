"""
utils.py
--------
Общие вспомогательные функции: билдеры embed'ов и кастомные проверки
(checks) для slash-команд, чтобы не дублировать код в каждом cog'е.
"""

from __future__ import annotations

import discord
from discord import app_commands

import config


def build_embed(
    title: str,
    description: str = "",
    color: int = config.COLOR_MAIN,
) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=f"Сервер «{config.GUILD_NAME}»")
    return embed


def error_embed(description: str) -> discord.Embed:
    return build_embed("❌ Ошибка", description, color=config.COLOR_ERROR)


def success_embed(title: str, description: str = "") -> discord.Embed:
    return build_embed(f"✅ {title}", description, color=config.COLOR_SUCCESS)


class NotAdminError(app_commands.CheckFailure):
    """Кастомное исключение для команд, доступных только админ/стафф-ролям."""


def is_admin_role():
    """
    Кастомный decorator-check для app_commands.
    Пропускает выполнение команды, только если у автора есть хотя бы
    одна из ролей, перечисленных в config.ADMIN_ROLE_IDS.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            raise NotAdminError("Команда доступна только на сервере.")

        member_role_ids = {role.id for role in interaction.user.roles}
        if member_role_ids.isdisjoint(config.ADMIN_ROLE_IDS):
            raise NotAdminError(
                "У вас нет прав для использования этой команды. "
                "Она доступна только администрации/стаффу."
            )
        return True

    return app_commands.check(predicate)
