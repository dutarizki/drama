"""Database handler - PostgreSQL + asyncpg untuk Supabase."""

import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL", "")


async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    return conn


async def init_db():
    conn = await get_db()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS dramas (
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                drama_id INTEGER NOT NULL REFERENCES dramas(id) ON DELETE CASCADE,
                episode_number INTEGER NOT NULL,
                url TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(drama_id, episode_number)
            );

            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    finally:
        await conn.close()


# =====================
#   DRAMA OPERATIONS
# =====================

async def add_drama(title, original_title="", description="", genre="", year="",
                    status="Ongoing", poster_url="", rating=0, vote_count=0, tmdb_id=0):
    conn = await get_db()
    try:
        row = await conn.fetchrow(
            """INSERT INTO dramas (title, original_title, description, genre, year,
               status, poster_url, rating, vote_count, tmdb_id)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING id""",
            title, original_title, description, genre, year,
            status, poster_url, rating, vote_count, tmdb_id)
        return row["id"]
    finally:
        await conn.close()


async def get_drama(drama_id):
    conn = await get_db()
    try:
        row = await conn.fetchrow("SELECT * FROM dramas WHERE id = $1", drama_id)
        return dict(row) if row else None
    finally:
        await conn.close()


async def list_dramas(page=1, page_size=8):
    conn = await get_db()
    try:
        offset = (page - 1) * page_size
        total = await conn.fetchval("SELECT COUNT(*) FROM dramas")
        rows = await conn.fetch(
            "SELECT * FROM dramas ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            page_size, offset)
        return [dict(r) for r in rows], total
    finally:
        await conn.close()


async def search_dramas(query):
    conn = await get_db()
    try:
        rows = await conn.fetch(
            "SELECT * FROM dramas WHERE title ILIKE $1 OR original_title ILIKE $1 ORDER BY title",
            f"%{query}%")
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_dramas_by_genre(genre):
    conn = await get_db()
    try:
        rows = await conn.fetch(
            "SELECT * FROM dramas WHERE genre ILIKE $1 ORDER BY title", f"%{genre}%")
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_all_genres():
    conn = await get_db()
    try:
        rows = await conn.fetch("SELECT DISTINCT genre FROM dramas WHERE genre != '' ORDER BY genre")
        genres = set()
        for row in rows:
            for g in row["genre"].split(","):
                g = g.strip()
                if g:
                    genres.add(g)
        return sorted(genres)
    finally:
        await conn.close()


async def delete_drama(drama_id):
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM dramas WHERE id = $1", drama_id)
    finally:
        await conn.close()


async def get_all_dramas():
    conn = await get_db()
    try:
        rows = await conn.fetch("SELECT id, title FROM dramas ORDER BY title")
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# =====================
#   EPISODE OPERATIONS
# =====================

async def add_episode(drama_id, episode_number, url=""):
    conn = await get_db()
    try:
        row = await conn.fetchrow(
            """INSERT INTO episodes (drama_id, episode_number, url) VALUES ($1,$2,$3)
               ON CONFLICT(drama_id, episode_number) DO UPDATE SET url = EXCLUDED.url
               RETURNING id""",
            drama_id, episode_number, url)
        return row["id"]
    finally:
        await conn.close()


async def get_episodes(drama_id):
    conn = await get_db()
    try:
        rows = await conn.fetch(
            "SELECT * FROM episodes WHERE drama_id = $1 ORDER BY episode_number", drama_id)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def get_episode(episode_id):
    conn = await get_db()
    try:
        row = await conn.fetchrow("SELECT * FROM episodes WHERE id = $1", episode_id)
        return dict(row) if row else None
    finally:
        await conn.close()


async def delete_episode(episode_id):
    conn = await get_db()
    try:
        await conn.execute("DELETE FROM episodes WHERE id = $1", episode_id)
    finally:
        await conn.close()


# =====================
#   USER TRACKING
# =====================

async def track_user(telegram_id, username="", first_name=""):
    conn = await get_db()
    try:
        await conn.execute(
            """INSERT INTO users (telegram_id, username, first_name)
               VALUES ($1,$2,$3)
               ON CONFLICT(telegram_id) DO UPDATE SET
               username = EXCLUDED.username,
               first_name = EXCLUDED.first_name,
               last_seen = CURRENT_TIMESTAMP""",
            telegram_id, username, first_name)
    finally:
        await conn.close()


async def get_stats():
    conn = await get_db()
    try:
        dramas = await conn.fetchval("SELECT COUNT(*) FROM dramas")
        episodes = await conn.fetchval("SELECT COUNT(*) FROM episodes")
        users = await conn.fetchval("SELECT COUNT(*) FROM users")
        return {"dramas": dramas, "episodes": episodes, "users": users}
    finally:
        await conn.close()
