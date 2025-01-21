import aiosqlite

DB_PATH = 'database.db'


async def init_cd_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cooldown (
                chat_id INTEGER PRIMARY KEY,
                on_or_off TEXT DEFAULT 'off',
                cooldown INTEGER
            )
        ''')
        await db.commit()


async def get_cooldown_state(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT on_or_off FROM cooldown WHERE chat_id = ?', (chat_id,))
        result = await cursor.fetchone()
        await cursor.close()
        return result[0] if result else "off"


async def toggle_cooldown_state(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT on_or_off FROM cooldown WHERE chat_id = ?', (chat_id,))
        result = await cursor.fetchone()
        await cursor.close()

        new_state = "off" if result and result[0] == "on" else "on"

        await db.execute('''
            INSERT INTO cooldown (chat_id, on_or_off) VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET on_or_off = ?
        ''', (chat_id, new_state, new_state))
        await db.commit()

    return new_state


async def set_cooldown_time(chat_id, minutes):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO cooldown (chat_id, cooldown) VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET cooldown = ?
        ''', (chat_id, minutes, minutes))
        await db.commit()


async def get_cooldown_time(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT cooldown FROM cooldown WHERE chat_id = ?', (chat_id,))
        result = await cursor.fetchone()
        await cursor.close()
        return int(result[0]) if result else 0
