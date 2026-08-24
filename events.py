"""
cogs/events.py
----------------
Слушает on_member_update и выдаёт одноразовый бонус в 30 монет за
ПЕРВОЕ получение одной из ролей BONUS_ROLE_IDS.

Защита от эксплойта (снять роль -> надеть заново -> получить бонус
повторно) реализована через database.has_received_bonus /
mark_bonus_received: ID пользователя один раз попадает в список
"bonus_received" и больше оттуда не удаляется, даже если роль снята.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from database import db
from utils import build_embed

logger = logging.getLogger("alone-bot.events")


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        before_role_ids = {role.id for role in before.roles}
        after_role_ids = {role.id for role in after.roles}

        # Роли, которые появились ИМЕННО в этом обновлении
        newly_added = after_role_ids - before_role_ids
        relevant_new_roles = newly_added & config.BONUS_ROLE_IDS

        if not relevant_new_roles:
            return  # обновление не связано с нужными ролями

        if db.has_received_bonus(after.id):
            return  # бонус уже был выдан ранее — игнорируем (анти-эксплойт)

        db.mark_bonus_received(after.id)
        new_balance = db.add_coins(after.id, config.BONUS_AMOUNT)

        logger.info(
            "Выдан бонус за первую роль пользователю %s (+%s монет, баланс: %s)",
            after,
            config.BONUS_AMOUNT,
            new_balance,
        )

        # Пытаемся уведомить пользователя в личные сообщения.
        # Если у него закрыты ЛС — просто логируем и не роняем событие.
        try:
            embed = build_embed(
                title="🎉 Бонус за роль!",
                description=(
                    f"Вы впервые получили особую роль на сервере «{config.GUILD_NAME}» "
                    f"и заработали **{config.BONUS_AMOUNT}** 🪙!\n"
                    f"Текущий баланс: **{new_balance}** 🪙."
                ),
                color=config.COLOR_GOLD,
            )
            await after.send(embed=embed)
        except discord.Forbidden:
            logger.info("Не удалось отправить ЛС пользователю %s (закрыты ЛС)", after)
        except discord.HTTPException:
            logger.exception("Ошибка при отправке ЛС о бонусе пользователю %s", after)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
