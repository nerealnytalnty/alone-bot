"""
database.py
------------
Простая, но потокобезопасная "база данных" на основе JSON-файла.

Почему JSON, а не SQLite? Для данного объёма данных (баланс монет +
список ID пользователей, получивших бонус) JSON полностью достаточен,
не требует дополнительных зависимостей и его легко читать глазами
при отладке. Всё обёрнуто в threading.Lock, потому что Flask
(keep-alive сервер) работает в отдельном потоке, а discord.py — в
основном асинхронном цикле. Без блокировки возможна гонка при
одновременной записи файла.

Структура database.json:
{
    "users": {
        "123456789012345678": {"coins": 150},
        ...
    },
    "bonus_received": ["123456789012345678", ...]
}
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any

import config

logger = logging.getLogger("alone-bot.database")

_LOCK = threading.Lock()

_DEFAULT_STRUCTURE: dict[str, Any] = {
    "users": {},
    "bonus_received": [],
}


class Database:
    """Обёртка над JSON-файлом с базовыми операциями чтения/записи."""

    def __init__(self, path: str = config.DB_PATH) -> None:
        self.path = path
        self._ensure_file()

    # ------------------------------------------------------------------ #
    # Внутренние helpers
    # ------------------------------------------------------------------ #
    def _ensure_file(self) -> None:
        """Создаёт файл базы данных, если он ещё не существует."""
        if not os.path.exists(self.path):
            with _LOCK:
                with open(self.path, "w", encoding="utf-8") as f:
                    json.dump(_DEFAULT_STRUCTURE, f, ensure_ascii=False, indent=4)
            logger.info("Создан новый файл базы данных: %s", self.path)

    def _read(self) -> dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as exc:
            logger.error("Ошибка чтения базы данных, восстанавливаю дефолт: %s", exc)
            return json.loads(json.dumps(_DEFAULT_STRUCTURE))

    def _write(self, data: dict[str, Any]) -> None:
        # Пишем во временный файл и заменяем — так исключаем повреждение
        # database.json при внезапном падении процесса посреди записи.
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(tmp_path, self.path)

    def _get_user(self, data: dict[str, Any], user_id: int) -> dict[str, Any]:
        uid = str(user_id)
        if uid not in data["users"]:
            data["users"][uid] = {"coins": config.STARTING_BALANCE}
        return data["users"][uid]

    # ------------------------------------------------------------------ #
    # Публичное API — монеты
    # ------------------------------------------------------------------ #
    def get_balance(self, user_id: int) -> int:
        with _LOCK:
            data = self._read()
            user = self._get_user(data, user_id)
            self._write(data)  # сохраняем на случай, если юзер создан впервые
            return int(user["coins"])

    def add_coins(self, user_id: int, amount: int) -> int:
        """Добавляет монеты (amount может быть отрицательным). Возвращает новый баланс."""
        with _LOCK:
            data = self._read()
            user = self._get_user(data, user_id)
            new_balance = max(0, int(user["coins"]) + amount)
            user["coins"] = new_balance
            self._write(data)
            return new_balance

    def set_balance(self, user_id: int, amount: int) -> int:
        with _LOCK:
            data = self._read()
            user = self._get_user(data, user_id)
            user["coins"] = max(0, amount)
            self._write(data)
            return user["coins"]

    def has_enough(self, user_id: int, amount: int) -> bool:
        return self.get_balance(user_id) >= amount

    # ------------------------------------------------------------------ #
    # Публичное API — бонус за первую роль
    # ------------------------------------------------------------------ #
    def has_received_bonus(self, user_id: int) -> bool:
        with _LOCK:
            data = self._read()
            return str(user_id) in data["bonus_received"]

    def mark_bonus_received(self, user_id: int) -> None:
        with _LOCK:
            data = self._read()
            uid = str(user_id)
            if uid not in data["bonus_received"]:
                data["bonus_received"].append(uid)
            self._write(data)


# Единый инстанс базы данных, импортируемый во всех модулях бота.
db = Database()
