
import os
import asyncio
import sqlite3

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))
DB_PATH = os.getenv("DB_PATH", "players.db")

dp = Dispatcher(storage=MemoryStorage())


class ProfileForm(StatesGroup):
    nickname = State()
    mode = State()
    rating = State()
    language = State()


keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔎 Найти тиммейтов")],
        [KeyboardButton(text="👤 Моя анкета")],
        [KeyboardButton(text="📝 Создать анкету")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True,
)


mode_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎯 Premier")],
        [KeyboardButton(text="🔥 FACEIT")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери режим игры",
)


language_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Русский"), KeyboardButton(text="English")],
        [KeyboardButton(text="Другой")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
)


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


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎮 Привет! Это CS2 TeamFinder!\n\n"
        "Создай анкету и подготовься к поиску тиммейтов.\n"
        "Выбирай действие в меню 👇",
        reply_markup=keyboard,
    )


@dp.message(Command("cancel"))
@dp.message(F.text == "❌ Отмена")
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Заполнение анкеты отменено.",
        reply_markup=keyboard,
    )


@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь")
async def help_command(message: Message):
    await message.answer(
        "🎮 CS2 TeamFinder — бот для поиска тиммейтов.\n\n"
        "📝 Создать анкету — заполнить свои данные.\n"
        "👤 Моя анкета — посмотреть сохранённую анкету.\n"
        "🔎 Найти тиммейтов — поиск добавим следующим обновлением.",
        reply_markup=keyboard,
    )


@dp.message(F.text == "📝 Создать анкету")
async def create_profile(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ProfileForm.nickname)
    await message.answer(
        "📝 Давай создадим твою анкету!\n\n"
        "Шаг 1 из 4\n"
        "🎮 Напиши свой игровой ник:",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(ProfileForm.nickname)
async def enter_nickname(message: Message, state: FSMContext):
    nickname = (message.text or "").strip()

    if not nickname or len(nickname) > 32:
        await message.answer("Ник должен содержать от 1 до 32 символов. Попробуй ещё раз:")
        return

    await state.update_data(nickname=nickname)
    await state.set_state(ProfileForm.mode)
    await message.answer(
        "Шаг 2 из 4\n"
        "🎯 Выбери режим игры:",
        reply_markup=mode_keyboard,
    )



@dp.message(ProfileForm.mode)
async def enter_mode(message: Message, state: FSMContext):
    raw_mode = (message.text or "").strip().lower()

    if raw_mode in (
        "🎯 premier",
        "premier",
        "премьер",
        "премьер режим",
        "премьерка",
    ):
        mode = "Premier"
    elif raw_mode in (
        "🔥 faceit",
        "faceit",
        "фейсит",
        "фейсит режим",
        "фейс",
    ):
        mode = "FACEIT"
    else:
        await message.answer(
            "🎮 Выбери режим игры кнопкой ниже:\n\n"
            "🎯 Premier — рейтинговый режим CS2\n"
            "🔥 FACEIT — игра на платформе FACEIT",
            reply_markup=mode_keyboard,
        )
        return

    await state.update_data(mode=mode)
    await state.set_state(ProfileForm.rating)
    await message.answer(
        f"✅ Режим выбран: {mode}\n\n"
        "Шаг 3 из 4 — рейтинг\n"
        "🏆 Напиши свой рейтинг.\n\n"
        "Например:\n"
        "• Premier: 12000\n"
        "• FACEIT: уровень 5 или 1500 Elo",
        reply_markup=ReplyKeyboardRemove(),
    )



@dp.message(ProfileForm.rating)
async def enter_rating(message: Message, state: FSMContext):
    rating = (message.text or "").strip()

    if not rating or len(rating) > 32:
        await message.answer("Укажи рейтинг длиной до 32 символов. Попробуй ещё раз:")
        return

    await state.update_data(rating=rating)
    await state.set_state(ProfileForm.language)
    await message.answer(
        "Шаг 4 из 4\n"
        "🌍 Выбери язык общения:",
        reply_markup=language_keyboard,
    )


@dp.message(ProfileForm.language)
async def enter_language(message: Message, state: FSMContext):
    language = (message.text or "").strip()

    if language not in ("Русский", "English", "Другой"):
        await message.answer(
            "Выбери язык с помощью кнопок ниже.",
            reply_markup=language_keyboard,
        )
        return

    data = await state.get_data()

    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            INSERT INTO players (user_id, nickname, mode, rating, language)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                nickname=excluded.nickname,
                mode=excluded.mode,
                rating=excluded.rating,
                language=excluded.language
            """,
            (
                message.from_user.id,
                data["nickname"],
                data["mode"],
                data["rating"],
                language,
            ),
        )

    await state.clear()
    await message.answer(
        "✅ Анкета успешно сохранена!\n\n"
        f"🎮 Ник: {data['nickname']}\n"
        f"🎯 Режим: {data['mode']}\n"
        f"🏆 Рейтинг: {data['rating']}\n"
        f"🌍 Язык: {language}\n\n"
        "Посмотреть анкету можно кнопкой «👤 Моя анкета».",
        reply_markup=keyboard,
    )


@dp.message(F.text == "👤 Моя анкета")
async def profile(message: Message):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            """
            SELECT nickname, mode, rating, language
            FROM players WHERE user_id = ?
            """,
            (message.from_user.id,),
        ).fetchone()

    if not row:
        await message.answer(
            "У тебя пока нет анкеты.\nНажми «📝 Создать анкету».",
            reply_markup=keyboard,
        )
        return

    await message.answer(
        "👤 Твоя анкета\n\n"
        f"🎮 Ник: {row[0]}\n"
        f"🎯 Режим: {row[1]}\n"
        f"🏆 Рейтинг: {row[2]}\n"
        f"🌍 Язык: {row[3]}",
        reply_markup=keyboard,
    )


@dp.message(F.text == "🔎 Найти тиммейтов")
async def find_players(message: Message):
    await message.answer(
        "🔎 Поиск тиммейтов — следующая задача!\n\n"
        "Сначала создай свою анкету, чтобы быть готовым к поиску.",
        reply_markup=keyboard,
    )


@dp.message()
async def other_messages(message: Message):
    await message.answer(
        "Выбери действие с помощью кнопок меню 👇",
        reply_markup=keyboard,
    )


async def on_startup(app):
    if not TOKEN or not WEBHOOK_URL:
        raise RuntimeError("Не заданы BOT_TOKEN или WEBHOOK_URL.")
    await app["bot"].set_webhook(
        f"{WEBHOOK_URL.rstrip('/')}/webhook"
    )


async def on_shutdown(app):
    await app["bot"].delete_webhook()


async def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN.")

    init_db()
    bot = Bot(token=TOKEN)
    app = web.Application()
    app["bot"] = bot

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path="/webhook")

    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_shutdown)
    app.router.add_get(
        "/",
        lambda request: web.Response(text="CS2 TeamFinder is running"),
    )

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
