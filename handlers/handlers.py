from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberAdministrator, ChatMemberOwner, CallbackQuery

from database.cooldown import toggle_cooldown_state, set_cooldown_time
from database.mailing import add_user, add_chat
from kb import cooldown_kb, cooldown_time_kb, add_to_group, start_keyboard

router = Router()


async def is_admin_with_rights(message: Message) -> bool:
    admins = await message.bot.get_chat_administrators(chat_id=message.chat.id)

    for admin in admins:
        if admin.user.id == message.from_user.id:
            if isinstance(admin, ChatMemberAdministrator) and admin.can_promote_members:
                return True
            if isinstance(admin, ChatMemberOwner):
                return True

    return False


@router.message(Command("start"))
async def start_handler(msg: Message):
    mention = msg.from_user.mention_html()
    user_id = msg.from_user.id
    chat_id = msg.chat.id
    text = (f"👋 {mention}, добро пожаловать в MemeCats Cards!\n\n"
            f"🃏 Открывай карточки с мемными котами..\n\n"
            f"🔄 Вселенная карт постоянно обновляется, новые котики ожидают тебя.\n\n")
    if msg.chat.type == "private":
        text += '<blockquote> 🚀 Напиши "мкот" чтобы открыть твою первую карточку. </blockquote>'
        await msg.bot.send_sticker(
            chat_id=chat_id,
            sticker="CAACAgIAAxkBAAENI7xnOayUyZWNA_oYkHmB90x1HW5uNQACujkAArW6WUjV9K26kAro_jYE",
            reply_markup=await start_keyboard()
        )
        await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=await add_to_group())
        await add_user(user_id)
    elif msg.chat.type in ["group", "supergroup"]:
        text += '<blockquote> 🚀 Напиши "мкот" чтобы открыть твою первую карточку.</blockquote>\n❔ /help - Посмотреть все команды.'
        await msg.reply(text, parse_mode=ParseMode.HTML, reply_markup=await add_to_group())
        await add_chat(chat_id)


@router.message(Command("help"))
async def start_handler(msg: Message):
    text = (
        f"<b>📚 Доступные команды:</b>\n\n"
        f"🎮 <b>Основные:</b>\n"
        f"/start — Начать игру 🃏\n"
        f"/mcat — Получить карточку 🎲\n\n"
        f"🛠 <b>Настройки:</b>\n"
        f"/adm — Настроить автоудаление ⏳\n"
        f"/profile — Ваш профиль 🎴\n\n"
        f"<i>Собирайте карточки, зарабатывайте очки и станьте лучшим коллекционером! 🐾</i>"
    )
    await msg.reply(text, parse_mode="HTML")


@router.message(Command("adm"))
async def adm_handler(msg: Message):
    if msg.chat.type not in ["group", "supergroup"]:
        await msg.answer("❌ Данная команда работает только в чатах!", reply_markup=await add_to_group())
        return
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    is_admin = await is_admin_with_rights(msg)
    if not is_admin:
        await msg.reply("❌ У вас нет прав для выполнения этой команды.")
        return

    explanation_text = (
        "🕓 <b>Настройка автоудаления сообщений (Кулдаун)</b>\n\n"
        "<i>Кулдаун</i> — это время, через которое сообщения с карточками автоматически удаляются. "
        "Если вы не уверены, лучше не изменяйте настройки. Настройка применяется на весь чат."
        "Настройка предназначена для администратора.\n\n"
        "Вы можете выбрать время, по истечении которого сообщение с карточкий будет автоматически удалено.\n"
    )
    await msg.answer(explanation_text, parse_mode=ParseMode.HTML, reply_markup=await cooldown_kb(user_id, chat_id))


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_cooldown_handler(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    if user_id != str(callback.from_user.id):
        await callback.answer("Не для ваших лапок кнопка.")
        return
    chat_id = callback.message.chat.id
    await toggle_cooldown_state(chat_id)
    await callback.message.edit_reply_markup(reply_markup=await cooldown_kb(int(user_id), chat_id))


@router.callback_query(F.data.startswith("set_time:"))
async def open_cooldown_time_menu(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user_id = callback.data.split(":")[1]
    if user_id != str(callback.from_user.id):
        await callback.answer("Не для ваших лапок кнопка.")
        return
    await callback.message.edit_text(
        "🕓 <b>Выберите время для автоудаления:</b>\n\n"
        "<i>После выбранного времени сообщение с карточкой будет удалено.</i>\n\n"
        "🔄 <b>Выбор временного интервала:</b>",
        reply_markup=await cooldown_time_kb(chat_id, user_id),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("time_set:"))
async def set_cooldown_time_handler(callback: CallbackQuery):
    _, chat_id, minutes, user_idd = callback.data.split(":")
    user_id = callback.from_user.id
    if user_idd != str(user_id):
        await callback.answer("Не для ваших лапок кнопка.")
        return
    chat_id = int(chat_id)
    minutes = int(minutes)

    await set_cooldown_time(chat_id, minutes)
    await callback.message.edit_text(
        f"⏳ <b>Время кулдауна обновлено:</b> {minutes} минут.\n\n"
        "<i>Теперь сообщения с карточкой будут удаляться через указанное время.</i>",
        reply_markup=await cooldown_kb(user_id, chat_id),
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"Кулдаун установлен на {minutes} минут.")


@router.callback_query(F.data.startswith("back:"))
async def back_to_main_menu(callback: CallbackQuery):
    _, chat_id, user_idd = callback.data.split(":")
    user_id = callback.from_user.id
    if user_idd != str(user_id):
        await callback.answer("Не для ваших лапок кнопка.")
        return
    await callback.message.edit_text(
        "🕓 <b>Настройка автоудаления сообщений</b>\n\n"
        "<i>Вы можете изменить время автоудаления для управления сообщениями с карточками в чате.</i>",
        reply_markup=await cooldown_kb(user_id, chat_id),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()
