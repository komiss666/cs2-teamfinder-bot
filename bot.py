
import os
import asyncio
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))
DB_PATH = os.getenv("DB_PATH", "players.db")

dp = Dispatcher()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT NOT NULL,
                mode TEXT NOT NULL,
                rating TEXT NOT NULL,
                language TEXT NOT NULL
            )
        """)


keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔎 Найти тиммейтов")],
        [KeyboardButton(text="👤 Моя анкета")],
        [KeyboardButton(text="📝 Создать анкету")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎮 Привет! Это CS2 TeamFinder!\n\n"
        "Создай анкету и в будущем сможешь находить тиммейтов.\n"
        "Выбирай действие в меню 👇",
        reply_markup=keyboard
    )


@dp.message(Command("help"))
@dp.message(lambda m: m.text == "ℹ️ Помощь")
async def help_command(message: Message):
    await message.answer(
        "🎮 CS2 TeamFinder — поиск игроков для совместной игры.\n\n"
        "Создай анкету: ник, режим, рейтинг и язык.\n"
        "Следующий этап — полноценный поиск тиммейтов."
    )


@dp.message(lambda m: m.text == "📝 Создать анкету")
async def create_profile(message: Message):
    await message.answer(
        "📝 Создание анкеты\n\n"
        "Отправь одним сообщением данные в таком формате:\n\n"
        "Ник: YourNick\n"
        "Режим: Premier или FACEIT\n"
        "Рейтинг: например, 12000 или FACEIT 5\n"
        "Язык: русский\n\n"
        "Пример:\n"
        "Ник: Mika\n"
        "Режим: Premier\n"
        "Рейтинг: 12000\n"
        "Язык: русский\n\n"
        "⚠️ Не указывай пароль Steam или другие секретные данные."
    )


@dp.message(lambda m: m.text == "👤 Моя анкета")
async def profile(message: Message):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            "SELECT nickname, mode, rating, language "
            "FROM players WHERE user_id = ?",
            (message.from_user.id,)
        ).fetchone()

    if not row:
        await message.answer(
            "У тебя пока нет анкеты. Нажми «📝 Создать анкету».",
            reply_markup=keyboard
        )
        return

    await message.answer(
        f"👤 Твоя анкета\n\n"
        f"🎮 Ник: {row[0]}\n"
        f"🏆 Режим: {row[1]}\n"
        f"📊 Рейтинг: {row[2]}\n"
        f"🌍 Язык: {row[3]}",
        reply_markup=keyboard
    )


@dp.message(lambda m: m.text == "🔎 Найти тиммейтов")
async def find_players(message: Message):
    await message.answer(
        "🔎 Поиск игроков добавим следующим обновлением.\n"
        "Сначала создай свою анкету!"
    )


@dp.message()
async def save_profile(message: Message):
    if not message.text:
        await message.answer("Пожалуйста, отправь текст анкеты.")
        return

    fields = {}
    for line in message.text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()

    nickname = fields.get("ник")
    mode = fields.get("режим", "").capitalize()
    rating = fields.get("рейтинг")
    language = fields.get("язык")

    if not all([nickname, rating, language]) or mode not in ("Premier", "Faceit"):
        await message.answer(
            "Не удалось распознать анкету.\n\n"
            "Используй формат:\n"
            "Ник: Mika\n"
            "Режим: Premier или FACEIT\n"
            "Рейтинг: 12000\n"
            "Язык: русский"
        )
        return

    if len(nickname) > 32 or len(rating) > 32 or len(language) > 32:
        await message.answer("Слишком длинное поле. Сократи данные и попробуй снова.")
        return

    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO players (user_id, nickname, mode, rating, language) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "nickname=excluded.nickname, mode=excluded.mode, "
            "rating=excluded.rating, language=excluded.language",
            (message.from_user.id, nickname, mode, rating, language)
        )

    await message.answer(
        "✅ Анкета сохранена!\n\n"
        f"🎮 Ник: {nickname}\n"
        f"🏆 Режим: {mode}\n"
        f"📊 Рейтинг: {rating}\n"
        f"🌍 Язык: {language}\n\n"
        "Открой «👤 Моя анкета», чтобы проверить её.",
        reply_markup=keyboard
    )


async def on_startup(app):
    if not TOKEN or not WEBHOOK_URL:
        raise RuntimeError("Не заданы BOT_TOKEN или WEBHOOK_URL.")
    await app["bot"].set_webhook(f"{WEBHOOK_URL.rstrip('/')}/webhook")


async def on_shutdown(app):
    await app["bot"].delete_webhook()


async def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN.")

    init_db()
    bot = Bot(token=TOKEN)
    app = web.Application()
    app["bot"] = bot

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_shutdown)
    app.router.add_get("/", lambda request: web.Response(text="CS2 TeamFinder is running"))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
