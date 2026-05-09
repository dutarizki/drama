"""Database handler - SQLite + aiosqlite. Simplified: no resolution, 1 episode = 1 link."""

import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "drama_bot.db")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS dramas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                original_title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                genre TEXT DEFAULT '',
                year TEXT DEFAULT '',
                status TEXT DEFAULT 'Ongoing',
                poster_url TEXT DEFAULT '',
                rating REAL DEFAULT 0,
                vote_count INTEGER DEFAULT 0,
                tmdb_id INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drama_id INTEGER NOT NULL,
                episode_number INTEGER NOT NULL,
                url TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (drama_id) REFERENCES dramas(id) ON DELETE CASCADE,
                UNIQUE(drama_id, episode_number)
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()
    finally:
        await db.close()


# =====================
#   DRAMA OPERATIONS
# =====================

async def add_drama(title, original_title="", description="", genre="", year="",
                    status="Ongoing", poster_url="", rating=0, vote_count=0, tmdb_id=0):
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO dramas (title, original_title, description, genre, year,
               status, poster_url, rating, vote_count, tmdb_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, original_title, description, genre, year, status, poster_url, rating, vote_count, tmdb_id)
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_drama(drama_id):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM dramas WHERE id = ?", (drama_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def list_dramas(page=1, page_size=8):
    db = await get_db()
    try:
        offset = (page - 1) * page_size
        cursor = await db.execute("SELECT COUNT(*) as count FROM dramas")
        row = await cursor.fetchone()
        total = row["count"]
        cursor = await db.execute(
            "SELECT * FROM dramas ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows], total
    finally:
        await db.close()


async def search_dramas(query):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM dramas WHERE title LIKE ? OR original_title LIKE ? ORDER BY title",
            (f"%{query}%", f"%{query}%"))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_dramas_by_genre(genre):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM dramas WHERE genre LIKE ? ORDER BY title", (f"%{genre}%",))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_all_genres():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT DISTINCT genre FROM dramas WHERE genre != '' ORDER BY genre")
        rows = await cursor.fetchall()
        genres = set()
        for row in rows:
            for g in row["genre"].split(","):
                g = g.strip()
                if g:
                    genres.add(g)
        return sorted(genres)
    finally:
        await db.close()


async def delete_drama(drama_id):
    db = await get_db()
    try:
        await db.execute("DELETE FROM dramas WHERE id = ?", (drama_id,))
        await db.commit()
    finally:
        await db.close()


async def get_all_dramas():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id, title FROM dramas ORDER BY title")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


# =====================
#   EPISODE OPERATIONS
# =====================

async def add_episode(drama_id, episode_number, url=""):
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO episodes (drama_id, episode_number, url) VALUES (?, ?, ?)
               ON CONFLICT(drama_id, episode_number) DO UPDATE SET url = excluded.url""",
            (drama_id, episode_number, url))
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_episodes(drama_id):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM episodes WHERE drama_id = ? ORDER BY episode_number", (drama_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_episode(episode_id):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def delete_episode(episode_id):
    db = await get_db()
    try:
        await db.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))
        await db.commit()
    finally:
        await db.close()


# =====================
#   USER TRACKING
# =====================

async def track_user(telegram_id, username="", first_name=""):
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO users (telegram_id, username, first_name)
               VALUES (?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET
               username = excluded.username,
               first_name = excluded.first_name,
               last_seen = CURRENT_TIMESTAMP""",
            (telegram_id, username, first_name))
        await db.commit()
    finally:
        await db.close()


async def get_stats():
    db = await get_db()
    try:
        stats = {}
        for table, key in [("dramas", "dramas"), ("episodes", "episodes"), ("users", "users")]:
            cursor = await db.execute(f"SELECT COUNT(*) as count FROM {table}")
            row = await cursor.fetchone()
            stats[key] = row["count"]
        return stats
    finally:
        await db.close()
