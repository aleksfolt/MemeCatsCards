import json
import aiosqlite
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
    ContentType, InputFile, FSInputFile,
)
from aiogram.filters import Command

from database.cards import cards_data, reset_cooldown
from database.mailing import get_stats

ADMIN_ID = []

admin_router = Router()


class CardStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_rarity = State()
    waiting_for_photo = State()
    waiting_for_message = State()


def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🃏 Добавить карточку", callback_data="add_card")],
            [InlineKeyboardButton(text="📜 Показать все карточки", callback_data="show_cards")],
            [InlineKeyboardButton(text="📈 Статистика", callback_data="show_stats")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="send_broadcast")],
            [InlineKeyboardButton(text="💾 Резерв Б/Д", callback_data="backup_db")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")],
        ]
    )
    return keyboard


def get_cancel_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]
    )
    return keyboard


@admin_router.message(Command('admin'))
async def start(message: Message):
    if message.from_user.id not in ADMIN_ID:
        await message.reply("❌ У вас нет доступа к этой функции.")
    else:
        if message.chat.type != "private":
            await message.reply("НАЙН, ТОЛЬКО В ЛС")
            return
        await show_admin_panel(message)


async def show_admin_panel(message: Message):
    keyboard = get_admin_keyboard()
    await message.answer("🎛️ **Админ-панель:**", reply_markup=keyboard, parse_mode='Markdown')


@admin_router.callback_query(F.data == "cancel_action")
async def cancel_action(callback_query: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await callback_query.answer("❗ Нет активных действий для отмены.", show_alert=True)
        return
    await state.clear()
    await callback_query.message.edit_text("✅ Действие отменено.", reply_markup=get_admin_keyboard())
    await callback_query.answer()


@admin_router.callback_query(F.data == "send_broadcast")
async def start_broadcast(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "📢 **Введите сообщение для рассылки** (поддерживается HTML-разметка):",
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    await state.set_state(CardStates.waiting_for_message)
    await callback_query.answer()


@admin_router.message(CardStates.waiting_for_message, F.content_type == ContentType.TEXT)
async def process_broadcast_message(message: Message, state: FSMContext):
    broadcast_text = message.text
    await state.clear()

    await message.answer("🚀 Начинаю рассылку по чатам...", reply_markup=get_admin_keyboard())

    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT DISTINCT chat_id FROM chat_users WHERE chat_id IS NOT NULL")
        rows = await cursor.fetchall()
        chat_ids = [row[0] for row in rows]

    success_count = 0
    failure_count = 0

    for chat_id in chat_ids:
        try:
            await message.bot.send_message(
                chat_id=chat_id,
                text=broadcast_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            success_count += 1
        except Exception as e:
            print(f"Не удалось отправить сообщение в чат {chat_id}: {e}")
            failure_count += 1

    await message.answer(
        f"✅ **Рассылка завершена.**\n\n"
        f"🎯 Успешно: {success_count}\n"
        f"⚠️ Не удалось: {failure_count}",
        parse_mode='Markdown'
    )


@admin_router.callback_query(F.data == "show_stats")
async def show_stats(callback_query: CallbackQuery):
    users_count, chats_count = await get_stats()

    stats_message = (
        f"📊 **Статистика:**\n\n"
        f"👤 Личных пользователей: **{users_count}**\n"
        f"💬 Чатов: **{chats_count}**"
    )
    await callback_query.message.edit_text(stats_message, parse_mode='Markdown', reply_markup=get_admin_keyboard())
    await callback_query.answer()


@admin_router.callback_query(F.data == "add_card")
async def add_card(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "📝 **Введите имя карточки:**",
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    await state.set_state(CardStates.waiting_for_name)
    await callback_query.answer()


@admin_router.callback_query(F.data == "show_cards")
async def show_cards(callback_query: CallbackQuery):
    if not cards_data.get("cards"):
        await callback_query.message.edit_text("❌ Нет добавленных карточек.", reply_markup=get_admin_keyboard())
    else:
        text = "📜 **Список карточек:**\n\n"
        for card in cards_data["cards"]:
            media_type = card.get("media_type", "photo")
            rarity = card.get("rarity", "Неизвестно")
            text += (
                f"• **{card['name']}**\n"
                f"  ID: {card['id']}\n"
                f"  Редкость: {rarity}\n"
            )
        await callback_query.message.edit_text(text, parse_mode='Markdown', reply_markup=get_admin_keyboard())
    await callback_query.answer()


@admin_router.callback_query(F.data == "backup_db")
async def backup_db(callback_query: CallbackQuery):
    try:
        db_file = FSInputFile("database.db")
        await callback_query.bot.send_document(
            chat_id=callback_query.message.chat.id,
            document=db_file,
            caption="📦 *Резервная копия базы данных.*",
            parse_mode="MarkDown"
        )
        await callback_query.message.answer("✅ Резервная копия базы данных отправлена в ЛС.")
    except Exception as e:
        await callback_query.message.answer(f"❌ Не удалось отправить резервную копию: {e}")
    await callback_query.answer()


@admin_router.message(CardStates.waiting_for_photo, F.content_type == ContentType.ANY)
async def process_invalid_photo(message: Message):
    await message.answer("❌ Пожалуйста, отправьте изображение (фото) или GIF-анимацию карточки.",
                         reply_markup=get_cancel_keyboard())


@admin_router.message(CardStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("❌ Имя карточки не может быть пустым. Попробуйте снова:",
                             reply_markup=get_cancel_keyboard())
        return
    await state.update_data(name=name)
    await message.answer("✨ **Введите редкость карточки:**", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
    await state.set_state(CardStates.waiting_for_rarity)


@admin_router.message(CardStates.waiting_for_rarity)
async def process_rarity(message: Message, state: FSMContext):
    rarity = message.text.strip()
    if not rarity:
        await message.answer("❌ Редкость карточки не может быть пустой. Попробуйте снова:",
                             reply_markup=get_cancel_keyboard())
        return
    await state.update_data(rarity=rarity)
    await message.answer("📷 **Отправьте изображение (фото) или GIF-анимацию карточки:**",
                         reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
    await state.set_state(CardStates.waiting_for_photo)


@admin_router.message(
    CardStates.waiting_for_photo,
    F.content_type.in_([ContentType.PHOTO, ContentType.ANIMATION])
)
async def process_photo(message: Message, state: FSMContext):
    if message.content_type == ContentType.PHOTO:
        media_file = message.photo[-1]
        media_type = "photo"
    elif message.content_type == ContentType.ANIMATION:
        media_file = message.animation
        media_type = "animation"
    else:
        await message.answer("❌ Пожалуйста, отправьте изображение (фото) или GIF-анимацию карточки.",
                             reply_markup=get_cancel_keyboard())
        return

    file_id = media_file.file_id
    await state.update_data(file_id=file_id, media_type=media_type)
    data = await state.get_data()

    if cards_data.get("cards"):
        max_id = max(int(card["id"]) for card in cards_data["cards"] if card["id"].isdigit())
        new_id = str(max_id + 1)
    else:
        new_id = '1'

    card = {
        "name": data["name"],
        "id": new_id,
        "rarity": data["rarity"],
        "file_id": data["file_id"],
        "media_type": data["media_type"]
    }
    cards_data["cards"].append(card)

    with open('cards.json', 'w', encoding='utf-8') as f:
        json.dump(cards_data, f, ensure_ascii=False, indent=4)

    await message.answer(
        f"✅ **Карточка успешно добавлена!**\n\n"
        f"• **ID:** {new_id}\n"
        f"• **Имя:** {data['name']}\n"
        f"• **Редкость:** {data['rarity']}\n"
        f"• **Тип:** {data['media_type']}",
        parse_mode='Markdown',
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@admin_router.message(CardStates.waiting_for_photo, F.content_type == ContentType.ANY)
async def handle_invalid_photo(message: Message):
    await message.answer("❌ Пожалуйста, отправьте изображение (фото) или GIF-анимацию карточки.",
                         reply_markup=get_cancel_keyboard())
