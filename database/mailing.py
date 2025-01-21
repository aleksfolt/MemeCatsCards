import aiosqlite


# создание таблицы
async def create_table():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                chat_id INTEGER UNIQUE
            )
        """)
        await db.commit()


# добавление пользователя
async def add_user(user_id: int):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR IGNORE INTO chat_users (user_id) VALUES (?)", (user_id,))
        await db.commit()


# добавление чата
async def add_chat(chat_id: int):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR IGNORE INTO chat_users (chat_id) VALUES (?)", (chat_id,))
        await db.commit()


async def get_stats():
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM chat_users")
        users_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(DISTINCT chat_id) FROM chat_users")
        chats_count = (await cursor.fetchone())[0]

    return users_count, chats_count