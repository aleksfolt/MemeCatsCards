import json
import aiosqlite
import datetime
import os

DB_PATH = 'database.db'

cards_data = {"cards": []}

if os.path.exists('cards.json'):
    try:
        with open('cards.json', 'r', encoding='utf-8') as f:
            cards_data = json.load(f)
    except json.JSONDecodeError:
        print("Ошибка декодирования JSON. Файл 'cards.json' может быть поврежден.")
else:
    print("Файл 'cards.json' не найден.")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                cards TEXT DEFAULT '[]',
                all_points INTEGER DEFAULT 0,
                now_points INTEGER DEFAULT 0,
                last_received_at TEXT
            )
        ''')
        await db.commit()


async def get_last_card_time(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT last_received_at FROM user_data WHERE user_id = ?', (user_id,))
        result = await cursor.fetchone()
        await cursor.close()
        if result and result[0]:
            return datetime.datetime.fromisoformat(result[0])
        else:
            return None


async def add_card_and_points(user_id, first_name, card_id, timestamp, points):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT cards, all_points, now_points FROM user_data WHERE user_id = ?', (user_id,))
        result = await cursor.fetchone()

        if result is None:
            cards = json.dumps([card_id])
            await db.execute('''
                INSERT INTO user_data (user_id, first_name, cards, all_points, now_points, last_received_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, first_name, cards, points, points, timestamp.isoformat()))
        else:
            cards, all_points, now_points = result
            cards_list = json.loads(cards)

            if card_id not in cards_list:
                cards_list.append(card_id)
                cards = json.dumps(cards_list)

            await db.execute('''
                UPDATE user_data
                SET first_name = ?,
                    cards = ?,
                    all_points = all_points + ?,
                    now_points = now_points + ?,
                    last_received_at = ?
                WHERE user_id = ?
            ''', (first_name, cards, points, points, timestamp.isoformat(), user_id))

        await db.commit()


async def has_user_card(user_id, card_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT cards FROM user_data WHERE user_id = ?', (user_id,))
        result = await cursor.fetchone()
        print(result)
        await cursor.close()
        if result:
            cards = json.loads(result[0])
            print(cards)
            return card_id in cards
        return False


async def reset_cooldown(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE user_data SET last_received_at = NULL WHERE user_id = ?', (user_id,))
        await db.commit()


async def get_user_profile_data(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT cards, now_points, all_points FROM user_data WHERE user_id = ?', (user_id,))
        result = await cursor.fetchone()
        await cursor.close()

        if result:
            cards = json.loads(result[0])
            now_points = result[1]
            all_points = result[2]
            return {
                "cards": cards,
                "now_points": now_points,
                "all_points": all_points
            }
        return None


async def get_top_users_by_cards():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT user_id, first_name, cards FROM user_data')
        all_users = await cursor.fetchall()
        user_card_counts = []
        for user_id, first_name, cards_json in all_users:
            cards_list = json.loads(cards_json)
            card_count = len(cards_list)
            user_card_counts.append((user_id, first_name, card_count))
        user_card_counts.sort(key=lambda x: x[2], reverse=True)
        top_users = user_card_counts[:10]
        return top_users


async def get_top_users_by_now_points():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT user_id, first_name, now_points FROM user_data ORDER BY now_points DESC LIMIT 10')
        result = await cursor.fetchall()
        return result


async def get_top_users_by_all_points():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT user_id, first_name, all_points FROM user_data ORDER BY all_points DESC LIMIT 10')
        result = await cursor.fetchall()
        return result