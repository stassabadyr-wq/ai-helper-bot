import aiosqlite
from datetime import datetime
from config import DB_PATH


async def init_db():
    """Создаёт таблицы, если их ещё нет. Вызывается один раз при старте бота."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS leads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                name        TEXT,
                contact     TEXT,
                message     TEXT,
                status      TEXT DEFAULT 'new',
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                role        TEXT,
                content     TEXT,
                created_at  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_messages_user
                ON messages(user_id, id DESC);

            CREATE INDEX IF NOT EXISTS idx_leads_status
                ON leads(status, id DESC);
        """)
        await db.commit()


# ---------- Пользователи ----------

async def save_user(user_id: int, username: str | None, full_name: str):
    """Сохраняет или обновляет пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (user_id, username, full_name, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 username = excluded.username,
                 full_name = excluded.full_name""",
            (
                user_id,
                username,
                full_name,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        await db.commit()


# ---------- Заявки ----------

async def save_lead(user_id: int, name: str, contact: str, message: str) -> int:
    """Создаёт новую заявку и возвращает её ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO leads (user_id, name, contact, message, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                user_id,
                name,
                contact,
                message,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        await db.commit()
        return cur.lastrowid


async def get_recent_leads(limit: int = 10) -> list[tuple]:
    """Возвращает последние N заявок для админ-панели."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT id, name, contact, message, status, created_at
               FROM leads
               ORDER BY id DESC
               LIMIT ?""",
            (limit,),
        )
        return await cur.fetchall()


async def update_lead_status(lead_id: int, status: str):
    """Меняет статус заявки (например, 'new' → 'done')."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE leads SET status = ? WHERE id = ?",
            (status, lead_id),
        )
        await db.commit()


# ---------- История AI-диалогов ----------

async def save_message(user_id: int, role: str, content: str):
    """Сохраняет одно сообщение диалога (role: 'user' или 'assistant')."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO messages (user_id, role, content, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                user_id,
                role,
                content,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        await db.commit()


async def get_history(user_id: int, limit: int = 8) -> list[dict]:
    """Возвращает последние N сообщений пользователя в формате OpenAI API."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT role, content
               FROM messages
               WHERE user_id = ?
               ORDER BY id DESC
               LIMIT ?""",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        # Разворачиваем — нам нужен хронологический порядок
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


# ---------- Статистика ----------

async def get_stats() -> dict:
    """Возвращает сводку для админ-панели."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM leads") as c:
            leads = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM leads WHERE status = 'new'"
        ) as c:
            new_leads = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM messages WHERE role = 'user'"
        ) as c:
            messages = (await c.fetchone())[0]

    return {
        "users": users,
        "leads": leads,
        "new_leads": new_leads,
        "messages": messages,
    }