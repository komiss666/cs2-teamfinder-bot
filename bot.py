
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

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
        "Сейчас доступна тестовая версия. "
        "Следующим этапом добавим анкеты игроков и поиск команды."
    )


@dp.message(lambda message: message.text == "🔎 Найти тиммейтов")
async def find_players(message: Message):
    await message.answer(
        "🔎 Поиск тиммейтов пока находится в разработке.\n\n"
        "В следующей версии добавим выбор режима: FACEIT или Premier."
    )


@dp.message(lambda message: message.text == "👤 Моя анкета")
async def profile(message: Message):
    await message.answer(
        "👤 Анкеты пока не подключены.\n\n"
        "В следующей версии можно будет указать свой ник, "
        "режим игры, рейтинг и предпочтения."
    )


@dp.message()
async def other_messages(message: Message):
    await message.answer(
        "Выбери действие с помощью кнопок меню 👇",
        reply_markup=keyboard
    )


async def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN в настройках сервиса.")

    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
