"""Handler user: browse, search, watch. Simplified - no resolution, direct link."""

import urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import (
    CB_DRAMA_LIST, CB_DRAMA_VIEW, CB_EPISODE_LIST, CB_WATCH,
    CB_GENRE_LIST, CB_GENRE_DRAMAS, CB_SEARCH, CB_BACK_MAIN,
    PAGE_SIZE, SEARCH_QUERY
)
from database import (
    list_dramas, get_drama, get_episodes, get_episode,
    search_dramas, get_dramas_by_genre, get_all_genres, track_user
)
from utils.keyboard import (
    drama_list_keyboard, drama_detail_keyboard, episode_list_keyboard,
    genre_list_keyboard, search_result_keyboard
)
from utils.helpers import format_drama_info, esc

PLAYER_BASE_URL = "https://drama-bot-production.up.railway.app/watch"


async def drama_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1]) if ":" in query.data else 1
    dramas, total = await list_dramas(page=page, page_size=PAGE_SIZE)
    if not dramas:
        await query.edit_message_text(
            "📋 *Daftar Drama*\n\n😕 Belum ada drama\\.",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data=CB_BACK_MAIN)]]))
        return
    text = f"📋 *Daftar Drama*\n━━━━━━━━━━━━━━\n\nTotal: {esc(str(total))} drama\n"
    await query.edit_message_text(text, parse_mode="MarkdownV2",
        reply_markup=drama_list_keyboard(dramas, page, total))


async def drama_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    drama_id = int(query.data.split(":")[1])
    drama = await get_drama(drama_id)
    if not drama:
        await query.edit_message_text("❌ Drama tidak ditemukan\\.", parse_mode="MarkdownV2")
        return
    episodes = await get_episodes(drama_id)
    text = format_drama_info(drama, episode_count=len(episodes))
    kb = drama_detail_keyboard(drama_id, has_episodes=len(episodes) > 0)
    poster = drama.get("poster_url", "")
    if poster:
        try:
            await query.message.delete()
            await query.message.chat.send_photo(
                photo=poster, caption=text, parse_mode="MarkdownV2", reply_markup=kb)
            return
        except Exception:
            pass
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=kb)


async def episode_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")
    drama_id = int(data[1])
    page = int(data[2]) if len(data) > 2 else 1
    drama = await get_drama(drama_id)
    episodes = await get_episodes(drama_id)
    if not episodes:
        await _safe_edit(query,
            f"📺 *{esc(drama['title'])}*\n\n😕 Belum ada episode\\.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"{CB_DRAMA_VIEW}:{drama_id}")]]))
        return
    text = f"📺 *{esc(drama['title'])}*\n━━━━━━━━━━━━━━\n\nPilih episode untuk menonton:\n"
    await _safe_edit(query, text, episode_list_keyboard(episodes, drama_id, page))


async def watch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Klik episode → buka via Railway player (fullscreen, no ads)."""
    query = update.callback_query
    await query.answer()
    ep_id = int(query.data.split(":")[1])
    ep = await get_episode(ep_id)
    if not ep or not ep.get("url"):
        await query.answer("❌ Link belum tersedia", show_alert=True)
        return
    drama = await get_drama(ep["drama_id"])
    drama_title = drama["title"] if drama else "Drama"
    ep_num = ep['episode_number']

    player_url = (
        f"{PLAYER_BASE_URL}"
        f"?src={urllib.parse.quote(ep['url'], safe='')}"
        f"&title={urllib.parse.quote(drama_title, safe='')}"
        f"&ep={ep_num}"
    )

    title_esc = esc(drama_title)
    text = (f"🎬 *{title_esc}*\n"
            f"📺 Episode {ep_num}\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"Tap tombol di bawah untuk nonton fullscreen\\!")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Tonton Sekarang", url=player_url)],
        [InlineKeyboardButton("🔙 Daftar Episode", callback_data=f"{CB_EPISODE_LIST}:{ep['drama_id']}:1")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data=CB_BACK_MAIN)],
    ])
    await query.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=kb, disable_web_page_preview=True)


async def genre_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    genres = await get_all_genres()
    if not genres:
        await query.edit_message_text("🎭 *Genre*\n\n😕 Belum ada genre\\.",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data=CB_BACK_MAIN)]]))
        return
    await query.edit_message_text("🎭 *Genre*\n━━━━━━━━━━━━━━\n\nPilih genre:\n",
        parse_mode="MarkdownV2", reply_markup=genre_list_keyboard(genres))


async def genre_dramas_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    genre = query.data.split(":")[1] if ":" in query.data else ""
    dramas = await get_dramas_by_genre(genre)
    if not dramas:
        await query.edit_message_text(f"🎭 *{esc(genre)}*\n\n😕 Tidak ada drama\\.",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Genre", callback_data=CB_GENRE_LIST)]]))
        return
    text = f"🎭 *{esc(genre)}*\n\nDitemukan {esc(str(len(dramas)))} drama:\n"
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=search_result_keyboard(dramas))


async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔍 *Cari Drama*\n━━━━━━━━━━━━━━\n\nKetik judul drama:",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data=CB_BACK_MAIN)]]))
    context.user_data["awaiting_search"] = True
    return SEARCH_QUERY


async def search_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_search"):
        return
    q = update.message.text.strip()
    context.user_data["awaiting_search"] = False
    user = update.effective_user
    await track_user(user.id, user.username or "", user.first_name or "")
    dramas = await search_dramas(q)
    if not dramas:
        await update.message.reply_text(
            f"🔍 *{esc(q)}*\n\n😕 Tidak ditemukan\\.",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Cari Lagi", callback_data=CB_SEARCH)],
                [InlineKeyboardButton("🏠 Menu", callback_data=CB_BACK_MAIN)]]))
        return ConversationHandler.END
    await update.message.reply_text(
        f"🔍 *{esc(q)}*\n\nDitemukan {esc(str(len(dramas)))} drama:\n",
        parse_mode="MarkdownV2", reply_markup=search_result_keyboard(dramas))
    return ConversationHandler.END


async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


async def _safe_edit(query, text, reply_markup):
    try:
        await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=reply_markup)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(text, parse_mode="MarkdownV2", reply_markup=reply_markup)
