from aiogram import types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from database.cooldown import get_cooldown_state


async def cooldown_kb(user_id, chat_id):
    builder = InlineKeyboardBuilder()
    state = await get_cooldown_state(chat_id)

    toggle_text = "❌ Выкл" if state == "on" else "✅ Вкл"
    builder.add(InlineKeyboardButton(text="🕓 КулДаун", callback_data=f"set_time:{user_id}"))
    builder.add(InlineKeyboardButton(text=toggle_text, callback_data=f"toggle:{user_id}"))
    return builder.as_markup()


async def cooldown_time_kb(chat_id, user_id):
    builder = InlineKeyboardBuilder()
    times = [
        ("1 минута", 1),
        ("10 минут", 10),
        ("20 минут", 20),
        ("30 минут", 30),
        ("1 час", 60)
    ]

    for label, minutes in times:
        builder.row(InlineKeyboardButton(text=label, callback_data=f"time_set:{chat_id}:{minutes}:{user_id}"))

    builder.add(InlineKeyboardButton(text="Назад", callback_data=f"back:{chat_id}:{user_id}"))
    builder.adjust(1)
    return builder.as_markup()


async def profile_kb(user_id):
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🎴Мои карты", callback_data=f"cards:{user_id}"),
        InlineKeyboardButton(text="🏆 Топ карточек", callback_data=f"top:{user_id}"),
        InlineKeyboardButton(text="🗼 Кланы", callback_data=f"clans:{user_id}")
    )
    builder.adjust(2, 2)
    return builder.as_markup()


async def clans_kb():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🏰 Создать клан", callback_data="tribe:create"),
        InlineKeyboardButton(text="🀄️ Вступить в клан", callback_data="tribe:join"),
        InlineKeyboardButton(text="👤 Мой клан", callback_data="tribe:my_clan"),
    )
    builder.adjust(1)
    return builder.as_markup()


async def top_kb(user_id):
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🃏 Топ по карточкам", callback_data=f"top_cards:{user_id}"),
        InlineKeyboardButton(text="💯 Топ по очкам", callback_data=f"top_points:{user_id}"),
        InlineKeyboardButton(text="🎴 Топ за все время", callback_data=f"top_all:{user_id}"),
        InlineKeyboardButton(text="🏰 Топ кланов", callback_data=f"top_clans:{user_id}")
    )
    builder.adjust(2, 1)
    return builder.as_markup()


async def top_back_kb(user_id):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Назад 🔙️", callback_data=f"top_back:{user_id}"))
    return builder.as_markup()


async def rarity_kb():
    keyboard = InlineKeyboardBuilder()
    rarities = ["⚡️ Редкая", "🐲 СверхРедкая", "⚔️ Мифическая", "🩸 Легендарная", "🎞 Анимка"]
    rarities_callback = ["Редкая", "СверхРедкая", "Мифическая", "Легендарная", "Анимка"]

    for rarity, rarity_callback in zip(rarities, rarities_callback):
        button = InlineKeyboardButton(text=rarity, callback_data=f"select_rarity:{rarity_callback}")
        keyboard.add(button)

    keyboard.adjust(1)
    return keyboard.as_markup()


async def next_keyboard(rarity, index):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"view_card:{rarity}:{index+1}"))
    return builder.as_markup()


async def cards_keyboard(rarity, index, total_cards):
    builder = InlineKeyboardBuilder()
    if index > 0:
        builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data=f'view_card:{rarity}:{index-1}'))
    if index < total_cards - 1:
        builder.add(InlineKeyboardButton(text="Вперед ➡️", callback_data=f'view_card:{rarity}:{index+1}'))
    return builder.as_markup()


async def add_to_group():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Добавить в группу", url="https://t.me/MemeCatsCardsBot?startgroup=new"))
    return builder.as_markup()


async def start_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="🐈 Мкот"))
    builder.add(types.KeyboardButton(text="👥️ Профиль"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)