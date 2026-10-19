
import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))

dp = Dispatcher()

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔎 Найти тиммейтов")],
        [KeyboardButton(text="👤 Моя анкета")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎮 Привет! Это CS2 TeamFinder.\n\n"
        "Здесь ты сможешь находить игроков для совместной игры в CS2.\n\n"
        "Выбери действие в меню ниже.",
        reply_markup=keyboard
    )


@dp.message(Command("help"))
@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def help_command(message: Message):
    await message.answer(
        "CS2 TeamFinder — бот для поиска тиммейтов.\n\n"
        "Это тестовая версия. Скоро добавим анкеты и поиск команды."
    )


@dp.message(lambda message: message.text == "🔎 Найти тиммейтов")
async def find_players(message: Message):
    await message.answer(
        "🔎 Поиск тиммейтов пока в разработке.\n"
        "Позже добавим выбор режима: FACEIT или Premier."
    )


@dp.message(lambda message: message.text == "👤 Моя анкета")
async def profile(message: Message):
    await message.answer(
        "👤 Анкеты пока не подключены.\n"
        "Позже можно будет указать ник, режим игры и рейтинг."
    )


@dp.message()
async def other_messages(message: Message):
    await message.answer("Выбери действие с помощью кнопок меню 👇", reply_markup=keyboard)


async def on_startup(bot: Bot):
    if not TOKEN or not WEBHOOK_URL:
        raise RuntimeError("Не заданы BOT_TOKEN или WEBHOOK_URL.")
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()


async def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN в настройках сервиса.")

    bot = Bot(token=TOKEN)
    app = web.Application()
    app["bot"] = bot

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.on_startup.append(lambda app: on_startup(bot))
    app.on_cleanup.append(lambda app: on_shutdown(bot))
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
