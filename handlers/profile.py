from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaAnimation
from aiogram.utils.text_decorations import html_decoration

from database.cards import get_user_profile_data, cards_data, get_top_users_by_now_points, get_top_users_by_cards, \
    get_top_users_by_all_points
from database.clans import get_top_clans_by_points
from kb import profile_kb, rarity_kb, cards_keyboard, top_kb, top_back_kb

profile_router = Router()

RARITY_POINTS = {
    "Редкая": 1500,
    "СверхРедкая": 3500,
    "Мифическая": 5000,
    "Легендарная": 10000,
    "Анимка": 15000
}


@profile_router.message(Command("profile"))
@profile_router.message(F.text.lower().in_({"мпрофиль", "👥️ профиль"}))
async def profile(msg: Message):
    user_id = msg.from_user.id
    user_data = await get_user_profile_data(user_id)
    if not user_data:
        await msg.answer("❌ Профиль не найден. Похоже, вы ещё не получили карточек.")
        return
    cards = user_data["cards"]
    now_points = user_data["now_points"]
    all_points = user_data["all_points"]
    card_count = len(cards)
    profile_text = (
        f"🎴 <b>Ваш профиль</b> 🎴\n\n"
        f"👤 <b>Имя:</b> {html_decoration.bold(html_decoration.quote(msg.from_user.first_name))}\n"
        f"🃏 <b>Количество карточек:</b> {card_count}\n"
        f"💰 <b>Текущие очки:</b> {now_points} 🪙\n"
        f"🏆 <b>Очки за все сезоны:</b> {all_points} 🏅\n\n"
        "<i>Собирайте больше карточек и увеличивайте свой счёт!</i> 📈"
    )
    await msg.reply(profile_text, parse_mode="HTML", reply_markup=await profile_kb(user_id))


@profile_router.callback_query(F.data.startswith("top:"))
async def top_cards(callback: CallbackQuery):
    user_id = callback.from_user.id
    if callback.data.split(":")[1] != str(user_id):
        await callback.answer("Вы арестованы, руки вверх!")
        return
    await callback.message.reply(
        "<blockquote>Выберите нужный вам топ:</blockquote>",
        reply_markup=await top_kb(user_id),
        parse_mode="HTML"
    )


@profile_router.callback_query(F.data.startswith("top_"))
async def show_top(callback: CallbackQuery):
    data = callback.data.split(":")
    top_data = data[0]
    user_id = callback.from_user.id
    if data[1] != str(user_id):
        await callback.answer("Вы арестованы, руки вверх!")
        return
    top_type = top_data.split("_")[1]
    if top_type == "points":
        top_users = await get_top_users_by_now_points()
        text = "🏆 Топ 10 игроков по текущим очкам:\n\n"
        for i, (user_id, first_name, now_points) in enumerate(top_users, start=1):
            text += f"<blockquote> {i}. {html_decoration.bold(html_decoration.quote(first_name))} - {now_points} очков </blockquote>\n"
    elif top_type == "cards":
        top_users = await get_top_users_by_cards()
        text = "🏆 Топ 10 игроков по количеству карточек:\n\n"
        for i, (user_id, first_name, card_count) in enumerate(top_users, start=1):
            text += f"<blockquote> {i}. {html_decoration.bold(html_decoration.quote(first_name))}- {card_count} карточек </blockquote>\n"
    elif top_type == "all":
        top_users = await get_top_users_by_all_points()
        text = "🏆 Топ 10 игроков по очкам за все сезоны:\n\n"
        for i, (user_id, first_name, all_points) in enumerate(top_users, start=1):
            text += f"<blockquote> {i}. {html_decoration.bold(html_decoration.quote(first_name))} - {all_points} очков </blockquote>\n"
    elif top_type == "clans":
        top_clans = await get_top_clans_by_points()
        text = "🏆 <b>Топ 10 кланов по суммарным очкам:</b>\n\n"
        for i, (clan_name, member_count, total_points) in enumerate(top_clans, start=1):
            text += f"{i}. 🏰 {html_decoration.bold(html_decoration.quote(clan_name))} — {total_points} очков ({member_count} участников)\n"
    elif top_type == "back":
        await callback.message.edit_text(
            "<blockquote>Выберите нужный вам топ:</blockquote>",
            reply_markup=await top_kb(user_id),
            parse_mode="HTML"
        )
        return
    else:
        await callback.answer("Неверный выбор.", show_alert=True)
        return
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=await top_back_kb(callback.from_user.id))


@profile_router.callback_query(F.data.startswith("cards:"))
async def show_cards(callback: CallbackQuery):
    data = callback.data.split(":")
    user_id = data[1]
    user_nickname = callback.from_user.first_name
    if user_id != str(callback.from_user.id):
        await callback.answer("Вы арестованы, руки вверх!")
        return
    try:
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text="Выберите редкость карточек, которые хотите посмотреть:",
            reply_markup=await rarity_kb()
        )
        if callback.message.chat.type in ["group", "supergroup"]:
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text=f"{user_nickname}, карточки отправлены вам в личные сообщения!",
                reply_to_message_id=callback.message.message_id
            )
    except:
        await callback.answer(
            "Напишите боту что-то в личные сообщения, чтобы отправить вам карточки!",
            show_alert=True
        )


@profile_router.callback_query(F.data.startswith("select_rarity:"))
async def select_rarity(callback: CallbackQuery):
    rarity = callback.data.split(":")[1]
    user_data = await get_user_profile_data(callback.from_user.id)
    if user_data is None:
        await callback.message.answer("Данные профиля не найдены.")
        await callback.answer()
        return
    user_cards = user_data['cards']
    user_cards_data = [card for card in cards_data['cards'] if card['id'] in user_cards]
    rarity_cards = [card for card in user_cards_data if card['rarity'] == rarity]
    if not rarity_cards:
        await callback.answer("❌ У вас нет карточек этой редкости.")
        return
    index = 0
    card = rarity_cards[index]
    points = RARITY_POINTS.get(card['rarity'], 0)
    caption = f"🃏 Карточка: {card['name']}\n🎴 Раритет: {card['rarity']}\n💯 Очки: {points}"
    total_cards = len(rarity_cards)
    keyboard = await cards_keyboard(rarity, index, total_cards)

    if card['rarity'] == "Анимка":
        await callback.message.answer_animation(animation=card['file_id'], caption=caption, reply_markup=keyboard)
    else:
        await callback.message.answer_photo(photo=card['file_id'], caption=caption, reply_markup=keyboard)
    await callback.answer()


@profile_router.callback_query(F.data.startswith("view_card:"))
async def view_card(callback: CallbackQuery):
    data = callback.data.split(":")
    rarity = data[1]
    index = int(data[2])
    user_data = await get_user_profile_data(callback.from_user.id)
    if user_data is None:
        await callback.message.answer("Данные профиля не найдены.")
        await callback.answer()
        return
    user_cards = user_data['cards']
    user_cards_data = [card for card in cards_data['cards'] if card['id'] in user_cards]
    rarity_cards = [card for card in user_cards_data if card['rarity'] == rarity]
    total_cards = len(rarity_cards)

    card = rarity_cards[index]
    points = RARITY_POINTS.get(card['rarity'], 0)
    caption = f"🃏 Карточка: {card['name']}\n🎴 Раритет: {card['rarity']}\n💯 Очки: {points}"
    keyboard = await cards_keyboard(rarity, index, total_cards)

    if card['rarity'] == "Анимка":
        media = InputMediaAnimation(media=card['file_id'], caption=caption)
    else:
        media = InputMediaPhoto(media=card['file_id'], caption=caption)

    try:
        await callback.message.edit_media(media=media, reply_markup=keyboard)
    except Exception as e:
        await callback.message.delete()
        if card['rarity'] == "Анимка":
            await callback.message.answer_animation(animation=card['file_id'], caption=caption, reply_markup=keyboard)
        else:
            await callback.message.answer_photo(photo=card['file_id'], caption=caption, reply_markup=keyboard)
    await callback.answer()