"""
cogs/moderation.py
--------------------
Стандартные команды модерации. Права проверяются штатным механизмом
discord.py (app_commands.checks.has_permissions), плюс дополнительно
проверяем, что у самого бота есть нужные права (иначе Discord вернёт
Forbidden, и мы аккуратно это обрабатываем).
"""

from __future__ import annotations

import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import error_embed, success_embed

logger = logging.getLogger("alone-bot.moderation")


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------ #
    # /ban
    # ------------------------------------------------------------------ #
    @app_commands.command(name="ban", description="[Модерация] Забанить участника")
    @app_commands.describe(member="Участник, которого нужно забанить", reason="Причина бана")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Причина не указана",
    ) -> None:
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                embed=error_embed("Вы не можете забанить участника с ролью выше или равной вашей."),
                ephemeral=True,
            )
            return
        try:
            await member.ban(reason=f"{reason} | Модератор: {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("У бота недостаточно прав, чтобы забанить этого участника."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=success_embed("Участник забанен", f"{member.mention} забанен(а).\nПричина: {reason}")
        )
        logger.info("%s забанил %s (причина: %s)", interaction.user, member, reason)

    # ------------------------------------------------------------------ #
    # /kick
    # ------------------------------------------------------------------ #
    @app_commands.command(name="kick", description="[Модерация] Выгнать участника")
    @app_commands.describe(member="Участник, которого нужно выгнать", reason="Причина")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Причина не указана",
    ) -> None:
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                embed=error_embed("Вы не можете выгнать участника с ролью выше или равной вашей."),
                ephemeral=True,
            )
            return
        try:
            await member.kick(reason=f"{reason} | Модератор: {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("У бота недостаточно прав, чтобы выгнать этого участника."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=success_embed("Участник выгнан", f"{member.mention} выгнан(а).\nПричина: {reason}")
        )
        logger.info("%s выгнал %s (причина: %s)", interaction.user, member, reason)

    # ------------------------------------------------------------------ #
    # /mute (timeout)
    # ------------------------------------------------------------------ #
    @app_commands.command(name="mute", description="[Модерация] Замьютить участника (timeout)")
    @app_commands.describe(
        member="Участник, которого нужно замьютить",
        duration_minutes="Длительность мьюта в минутах (максимум 40320 = 28 дней)",
        reason="Причина",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration_minutes: app_commands.Range[int, 1, 40320],
        reason: str = "Причина не указана",
    ) -> None:
        until = discord.utils.utcnow() + datetime.timedelta(minutes=duration_minutes)
        try:
            await member.edit(timeout=until, reason=f"{reason} | Модератор: {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("У бота недостаточно прав, чтобы замьютить этого участника."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=success_embed(
                "Участник замьючен",
                f"{member.mention} замьючен(а) на **{duration_minutes}** мин.\nПричина: {reason}",
            )
        )
        logger.info("%s замьютил %s на %s минут", interaction.user, member, duration_minutes)

    # ------------------------------------------------------------------ #
    # /unmute
    # ------------------------------------------------------------------ #
    @app_commands.command(name="unmute", description="[Модерация] Снять мьют с участника")
    @app_commands.describe(member="Участник, с которого нужно снять мьют")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member) -> None:
        try:
            await member.edit(timeout=None, reason=f"Мьют снят модератором {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("У бота недостаточно прав, чтобы снять мьют с этого участника."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=success_embed("Мьют снят", f"С {member.mention} снят мьют.")
        )
        logger.info("%s снял мьют с %s", interaction.user, member)

    # ------------------------------------------------------------------ #
    # Единый обработчик ошибок прав доступа для всех команд этого cog'а
    # ------------------------------------------------------------------ #
    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=error_embed("У вас нет прав для использования этой команды."),
                ephemeral=True,
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                embed=error_embed("У бота недостаточно прав для выполнения этого действия."),
                ephemeral=True,
            )
        else:
            logger.exception("Неожиданная ошибка модерации", exc_info=error)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=error_embed("Произошла непредвиденная ошибка."), ephemeral=True
                )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
