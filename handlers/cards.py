import asyncio
import datetime
import random
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database.cards import get_last_card_time, cards_data, add_card_and_points, has_user_card
from database.cooldown import get_cooldown_time, get_cooldown_state
from filters.FloodWait import RateLimitFilter

cards_router = Router()

COOLDOWN_SECONDS = 5400

RARITY_POINTS = {
    "Редкая": 1500,
    "СверхРедкая": 3500,
    "Мифическая": 5000,
    "Легендарная": 10000,
    "Анимка": 15000
}


async def auto_delete(bot, chat_id: int, user_message_id: int, bot_message_id: int):
    delete_state = await get_cooldown_state(chat_id)
    delete_time_minutes = await get_cooldown_time(chat_id)

    if delete_state != "on":
        return

    delete_delay = int(delete_time_minutes) * 60
    if delete_delay <= 0:
        return

    await asyncio.sleep(delete_delay)

    try:
        await bot.delete_message(chat_id, user_message_id)
        await bot.delete_message(chat_id, bot_message_id)
    except Exception as e:
        print(f"Ошибка при автоудалении: {e}")


@cards_router.message(RateLimitFilter(2), Command("mcat"))
@cards_router.message(RateLimitFilter(2), F.text.lower().in_({"получить карту", "мкот", "🐈 мкот"}))
async def cards_handler(msg: Message):
    user_id = msg.from_user.id
    first_name = msg.from_user.first_name
    chat_id = msg.chat.id
    current_time = datetime.datetime.now()

    last_time = await get_last_card_time(user_id)
    if last_time is not None:
        elapsed_seconds = (current_time - last_time).total_seconds()
        if elapsed_seconds < COOLDOWN_SECONDS:
            remaining_seconds = int(COOLDOWN_SECONDS - elapsed_seconds)
            remaining_hours = remaining_seconds // 3600
            remaining_minutes = (remaining_seconds % 3600) // 60
            remaining_seconds = remaining_seconds % 60
            await msg.reply(
                f"<i>Вы уже получали карточку недавно.</i> Пожалуйста, подождите ещё:\n\n"
                f"<b>{remaining_hours} ч {remaining_minutes} мин {remaining_seconds} сек</b> ⏳",
                parse_mode='HTML'
            )
            return

    random_number = random.randint(1, 100)
    if 1 <= random_number <= 5:
        rarity = "Анимка 🎥"
    elif 6 <= random_number <= 15:
        rarity = "Легендарная 🌟"
    elif 16 <= random_number <= 30:
        rarity = "Мифическая ✨"
    elif 31 <= random_number <= 50:
        rarity = "СверхРедкая 💎"
    else:
        rarity = "Редкая ⭐️"

    clean_rarity = rarity.split(" ")[0]
    eligible_cards = [card for card in cards_data["cards"] if card["rarity"] == clean_rarity]
    if not eligible_cards:
        await msg.answer(f"<i>К сожалению, нет карточек с редкостью</i> <b>{rarity}</b>.", parse_mode='HTML')
        return

    selected_card = random.choice(eligible_cards)
    points = RARITY_POINTS[clean_rarity]

    if clean_rarity == "Анимка":
        send_method = msg.answer_animation
        media_arg = {"animation": selected_card["file_id"]}
    else:
        send_method = msg.answer_photo
        media_arg = {"photo": selected_card["file_id"]}

    if await has_user_card(user_id, selected_card["id"]):
        bot_message = await send_method(
            **media_arg,
            caption=(
                f"<b>Повторная карточка</b> 🃏\n\n"
                f"Название: <b>{selected_card['name']}</b>\n"
                f"Редкость: <b>{rarity}</b>\n"
                f"<i>Начислено очков:</i> <b>{points} 🪙</b>\n\n"
                "<blockquote>Вы уже получили эту карточку ранее. Начислены только очки!</blockquote>"
            ),
            parse_mode='HTML',
            reply_to_message_id=msg.message_id
        )
    else:
        bot_message = await send_method(
            **media_arg,
            caption=(
                f"<b>Поздравляем! 🎉 Вы получили новую карточку!</b>\n\n"
                f"<i>Название:</i> <b>{selected_card['name']}</b>\n"
                f"<i>Редкость:</i> <b>{rarity}</b>\n"
                f"<i>Начислено очков:</i> <b>{points} 🪙</b>\n\n"
                "<blockquote>Собирайте больше карточек, чтобы пополнить свою коллекцию!</blockquote>"
            ),
            parse_mode='HTML',
            reply_to_message_id=msg.message_id
        )

    await add_card_and_points(user_id, first_name, selected_card["id"], current_time, points)
    await auto_delete(msg.bot, chat_id, msg.message_id, bot_message.message_id)