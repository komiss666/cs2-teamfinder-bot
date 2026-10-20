
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
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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
    premier_rating = State()
    faceit_elo = State()
    goals = State()
    microphone = State()
    behavior = State()
    country = State()


keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Создать анкету")],
        [KeyboardButton(text="👤 Моя анкета")],
        [KeyboardButton(text="🔎 Найти тиммейтов")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True,
)

mode_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎯 Premier")],
        [KeyboardButton(text="🔥 FACEIT")],
        [KeyboardButton(text="🎯 Premier + FACEIT")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
)

yes_no_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
)


goals_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📈 Поднять рейтинг")],
        [KeyboardButton(text="🤝 Постоянные тиммейты")],
        [KeyboardButton(text="🎉 Играть ради удовольствия")],
        [KeyboardButton(text="🏆 Собрать команду для турниров")],
        [KeyboardButton(text="✅ Готово")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери цели и нажми «Готово»",
)

def goals_inline_keyboard(selected=None):
    selected = selected or []
    options = [
        ("Поднять рейтинг", "goal_rating"),
        ("Постоянные тиммейты", "goal_teammates"),
        ("Играть ради удовольствия", "goal_fun"),
        ("Команда для турниров", "goal_tournament"),
    ]

    buttons = []
    for title, callback in options:
        mark = "☑️" if title in selected else "⬜"
        buttons.append([
            InlineKeyboardButton(
                text=f"{mark} {title}",
                callback_data=callback,
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="✅ Готово", callback_data="goals_done")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="selection_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

behavior_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Не токсичу")],
        [KeyboardButton(text="✅ Играю командно")],
        [KeyboardButton(text="✅ Не бросаю матчи")],
        [KeyboardButton(text="✅ Хочу развиваться")],
        [KeyboardButton(text="✅ Готов играть регулярно")],
        [KeyboardButton(text="✅ Готово")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
)
def behavior_inline_keyboard(selected=None):
    selected = selected or []
    options = [
        ("Не токсичу", "behavior_non_toxic"),
        ("Играю командно", "behavior_teamplay"),
        ("Не бросаю матчи", "behavior_no_abandon"),
        ("Хочу развиваться", "behavior_improve"),
        ("Готов играть регулярно", "behavior_regular"),
    ]

    buttons = []
    for title, callback in options:
        mark = "☑️" if title in selected else "⬜"
        buttons.append([
            InlineKeyboardButton(
                text=f"{mark} {title}",
                callback_data=callback,
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="✅ Готово", callback_data="behavior_done")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="selection_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

country_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇷🇺 Россия")],
        [KeyboardButton(text="🇧🇾 Беларусь")],
        [KeyboardButton(text="🇰🇿 Казахстан")],
        [KeyboardButton(text="🇺🇦 Украина")],
        [KeyboardButton(text="🇱🇻 Латвия")],
        [KeyboardButton(text="🌍 Другая страна")],
        [KeyboardButton(text="⏭ Пропустить")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери страну или пропусти",
)

def connect_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT NOT NULL,
                mode TEXT NOT NULL,
                premier_rating INTEGER,
                faceit_elo INTEGER,
                goals TEXT NOT NULL,
                microphone TEXT NOT NULL,
                behavior TEXT NOT NULL,
                country TEXT NOT NULL
            )
        """)


def get_player(user_id):
    with connect_db() as db:
        return db.execute(
            """SELECT nickname, mode, premier_rating, faceit_elo,
                      goals, microphone, behavior, country
               FROM players WHERE user_id = ?""",
            (user_id,),
        ).fetchone()


def save_player(user_id, data):
    with connect_db() as db:
        db.execute(
            """INSERT INTO players
               (user_id, nickname, mode, premier_rating, faceit_elo,
                goals, microphone, behavior, country)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                nickname=excluded.nickname,
                mode=excluded.mode,
                premier_rating=excluded.premier_rating,
                faceit_elo=excluded.faceit_elo,
                goals=excluded.goals,
                microphone=excluded.microphone,
                behavior=excluded.behavior,
                country=excluded.country""",
            (
                user_id,
                data["nickname"],
                data["mode"],
                data.get("premier_rating"),
                data.get("faceit_elo"),
                ", ".join(data["goals"]),
                data["microphone"],
                ", ".join(data["behavior"]),
                data["country"],
            ),
        )


def profile_text(row):
    nickname, mode, premier, faceit, goals, mic, behavior, country = row
    lines = [
        "👤 Твоя анкета",
        "",
        f"🎮 Ник: {nickname}",
        f"🎯 Режимы: {mode}",
    ]
    if "Premier" in mode:
        lines.append(f"🏆 Premier: {premier}")
    if "FACEIT" in mode:
        lines.append(f"🔥 FACEIT Elo: {faceit}")
    lines.extend([
        f"🎯 Цели: {goals}",
        f"🎙 Микрофон: {mic}",
        f"🤝 Стиль игры: {behavior}",
        f"🌍 Страна/регион: {country or 'Не указан'}",
    ])
    return "\n".join(lines)


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎮 Добро пожаловать в CS2 TeamFinder!\n\n"
        "Создай анкету и находи игроков для совместных игр "
        "и постоянной команды.",
        reply_markup=keyboard,
    )


@dp.message(Command("cancel"))
@dp.message(F.text == "❌ Отмена")
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Заполнение отменено.",
        reply_markup=keyboard,
    )


@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь")
async def help_command(message: Message):
    await message.answer(
        "🎮 CS2 TeamFinder\n\n"
        "📝 Создай анкету.\n"
        "👤 Просматривай свою анкету.\n"
        "🔎 Ищи игроков с похожими целями и рейтингом.\n\n"
        "Заполняй данные честно и уважай других игроков.",
        reply_markup=keyboard,
    )


@dp.message(F.text == "📝 Создать анкету")
async def create_profile(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ProfileForm.nickname)
    await state.update_data(goals=[], behavior=[])
    await message.answer(
        "📝 Создаём анкету!\n\n"
        "Шаг 1 из 7\n🎮 Напиши игровой ник:",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(ProfileForm.nickname)
async def enter_nickname(message: Message, state: FSMContext):
    nickname = (message.text or "").strip()
    if not nickname or len(nickname) > 32:
        await message.answer("Ник должен быть длиной от 1 до 32 символов.")
        return

    await state.update_data(nickname=nickname)
    await state.set_state(ProfileForm.mode)
    await message.answer(
        "Шаг 2 из 7\nВыбери режим игры:",
        reply_markup=mode_keyboard,
    )


@dp.message(ProfileForm.mode)
async def enter_mode(message: Message, state: FSMContext):
    modes = {
        "🎯 premier": "Premier",
        "🔥 faceit": "FACEIT",
        "🎯 premier + faceit": "Premier + FACEIT",
    }
    mode = modes.get((message.text or "").strip().lower())
    if not mode:
        await message.answer("Выбери режим кнопкой ниже.", reply_markup=mode_keyboard)
        return

    await state.update_data(
        mode=mode,
        premier_rating=None,
        faceit_elo=None,
    )

    if "Premier" in mode:
        await state.set_state(ProfileForm.premier_rating)
        await message.answer(
            "Введи свой рейтинг Premier только числом.\n"
            "Например: 12500",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await state.set_state(ProfileForm.faceit_elo)
        await message.answer(
            "Введи свой FACEIT Elo только числом.\n"
            "Например: 1555",
            reply_markup=ReplyKeyboardRemove(),
        )


async def ask_goals(message: Message, state: FSMContext):
    await state.set_state(ProfileForm.goals)
    await message.answer(
        "Шаг 4 из 7\n"
        "Выбирай цели по очереди — можно несколько.\n"
        "Когда закончишь, нажми «✅ Готово».",
        reply_markup=goals_inline_keyboard(),
    )


@dp.message(ProfileForm.premier_rating)
async def enter_premier(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not value.isdigit() or not 1000 <= int(value) <= 50000:
        await message.answer("Введи рейтинг Premier числом от 1000 до 50000.")
        return

    await state.update_data(premier_rating=int(value))
    data = await state.get_data()

    if "FACEIT" in data["mode"]:
        await state.set_state(ProfileForm.faceit_elo)
        await message.answer("Теперь введи FACEIT Elo числом, например 1555.")
    else:
        await state.update_data(faceit_elo=None)
        await ask_goals(message, state)


@dp.message(ProfileForm.faceit_elo)
async def enter_faceit(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not value.isdigit() or not 100 <= int(value) <= 5000:
        await message.answer("Введи FACEIT Elo числом от 100 до 5000.")
        return

    await state.update_data(faceit_elo=int(value))
    data = await state.get_data()

    if "Premier" in data["mode"] and data.get("premier_rating") is None:
        await state.set_state(ProfileForm.premier_rating)
        await message.answer("Теперь введи рейтинг Premier числом, например 12500.")
    else:
        await ask_goals(message, state)



@dp.callback_query(ProfileForm.goals)
async def enter_goals(callback: CallbackQuery, state: FSMContext):
    options = {
        "goal_rating": "Поднять рейтинг",
        "goal_teammates": "Постоянные тиммейты",
        "goal_fun": "Играть ради удовольствия",
        "goal_tournament": "Команда для турниров",
    }

    data = await state.get_data()
    goals = data.get("goals", [])

    if callback.data in options:
        title = options[callback.data]

        if title in goals:
            goals.remove(title)
        else:
            goals.append(title)

        await state.update_data(goals=goals)
        await callback.message.edit_reply_markup(
            reply_markup=goals_inline_keyboard(goals)
        )
        await callback.answer()
        return

    if callback.data == "goals_done":
        if not goals:
            await callback.answer("Выбери хотя бы одну цель.", show_alert=True)
            return

        await callback.answer()
        await state.set_state(ProfileForm.microphone)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Шаг 5 из 7\n🎙 У тебя есть микрофон?",
            reply_markup=yes_no_keyboard,
        )
        return

    if callback.data == "selection_cancel":
        await callback.answer()
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Заполнение отменено.",
            reply_markup=keyboard,
        )


@dp.message(ProfileForm.microphone)
async def enter_microphone(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if value not in ("✅ Да", "❌ Нет"):
        await message.answer("Выбери «Да» или «Нет».", reply_markup=yes_no_keyboard)
        return

    await state.update_data(microphone="Да" if value == "✅ Да" else "Нет")
    await state.set_state(ProfileForm.behavior)
    await message.answer(
        "Шаг 6 из 7\n"
        "Отметь подходящие пункты. Это твои обещания другим игрокам.\n"
        "Нажми «✅ Готово», когда закончишь.",
        reply_markup=behavior_inline_keyboard(),
    )



@dp.callback_query(ProfileForm.behavior)
async def enter_behavior(callback: CallbackQuery, state: FSMContext):
    options = {
        "behavior_non_toxic": "Не токсичу",
        "behavior_teamplay": "Играю командно",
        "behavior_no_abandon": "Не бросаю матчи",
        "behavior_improve": "Хочу развиваться",
        "behavior_regular": "Готов играть регулярно",
    }

    data = await state.get_data()
    behavior = data.get("behavior", [])

    if callback.data in options:
        title = options[callback.data]

        if title in behavior:
            behavior.remove(title)
        else:
            behavior.append(title)

        await state.update_data(behavior=behavior)
        await callback.message.edit_reply_markup(
            reply_markup=behavior_inline_keyboard(behavior)
        )
        await callback.answer()
        return

    if callback.data == "behavior_done":
        if not behavior:
            await callback.answer(
                "Выбери хотя бы один пункт.",
                show_alert=True,
            )
            return

        await callback.answer()
        await state.set_state(ProfileForm.country)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Шаг 7 из 7\n🌍 Выбери страну кнопкой ниже "
            "или нажми «⏭ Пропустить».",
            reply_markup=country_keyboard,
        )
        return

    if callback.data == "selection_cancel":
        await callback.answer()
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Заполнение отменено.",
            reply_markup=keyboard,
        )


@dp.message(ProfileForm.country)
async def enter_country(message: Message, state: FSMContext):
    country = (message.text or "").strip()

    if country == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Заполнение отменено.",
            reply_markup=keyboard,
        )
        return

    if country == "🌍 Другая страна":
        await message.answer(
            "🌍 Напиши название своей страны:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    countries = {
        "🇷🇺 Россия": "Россия",
        "🇧🇾 Беларусь": "Беларусь",
        "🇰🇿 Казахстан": "Казахстан",
        "🇺🇦 Украина": "Украина",
        "🇱🇻 Латвия": "Латвия",
    }

    if country == "⏭ Пропустить" or country.lower() == "пропустить":
        country = ""
    else:
        country = countries.get(country, country)

    if len(country) > 60:
        await message.answer(
            "Слишком длинное название. Попробуй короче.",
            reply_markup=country_keyboard,
        )
        return

    data = await state.get_data()
    data["country"] = country
    save_player(message.from_user.id, data)
    await state.clear()

    row = get_player(message.from_user.id)
    await message.answer(
        "✅ Анкета сохранена!\n\n" + profile_text(row),
        reply_markup=keyboard,
    )

@dp.message(F.text == "👤 Моя анкета")
async def my_profile(message: Message):
    row = get_player(message.from_user.id)
    if not row:
        await message.answer(
            "Анкеты пока нет. Нажми «📝 Создать анкету».",
            reply_markup=keyboard,
        )
        return

    await message.answer(profile_text(row), reply_markup=keyboard)


@dp.message(F.text == "🔎 Найти тиммейтов")
async def find_players(message: Message):
    me = get_player(message.from_user.id)
    if not me:
        await message.answer(
            "Сначала создай анкету кнопкой «📝 Создать анкету».",
            reply_markup=keyboard,
        )
        return

    nickname, mode, premier, faceit, goals, mic, behavior, country = me

    with connect_db() as db:
        rows = db.execute(
            """SELECT user_id, nickname, mode, premier_rating, faceit_elo,
                      goals, microphone, behavior, country
               FROM players
               WHERE user_id != ?
               ORDER BY nickname LIMIT 10""",
            (message.from_user.id,),
        ).fetchall()

    matches = []
    for row in rows:
        uid, nick, other_mode, other_premier, other_faceit, other_goals, other_mic, other_behavior, other_country = row

        common_mode = any(
            part in other_mode for part in mode.split(" + ")
        ) or mode in other_mode

        if not common_mode:
            continue

        if "Premier" in mode and "Premier" in other_mode:
            if premier is not None and other_premier is not None:
                if abs(premier - other_premier) > 5000:
                    continue

        if "FACEIT" in mode and "FACEIT" in other_mode:
            if faceit is not None and other_faceit is not None:
                if abs(faceit - other_faceit) > 300:
                    continue

        matches.append(
            f"🎮 {nick}\n"
            f"🎯 Режим: {other_mode}\n"
            f"🏆 Premier: {other_premier if other_premier is not None else '—'}\n"
            f"🔥 FACEIT Elo: {other_faceit if other_faceit is not None else '—'}\n"
            f"🎙 Микрофон: {other_mic}\n"
            f"🎯 Цели: {other_goals}\n"
            f"🤝 Стиль игры: {other_behavior}\n"
            f"🌍 Регион: {other_country or 'Не указан'}"
        )

    if not matches:
        await message.answer(
            "Пока подходящих анкет нет.\n"
            "Пригласи друзей заполнить анкеты — тогда появятся варианты!",
            reply_markup=keyboard,
        )
        return

    await message.answer(
        "🔎 Игроки, которые могут тебе подойти:\n\n" + "\n\n──────────\n\n".join(matches),
        reply_markup=keyboard,
    )


@dp.message()
async def other_messages(message: Message):
    await message.answer("Выбери действие с помощью кнопок меню 👇", reply_markup=keyboard)


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
