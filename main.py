"""
main.py
--------
Точка входа. Инициализирует бота, подгружает cogs, поднимает
keep-alive веб-сервер и запускает бота.

Запуск: python main.py
"""

from __future__ import annotations

import asyncio
import logging
import sys

import discord
from discord.ext import commands

import config
from keep_alive import keep_alive

# ---------------------------------------------------------------------- #
# Логирование
# ---------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("alone-bot.main")

# ---------------------------------------------------------------------- #
# Intents
# ---------------------------------------------------------------------- #
# members=True ОБЯЗАТЕЛЕН для on_member_update (бонус за роль).
# Не забудьте включить "SERVER MEMBERS INTENT" в Discord Developer Portal!
intents = discord.Intents.default()
intents.members = True
intents.message_content = False  # бот работает только через slash-команды

COGS = (
    "cogs.economy",
    "cogs.moderation",
    "cogs.events",
)


class AloneBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        for extension in COGS:
            try:
                await self.load_extension(extension)
                logger.info("Загружен модуль: %s", extension)
            except Exception:
                logger.exception("Не удалось загрузить модуль %s", extension)

        # Синхронизация slash-команд с Discord API.
        try:
            synced = await self.tree.sync()
            logger.info("Синхронизировано %s slash-команд.", len(synced))
        except Exception:
            logger.exception("Ошибка синхронизации slash-команд")

    async def on_ready(self) -> None:
        logger.info("Бот запущен как %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"сервер «{config.GUILD_NAME}»",
            )
        )


bot = AloneBot()


def main() -> None:
    if not config.DISCORD_TOKEN:
        logger.critical(
            "Переменная окружения DISCORD_TOKEN не задана! "
            "Добавьте её в .env (локально) или в Environment на Render.com."
        )
        sys.exit(1)

    # Поднимаем Flask-сервер для Render Keep-Alive ДО запуска бота.
    keep_alive()

    try:
        bot.run(config.DISCORD_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.critical("Неверный DISCORD_TOKEN. Проверьте значение переменной окружения.")
        sys.exit(1)


if __name__ == "__main__":
    main()
