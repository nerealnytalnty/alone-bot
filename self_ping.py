"""
self_ping.py
-------------
ВНУТРЕННИЙ сам-пинг: бот сам, изнутри, каждые 10 секунд стучится
на свой собственный /health эндпоинт (тот, что поднимает keep_alive.py).

Это отдельный, более надёжный уровень защиты от засыпания Render —
он не зависит от внешних сервисов (UptimeRobot и т.п.), которые могут
пинговать редко или вообще отваливаться.

URL берётся так:
1. Если задана переменная окружения SELF_URL — используется она.
2. Иначе пробуем RENDER_EXTERNAL_URL — Render сам прописывает эту
   переменную для каждого Web Service автоматически, вручную
   указывать не обязательно.
3. Если ни одна не найдена — self-ping просто не запускается (и это
   пишется в лог), но внешний Flask-сервер продолжает работать и
   отвечать на входящие пинги как раньше.
"""

from __future__ import annotations

import logging
import os

import aiohttp
from discord.ext import tasks

logger = logging.getLogger("alone-bot.self_ping")

SELF_URL = (os.getenv("SELF_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")

# Одна долгоживущая сессия вместо создания новой каждые 10 секунд —
# это заметно дешевле по ресурсам.
_session: aiohttp.ClientSession | None = None


@tasks.loop(seconds=10)
async def _self_ping_loop() -> None:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()

    url = f"{SELF_URL}/health"
    try:
        async with _session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            logger.debug("Self-ping OK: %s -> %s", url, resp.status)
    except Exception as exc:  # noqa: BLE001 — self-ping не должен ронять бота
        logger.warning("Self-ping не удался (%s): %s", url, exc)


@_self_ping_loop.before_loop
async def _before_loop() -> None:
    logger.info("Self-ping запускается: каждые 10 секунд на %s/health", SELF_URL)


def start_self_ping() -> None:
    """Запускает фоновый цикл само-пинга. Вызывать из async-контекста (setup_hook)."""
    if not SELF_URL:
        logger.warning(
            "SELF_URL / RENDER_EXTERNAL_URL не заданы — внутренний self-ping отключён. "
            "На Render переменная RENDER_EXTERNAL_URL подставляется автоматически, "
            "но если пингов всё равно нет — задайте SELF_URL вручную в Environment "
            "(например https://alone-bot.onrender.com)."
        )
        return

    if not _self_ping_loop.is_running():
        _self_ping_loop.start()


async def stop_self_ping() -> None:
    """Аккуратно останавливает цикл и закрывает HTTP-сессию (при выключении бота)."""
    if _self_ping_loop.is_running():
        _self_ping_loop.cancel()
    global _session
    if _session and not _session.closed:
        await _session.close()
