from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from database.clans import (
    create_clan,
    get_user_clan,
    leave_clan,
    join_clan,
    update_clan_request_status,
    accept_member,
    reject_member,
    delete_clan,
    transfer_leadership
)
from database.cards import get_user_profile_data

clans_router = Router()


class ClansStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_join_clan_name = State()
    waiting_for_new_leader_id = State()


async def clans_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏰 Создать клан", callback_data="tribe:create")],
        [InlineKeyboardButton(text="🀄️ Вступить в клан", callback_data="tribe:join")],
        [InlineKeyboardButton(text="👤 Мой клан", callback_data="tribe:my_clan")]
    ])
    return keyboard


async def send_clans_menu(callback_or_message):
    text = "<b>Ты можешь создать клан или вступить в уже существующий.</b>"
    if callback_or_message.message.chat.type in ["group", "supergroup"]:
        await callback_or_message.answer("❌ Повторите ту же команду в личных сообщениях у бота.", show_alert=True)
        return 
    if isinstance(callback_or_message, CallbackQuery):
        try:
            await callback_or_message.message.edit_text(
                text=text,
                reply_markup=await clans_kb(),
                parse_mode="HTML"
            )
        except Exception:
            await callback_or_message.answer(
                "❌ Произошла ошибка при отправке сообщения. Попробуйте снова.",
                show_alert=True
            )
    elif isinstance(callback_or_message, Message):
        await callback_or_message.answer(
            text=text,
            reply_markup=await clans_kb(),
            parse_mode="HTML"
        )


@clans_router.callback_query(F.data.startswith("clans"))
async def clans(callback: CallbackQuery):
    user_id = callback.from_user.id
    data_parts = callback.data.split(":")
    if len(data_parts) > 1 and data_parts[1] != str(user_id) and data_parts[1] != "menu":
        await callback.answer("❌ <b>Вы арестованы, руки вверх!</b>", show_alert=True)
        return
    await send_clans_menu(callback)


@clans_router.callback_query(F.data.startswith("tribe:"))
async def tribe_callback_handler(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    user_id = callback.from_user.id

    if action == "create":
        user_clan = await get_user_clan(user_id)
        if user_clan:
            await callback.answer("⚠️ Вы уже состоите в клане. Сначала выйдите из текущего клана.", show_alert=True)
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:back")]
        ])
        await callback.message.edit_text(
            "<b>➡️ Введите имя клана:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(ClansStates.waiting_for_name)
    elif action == "my_clan":
        user_clan = await get_user_clan(user_id)
        if user_clan:
            clan_name = user_clan['name']
            members_count = len(user_clan['members'])
            text = (
                f"👥 <b>Ваш клан:</b> <i>{clan_name}</i>\n"
                f"🧑‍🤝‍🧑 <b>Участников:</b> <i>{members_count}</i>"
            )
            keyboard_buttons = [
                [InlineKeyboardButton(text="🚪 Выйти из клана", callback_data="tribe:leave")]
            ]
            if user_id == user_clan['creator']:
                keyboard_buttons.append(
                    [InlineKeyboardButton(text="⚙️ Настройка клана", callback_data="tribe:settings")]
                )
            keyboard_buttons.append(
                [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:back")]
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.answer("⚠️ Вы не состоите ни в одном клане.", show_alert=True)
    elif action == "settings":
        user_clan = await get_user_clan(user_id)
        if user_clan:
            if user_id != user_clan['creator']:
                await callback.answer("⚠️ Только создатель клана может настраивать его.", show_alert=True)
                return
            request_status = user_clan.get('request', 0)
            if request_status:
                request_text = "✅ По заявкам"
            else:
                request_text = "❌ По заявкам"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=request_text, callback_data="tribe:toggle_request")],
                    [InlineKeyboardButton(text="👑 Передать лидерство", callback_data="tribe:transfer_leadership")],
                    [InlineKeyboardButton(text="❌ Удалить клан", callback_data="tribe:delete_clan")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:my_clan")]
                ]
            )
            await callback.message.edit_text("<b>⚙️ Настройки клана:</b>", reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.answer("⚠️ Вы не состоите ни в одном клане.", show_alert=True)
    elif action == "transfer_leadership":
        user_clan = await get_user_clan(user_id)
        if user_clan:
            if user_id != user_clan['creator']:
                await callback.answer("⚠️ Только создатель клана может передать лидерство.", show_alert=True)
                return
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:settings")]
            ])
            await callback.message.edit_text(
                "<b>➡️ Введите user_id пользователя, которому хотите передать лидерство:</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await state.set_state(ClansStates.waiting_for_new_leader_id)
        else:
            await callback.answer("⚠️ Вы не состоите ни в одном клане.", show_alert=True)
    elif action == "confirm_transfer_leadership":
        data = await state.get_data()
        new_leader_id = data.get('new_leader_id')
        if not new_leader_id:
            await callback.answer("⚠️ Произошла ошибка. Попробуйте снова.", show_alert=True)
            return
        user_clan = await get_user_clan(user_id)
        if user_clan['creator'] != user_id:
            await callback.answer("⚠️ Только создатель клана может передать лидерство.", show_alert=True)
            return
        success, message_text = await transfer_leadership(user_clan['id'], new_leader_id)
        if success:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:back")]
            ])
            await callback.message.edit_text("<b>✅ Лидерство успешно передано.</b>", reply_markup=keyboard, parse_mode="HTML")
            await state.clear()
            await callback.bot.send_message(
                chat_id=int(new_leader_id),
                text="<b>✅ Лидерство вашего клана передано вам.</b>",
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Произошла ошибка при передаче лидерства.", show_alert=True)
    elif action == "toggle_request":
        user_clan = await get_user_clan(user_id)
        if user_clan:
            if user_id != user_clan['creator']:
                await callback.answer("⚠️ Только создатель клана может настраивать его.", show_alert=True)
                return
            new_request_status = 0 if user_clan['request'] else 1
            await update_clan_request_status(user_clan['id'], new_request_status)
            user_clan['request'] = new_request_status
            if new_request_status:
                request_text = "✅ По заявкам"
            else:
                request_text = "❌ По заявкам"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=request_text, callback_data="tribe:toggle_request")],
                    [InlineKeyboardButton(text="👑 Передать лидерство", callback_data="tribe:transfer_leadership")],
                    [InlineKeyboardButton(text="❌ Удалить клан", callback_data="tribe:delete_clan")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:my_clan")]
                ]
            )
            await callback.message.edit_text("<b>⚙️ Настройки клана:</b>", reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.answer("⚠️ Вы не состоите ни в одном клане.", show_alert=True)
    elif action == "delete_clan":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Да, удалить", callback_data="tribe:confirm_delete_clan")],
                [InlineKeyboardButton(text="🔙 Нет, отмена", callback_data="tribe:settings")]
            ]
        )
        await callback.message.edit_text(
            "<b>❗️ Вы уверены, что хотите удалить клан? Это действие необратимо.</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    elif action == "confirm_delete_clan":
        user_clan = await get_user_clan(user_id)
        if user_clan:
            if user_id != user_clan['creator']:
                await callback.answer("⚠️ Только создатель клана может удалить его.", show_alert=True)
                return
            success, message_text = await delete_clan(user_clan['id'])
            if success:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:back")]
                ])
                await callback.message.edit_text("<b>✅ Клан успешно удален.</b>", reply_markup=keyboard, parse_mode="HTML")
            else:
                await callback.answer("❌ Произошла ошибка при удалении клана.", show_alert=True)
        else:
            await callback.answer("⚠️ Вы не состоите ни в одном клане.", show_alert=True)
    elif action == "leave":
        success, message_text = await leave_clan(user_id)
        if success:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:back")]
            ])
            await callback.message.edit_text("<b>✅ Вы успешно вышли из клана.</b>", reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.answer(f"⚠️ {message_text}", show_alert=True)
    elif action == "join":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:back")]
        ])
        await callback.message.edit_text(
            "<b>➡️ Введите имя клана, в который хотите вступить:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(ClansStates.waiting_for_join_clan_name)
    elif action == "back":
        await state.clear()
        await callback.answer()
        await send_clans_menu(callback)
    else:
        await callback.message.edit_text("❌ <b>Неизвестная команда.</b>", parse_mode="HTML")


@clans_router.callback_query(F.data == "tribe:back")
async def handle_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await send_clans_menu(callback)


@clans_router.message(ClansStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    success, message_text = await create_clan(message.text.strip(), message.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:back")]
    ])
    if success:
        await message.reply(f"✅ <b>{message_text}</b>", reply_markup=keyboard, parse_mode="HTML")
        await state.clear()
    else:
        await message.reply(f"⚠️ <b>{message_text}</b>\n\n<b>Пожалуйста, введите другое имя:</b>", reply_markup=keyboard, parse_mode="HTML")


@clans_router.message(ClansStates.waiting_for_join_clan_name)
async def process_join_clan_name(message: Message, state: FSMContext):
    clan_name = message.text.strip()
    user_id = message.from_user.id
    success, message_text, creator_id = await join_clan(user_id, clan_name)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="tribe:back")]
    ])
    if success:
        await message.reply(f"✅ <b>{message_text}</b>", reply_markup=keyboard, parse_mode="HTML")
        if creator_id:
            await notify_clan_creator(message.bot, creator_id, user_id, clan_name)
        await state.clear()
    else:
        await message.reply(f"⚠️ <b>{message_text}</b>\n\n<b>Пожалуйста, введите другое имя клана:</b>", reply_markup=keyboard, parse_mode="HTML")


@clans_router.message(ClansStates.waiting_for_new_leader_id)
async def process_new_leader_id(message: Message, state: FSMContext):
    user_id = message.from_user.id
    new_leader_id = message.text.strip()
    if not new_leader_id.isdigit():
        await message.reply("⚠️ <b>Пожалуйста, введите корректный user_id пользователя.</b>", parse_mode="HTML")
        return
    new_leader_id = int(new_leader_id)
    user_clan = await get_user_clan(user_id)
    if new_leader_id not in user_clan['members']:
        await message.reply("⚠️ <b>Этот пользователь не состоит в вашем клане. Попробуйте снова.</b>", parse_mode="HTML")
        return
    if new_leader_id == user_id:
        await message.reply("⚠️ <b>Вы уже являетесь лидером клана.</b>", parse_mode="HTML")
        return
    # Подтверждение передачи лидерства
    await state.update_data(new_leader_id=new_leader_id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👑 Да, передать", callback_data="tribe:confirm_transfer_leadership")],
            [InlineKeyboardButton(text="🔙 Нет, отмена", callback_data="tribe:settings")]
        ]
    )
    await message.reply(
        f"❗️ <b>Вы уверены, что хотите передать лидерство пользователю с user_id {new_leader_id}?</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def notify_clan_creator(bot: Bot, creator_id: int, user_id: int, clan_name: str):
    user_profile = await get_user_profile_data(user_id)
    if user_profile:
        now_points = user_profile['now_points']
        all_points = user_profile['all_points']
        cards_count = len(user_profile['cards'])
    else:
        now_points = 0
        all_points = 0
        cards_count = 0

    text = (
        f"📝 <b>Новая заявка на вступление в ваш клан '{clan_name}':</b>\n\n"
        f"👤 <b>Игрок:</b> <a href='tg://user?id={user_id}'>{user_id}</a>\n"
        f"💠 <b>Очки сейчас:</b> {now_points}\n"
        f"🏅 <b>Всего очков:</b> {all_points}\n"
        f"🃏 <b>Карточек:</b> {cards_count}\n\n"
        f"<b>Принять или отклонить заявку?</b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept:{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")
        ]
    ])
    await bot.send_message(
        chat_id=creator_id,
        text=text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@clans_router.callback_query(F.data.startswith("accept:") | F.data.startswith("reject:"))
async def handle_join_request_response(callback: CallbackQuery):
    data = callback.data
    if data.startswith('accept:'):
        action = 'accept'
    elif data.startswith('reject:'):
        action = 'reject'
    else:
        return

    user_id = int(data.split(":")[1])
    clan_creator_id = callback.from_user.id

    if action == 'accept':
        success, message = await accept_member(clan_creator_id, user_id)
        if success:
            await callback.message.edit_text("<b>✅ Вы приняли игрока в клан.</b>", parse_mode="HTML")
            await callback.bot.send_message(
                user_id,
                "<b>✅ Ваша заявка на вступление в клан была одобрена!</b>",
                parse_mode="HTML"
            )
        else:
            if "Заявка истекла" in message:
                await callback.message.edit_text(f"⚠️ <b>{message}</b>", parse_mode="HTML")
            else:
                await callback.answer(f"⚠️ {message}", show_alert=True)
    elif action == 'reject':
        success, message = await reject_member(clan_creator_id, user_id)
        if success:
            await callback.message.edit_text("<b>❌ Вы отклонили заявку игрока на вступление в клан.</b>", parse_mode="HTML")
            await callback.bot.send_message(
                user_id,
                "<b>❌ Ваша заявка на вступление в клан была отклонена.</b>",
                parse_mode="HTML"
            )
        else:
            await callback.answer(f"⚠️ {message}", show_alert=True)
