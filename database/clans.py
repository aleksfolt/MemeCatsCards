import aiosqlite
import json
from typing import Optional, Tuple, List

from database.cards import get_user_profile_data

DATABASE = 'database.db'


async def initialize_database():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                members TEXT,
                creator INTEGER UNIQUE,
                request INTEGER DEFAULT 0
            )
        ''')
        await db.commit()


async def create_clan(clan_name: str, creator_id: int) -> Tuple[bool, str]:
    # Проверка длины названия клана
    if len(clan_name) > 10:
        return False, "⚠️ <b>Название клана не должно быть длиннее 10 символов.</b>"

    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute('SELECT id FROM clans WHERE creator = ?', (creator_id,))
        if await cursor.fetchone():
            return False, "⚠️ <b>Вы уже являетесь создателем другого клана.</b>\nВы не можете создать более одного клана."

        cursor = await db.execute('SELECT id, members FROM clans')
        clans = await cursor.fetchall()
        for _, members_json in clans:
            members = json.loads(members_json)
            if creator_id in members:
                return False, "⚠️ <b>Вы уже состоите в клане.</b>\nСначала выйдите из текущего клана."

        cursor = await db.execute('SELECT id FROM clans WHERE name = ?', (clan_name,))
        if await cursor.fetchone():
            return False, f"⚠️ <b>Клан с именем '{clan_name}' уже существует.</b>"

        members = json.dumps([creator_id])
        await db.execute('INSERT INTO clans (name, members, creator) VALUES (?, ?, ?)', (clan_name, members, creator_id))
        await db.commit()
        return True, "✅ <b>Клан успешно создан.</b>"


async def get_user_clan(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute('SELECT id, name, members, creator, request FROM clans')
        clans = await cursor.fetchall()
        for clan_id, name, members_json, creator, request in clans:
            members = json.loads(members_json)
            if user_id in members:
                return {
                    'id': clan_id,
                    'name': name,
                    'members': members,
                    'creator': creator,
                    'request': request
                }
        return None


async def leave_clan(user_id: int) -> Tuple[bool, str]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute('SELECT id FROM clans WHERE creator = ?', (user_id,))
        result = await cursor.fetchone()
        if result:
            return False, "⚠️ <b>Вы не можете выйти из клана, так как являетесь его создателем.</b>\nУдалите клан или передайте лидерство другому участнику."

        cursor = await db.execute('SELECT id, members FROM clans')
        clans = await cursor.fetchall()
        for clan_id, members_json in clans:
            members = json.loads(members_json)
            if user_id in members:
                members.remove(user_id)
                await db.execute('UPDATE clans SET members = ? WHERE id = ?', (json.dumps(members), clan_id))
                await db.commit()
                return True, "✅ <b>Вы вышли из клана.</b>"
        return False, "⚠️ <b>Вы не состоите в клане.</b>"


async def join_clan(user_id: int, clan_name: str) -> Tuple[bool, str, Optional[int]]:
    async with aiosqlite.connect(DATABASE) as db:
        user_clan = await get_user_clan(user_id)
        if user_clan:
            return False, "⚠️ <b>Вы уже состоите в клане.</b>\nСначала выйдите из текущего клана.", None

        cursor = await db.execute('SELECT id, members, request, creator FROM clans WHERE name = ?', (clan_name,))
        result = await cursor.fetchone()
        if not result:
            return False, f"⚠️ <b>Клан с именем '{clan_name}' не найден.</b>", None
        clan_id, members_json, request, creator_id = result
        members = json.loads(members_json)

        if len(members) >= 20:
            return False, "⚠️ <b>Клан уже достиг максимального количества участников (20).</b>", None

        if request == 0:
            members.append(user_id)
            await db.execute('UPDATE clans SET members = ? WHERE id = ?', (json.dumps(members), clan_id))
            await db.commit()
            return True, f"✅ <b>Вы успешно вступили в клан '{clan_name}'.</b>", None
        else:
            return True, f"📝 <b>Вы подали заявку на вступление в клан '{clan_name}'.</b>\nОжидайте решения.", creator_id


async def accept_member(clan_creator_id: int, user_id: int) -> Tuple[bool, str]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute('SELECT id, name, members, creator FROM clans WHERE creator = ?', (clan_creator_id,))
        result = await cursor.fetchone()
        if not result:
            return False, "⚠️ <b>Вы не являетесь создателем клана.</b>"
        clan_id, clan_name, members_json, creator_id = result

        if creator_id != clan_creator_id:
            return False, "⚠️ <b>Вы не являетесь создателем этого клана.</b>"

        members = json.loads(members_json)
        if user_id in members:
            return False, "⚠️ <b>Этот пользователь уже состоит в вашем клане.</b>"

        if len(members) >= 20:
            return False, "⚠️ <b>Клан уже достиг максимального количества участников (20).</b>"

        user_clan = await get_user_clan(user_id)
        if user_clan:
            return False, "⚠️ <b>Заявка истекла. Пользователь уже состоит в другом клане.</b>"

        members.append(user_id)
        await db.execute('UPDATE clans SET members = ? WHERE id = ?', (json.dumps(members), clan_id))
        await db.commit()
        return True, f"✅ <b>Пользователь успешно принят в клан '{clan_name}'.</b>"


async def reject_member(clan_creator_id: int, user_id: int) -> Tuple[bool, str]:
    return True, "❌ <b>Заявка отклонена.</b>"


async def update_clan_request_status(clan_id: int, request_status: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('UPDATE clans SET request = ? WHERE id = ?', (request_status, clan_id))
        await db.commit()


async def delete_clan(clan_id: int) -> Tuple[bool, str]:
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('DELETE FROM clans WHERE id = ?', (clan_id,))
        await db.commit()
        return True, "✅ <b>Клан успешно удален.</b>"


async def transfer_leadership(clan_id: int, new_creator_id: int) -> Tuple[bool, str]:
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('UPDATE clans SET creator = ? WHERE id = ?', (new_creator_id, clan_id))
        await db.commit()
        return True, "✅ <b>Лидерство успешно передано.</b>"


async def get_top_clans_by_points() -> List[Tuple[str, int, int]]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute('SELECT name, members FROM clans')
        clans = await cursor.fetchall()

        clan_points_list = []

        for clan_name, members_json in clans:
            members = json.loads(members_json)
            total_points = 0
            member_count = len(members)

            if member_count == 0:
                continue

            placeholders = ','.join(['?'] * member_count)
            query = f'SELECT now_points FROM user_data WHERE user_id IN ({placeholders})'
            cursor_points = await db.execute(query, members)
            points_results = await cursor_points.fetchall()
            total_points = sum([row[0] for row in points_results])

            clan_points_list.append((clan_name, member_count, total_points))

        clan_points_list.sort(key=lambda x: x[2], reverse=True)

        top_clans = clan_points_list[:10]
        return top_clans
