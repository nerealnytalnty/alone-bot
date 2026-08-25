"""
cogs/economy.py
-----------------
Экономика сервера: магазин, баланс, выдача монет админами и рулетка.
"""

from __future__ import annotations

import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

import config
from database import db
from utils import build_embed, error_embed, success_embed, is_admin_role, NotAdminError

logger = logging.getLogger("alone-bot.economy")


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------ #
    # /shop
    # ------------------------------------------------------------------ #
    @app_commands.command(name="shop", description="Открыть магазин сервера Alone")
    async def shop(self, interaction: discord.Interaction) -> None:
        embed = build_embed(
            title="🛒 Магазин сервера «Alone»",
            description=(
                "Обменивай заработанные монеты на эксклюзивные награды.\n"
                "Используй `/coin`, чтобы проверить свой баланс."
            ),
            color=config.COLOR_GOLD,
        )
        for item in config.SHOP_ITEMS:
            embed.add_field(
                name=f"{item['name']} — {item['price']} 🪙",
                value=item["desc"],
                inline=False,
            )

        if config.REMOVABLE_ROLES:
            roles_text = "\n".join(
                f"• **{info['name']}** — {info['price']} 🪙"
                for info in config.REMOVABLE_ROLES.values()
            )
            embed.add_field(
                name="🗑️ Снять роль с себя",
                value=f"{roles_text}\nПокупка: `/removerole`",
                inline=False,
            )

        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else discord.utils.MISSING)
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------ #
    # /coin
    # ------------------------------------------------------------------ #
    @app_commands.command(name="coin", description="Показать текущий баланс монет")
    async def coin(self, interaction: discord.Interaction) -> None:
        balance = db.get_balance(interaction.user.id)
        embed = build_embed(
            title="🪙 Баланс",
            description=f"{interaction.user.mention}, у вас **{balance}** монет.",
            color=config.COLOR_GOLD,
        )
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------ #
    # /getcoin  (только админ/стафф роли)
    # ------------------------------------------------------------------ #
    @app_commands.command(name="getcoin", description="[Админ] Выдать монеты пользователю")
    @app_commands.describe(member="Кому выдать монеты", amount="Сколько монет выдать")
    @is_admin_role()
    async def getcoin(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
    ) -> None:
        if amount <= 0:
            await interaction.response.send_message(
                embed=error_embed("Количество монет должно быть положительным числом."),
                ephemeral=True,
            )
            return

        new_balance = db.add_coins(member.id, amount)
        embed = success_embed(
            "Монеты выданы",
            f"{member.mention} получил(а) **{amount}** 🪙.\n"
            f"Новый баланс: **{new_balance}** 🪙.",
        )
        await interaction.response.send_message(embed=embed)
        logger.info("%s выдал %s монет пользователю %s", interaction.user, amount, member)

    @getcoin.error
    async def getcoin_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, NotAdminError):
            await interaction.response.send_message(embed=error_embed(str(error)), ephemeral=True)
        else:
            logger.exception("Неожиданная ошибка в /getcoin", exc_info=error)
            await interaction.response.send_message(
                embed=error_embed("Произошла непредвиденная ошибка."), ephemeral=True
            )

    # ------------------------------------------------------------------ #
    # /roulet
    # ------------------------------------------------------------------ #
    @app_commands.command(name="roulet", description="Сыграть в рулетку: Чёрный или Красный")
    @app_commands.describe(bet="Ставка в монетах")
    async def roulet(self, interaction: discord.Interaction, bet: int) -> None:
        if bet <= 0:
            await interaction.response.send_message(
                embed=error_embed("Ставка должна быть положительным числом."),
                ephemeral=True,
            )
            return

        balance = db.get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.send_message(
                embed=error_embed(
                    f"Недостаточно монет для такой ставки.\n"
                    f"Ваш баланс: **{balance}** 🪙, ставка: **{bet}** 🪙."
                ),
                ephemeral=True,
            )
            return

        # 50/50 — Чёрный или Красный
        result = random.choice(["black", "red"])

        if result == "red":
            new_balance = db.add_coins(interaction.user.id, bet)  # выигрыш = +bet (итого 2x)
            embed = build_embed(
                title="🔴 Выпал Красный!",
                description=(
                    f"Поздравляем, {interaction.user.mention}! Вы выиграли **{bet * 2}** 🪙 "
                    f"(ставка удвоена).\nНовый баланс: **{new_balance}** 🪙."
                ),
                color=config.COLOR_SUCCESS,
            )
        else:
            new_balance = db.add_coins(interaction.user.id, -bet)
            embed = build_embed(
                title="⚫ Выпал Чёрный",
                description=(
                    f"Не повезло, {interaction.user.mention}. Вы проиграли **{bet}** 🪙.\n"
                    f"Новый баланс: **{new_balance}** 🪙."
                ),
                color=config.COLOR_ERROR,
            )

        embed.set_footer(text=f"Сервер «{config.GUILD_NAME}» • Рулетка")
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------ #
    # /removerole — покупка снятия роли с себя (товар магазина)
    # ------------------------------------------------------------------ #
    @app_commands.command(name="removerole", description="Купить в магазине снятие роли с себя")
    @app_commands.describe(role="Какую роль снять")
    @app_commands.choices(
        role=[
            app_commands.Choice(name=f"{info['name']} ({info['price']} 🪙)", value=str(role_id))
            for role_id, info in config.REMOVABLE_ROLES.items()
        ]
    )
    async def removerole(
        self,
        interaction: discord.Interaction,
        role: app_commands.Choice[str],
    ) -> None:
        role_id = int(role.value)
        info = config.REMOVABLE_ROLES[role_id]
        price = info["price"]

        discord_role = interaction.guild.get_role(role_id) if interaction.guild else None
        if discord_role is None:
            await interaction.response.send_message(
                embed=error_embed("Эта роль больше не существует на сервере."),
                ephemeral=True,
            )
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or discord_role not in member.roles:
            await interaction.response.send_message(
                embed=error_embed(f"У вас нет роли **{discord_role.name}**, снимать нечего."),
                ephemeral=True,
            )
            return

        balance = db.get_balance(member.id)
        if balance < price:
            await interaction.response.send_message(
                embed=error_embed(
                    f"Недостаточно монет.\nНужно: **{price}** 🪙, у вас: **{balance}** 🪙."
                ),
                ephemeral=True,
            )
            return

        try:
            await member.remove_roles(discord_role, reason=f"Покупка в магазине: /removerole ({member})")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed(
                    "У бота недостаточно прав, чтобы снять эту роль. "
                    "Роль бота должна быть выше снимаемой роли в иерархии сервера."
                ),
                ephemeral=True,
            )
            return

        new_balance = db.add_coins(member.id, -price)
        embed = success_embed(
            "Роль снята",
            f"С вас списано **{price}** 🪙 и снята роль **{discord_role.name}**.\n"
            f"Новый баланс: **{new_balance}** 🪙.",
        )
        await interaction.response.send_message(embed=embed)
        logger.info("%s купил(а) снятие роли %s за %s монет", member, discord_role, price)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))
