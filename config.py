"""
config.py
---------
Центральное место для всех настроек бота.
Значения, которые могут отличаться от сервера к серверу (токен, порт),
берутся из переменных окружения (.env / Render Environment Variables).
Значения, специфичные для сервера "Alone" (ID ролей и т.д.), захардкожены,
как и было указано в ТЗ.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # подхватываем .env при локальном запуске

# --- Discord ---
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# --- Название сервера (используется в текстах embed'ов) ---
GUILD_NAME: str = "Alone"

# --- ID ролей, которым разрешено использовать /getcoin (админ/стафф) ---
ADMIN_ROLE_IDS: set[int] = {
    1541429748096307201,
    1541448711413174305,
}

# --- ID ролей, за ПЕРВОЕ получение которых выдаётся бонус в 30 монет ---
BONUS_ROLE_IDS: set[int] = {
    1541430133649449051,
    1541430309487255552,
}

BONUS_AMOUNT: int = 30

# --- Экономика ---
STARTING_BALANCE: int = 0

# --- Файл базы данных (JSON) ---
DB_PATH: str = os.getenv("DB_PATH", "database.json")

# --- Keep-Alive веб-сервер (Render) ---
KEEP_ALIVE_PORT: int = int(os.getenv("PORT", 8080))

# --- Цвета embed'ов (тема "Alone" — тёмная, минималистичная) ---
COLOR_MAIN = 0x2B2D31       # тёмно-серый, как фон Discord
COLOR_SUCCESS = 0x57F287    # зелёный
COLOR_ERROR = 0xED4245      # красный
COLOR_WARNING = 0xFEE75C    # жёлтый
COLOR_GOLD = 0xF1C40F       # для монет

# --- Товары магазина (пример, легко расширяется) ---
SHOP_ITEMS = [
    {"name": "🎨 Кастомная роль", "price": 500, "desc": "Уникальный цвет ника на сервере"},
    {"name": "🚀 Буст канала", "price": 300, "desc": "Продвижение вашего сообщения на 24ч"},
    {"name": "🎁 Мистический бокс", "price": 150, "desc": "Случайный приз от администрации"},
    {"name": "👑 VIP статус (7 дней)", "price": 1000, "desc": "Приоритетный доступ и бейдж VIP"},
]
