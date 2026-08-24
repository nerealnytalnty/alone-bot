"""
keep_alive.py
--------------
Render.com (бесплатный тариф "Web Service") усыпляет проект после
периода отсутствия HTTP-запросов, и, что важнее, требует, чтобы
приложение слушало сетевой порт — иначе деплой считается "неудачным"
(Render ждёт, что процесс забиндится на $PORT).

Discord-бот сам по себе ничего не слушает (он лишь держит исходящее
соединение с Discord через WebSocket), поэтому мы поднимаем
лёгкий Flask-сервер в ОТДЕЛЬНОМ потоке (threading.Thread), который
отвечает на любой GET-запрос. Это решает сразу две задачи:

1. Render видит открытый порт → деплой считается успешным.
2. Внешний сервис-пинговщик (например, UptimeRobot / cron-job.org),
   который раз в 5-10 минут дёргает URL нашего сервиса, не даёт
   Render усыпить контейнер по неактивности.

Поток Flask работает независимо от asyncio event loop'а discord.py,
поэтому они не мешают друг другу.
"""

import logging
import threading

from flask import Flask

import config

logger = logging.getLogger("alone-bot.keep_alive")

app = Flask(__name__)


@app.route("/")
def home() -> str:
    return f"✅ Бот сервера «{config.GUILD_NAME}» жив и работает!"


@app.route("/health")
def health() -> dict:
    return {"status": "ok", "guild": config.GUILD_NAME}


def _run() -> None:
    # use_reloader=False обязателен — иначе Flask попытается запустить
    # второй процесс и всё сломает, так как мы уже внутри треда.
    app.run(host="0.0.0.0", port=config.KEEP_ALIVE_PORT, use_reloader=False)


def keep_alive() -> None:
    """Запускает Flask-сервер в фоновом демоне-потоке."""
    thread = threading.Thread(target=_run, name="keep-alive-flask", daemon=True)
    thread.start()
    logger.info("Keep-alive сервер запущен на порту %s", config.KEEP_ALIVE_PORT)
