"""Handler admin: CRUD drama (TMDB auto-fetch), upload episode links."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import (
    ADMIN_ID, PAGE_SIZE,
    CB_ADMIN_MENU, CB_ADMIN_ADD_DRAMA, CB_ADMIN_DRAMA_LIST,
    CB_ADMIN_DRAMA_SELECT, CB_ADMIN_DRAMA_DELETE, CB_ADMIN_DRAMA_DELETE_CONFIRM,
    CB_ADMIN_ADD_EP, CB_ADMIN_EP_LIST, CB_ADMIN_EP_DELETE, CB_ADMIN_EP_DELETE_CONFIRM,
    CB_ADMIN_STATS, CB_ADMIN_SEARCH_TMDB, CB_ADMIN_TMDB_SELECT, CB_CANCEL, CB_BACK_MAIN,
    TMDB_SEARCH, TMDB_SELECT, ADD_CONFIRM, ADD_MANUAL_TITLE,
    EP_SELECT_DRAMA, EP_NUMBER, EP_LINK,
    STATUS_ONGOING
)
from database import (
    add_drama, get_drama, list_dramas, get_all_dramas, delete_drama,
    add_episode, get_episodes, get_episode, delete_episode, get_stats
)
from utils.keyboard import (
    admin_menu_keyboard, admin_drama_detail_keyboard, admin_episode_list_keyboard,
    confirm_keyboard, cancel_keyboard, drama_list_keyboard
)
from utils.helpers import format_drama_info, esc
from tmdb import search_tmdb, get_tmdb_detail, get_genre_names


def is_admin(uid):
    return uid == ADMIN_ID


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Kamu bukan admin.")
        return
    await update.message.reply_text(
        "👑 *Panel Admin*\n━━━━━━━━━━━━━━\n\nPilih menu:",
        parse_mode="MarkdownV2", reply_markup=admin_menu_keyboard())


async def admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌ Bukan admin", show_alert=True)
        return
    await query.answer()
    await _safe_edit(query, "👑 *Panel Admin*\n━━━━━━━━━━━━━━\n\nPilih menu:", admin_menu_keyboard())


# ========================
#   STATS
# ========================

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌ Bukan admin", show_alert=True)
        return
    await query.answer()
    s = await get_stats()
    text = (f"📊 *Statistik Bot*\n━━━━━━━━━━━━━━\n\n"
            f"🎬 Drama: {s['dramas']}\n"
            f"📺 Episode: {s['episodes']}\n"
            f"👥 User: {s['users']}\n")
    await _safe_edit(query, esc(text.replace("*","BM")).replace("BM","*"),
        InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin", callback_data=CB_ADMIN_MENU)]]))


# ========================
#   ADD DRAMA (TMDB AUTO)
# ========================

async def add_drama_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌ Bukan admin", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    context.user_data["new_drama"] = {}
    text = ("➕ *Tambah Drama Baru*\n━━━━━━━━━━━━━━\n\n"
            "Ketik judul drama untuk dicari di TMDB:\n"
            "\\(poster, rating, genre otomatis diambil\\)\n\n"
            "Atau ketik `manual:Judul Drama` untuk input manual\\.")
    await _safe_edit(query, text, cancel_keyboard())
    return TMDB_SEARCH


async def add_drama_tmdb_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cari drama di TMDB."""
    q = update.message.text.strip()

    # Manual mode
    if q.lower().startswith("manual:"):
        title = q[7:].strip()
        if not title:
            await update.message.reply_text("❌ Judul tidak boleh kosong\\.", parse_mode="MarkdownV2",
                reply_markup=cancel_keyboard())
            return TMDB_SEARCH
        context.user_data["new_drama"] = {
            "title": title, "description": "", "genre": "", "year": "",
            "status": STATUS_ONGOING, "poster_url": "", "rating": 0, "vote_count": 0, "tmdb_id": 0
        }
        text = (f"✅ *Konfirmasi Drama*\n━━━━━━━━━━━━━━\n\n"
                f"📝 Judul: {esc(title)}\n\nSimpan?")
        await update.message.reply_text(text, parse_mode="MarkdownV2",
            reply_markup=confirm_keyboard("confirm_add_drama", CB_CANCEL))
        return ADD_CONFIRM

    # Simpan judul yang diketik user
    context.user_data["user_title"] = q

    # Search TMDB
    await update.message.reply_text("🔍 Mencari di TMDB\\.\\.\\.", parse_mode="MarkdownV2")

    # Search both TV and movie
    results = await search_tmdb(q, "tv")
    if not results:
        results = await search_tmdb(q, "movie")

    if not results:
        await update.message.reply_text(
            "😕 Tidak ditemukan di TMDB\\.\n\nCoba lagi atau ketik `manual:Judul` untuk input manual\\.",
            parse_mode="MarkdownV2", reply_markup=cancel_keyboard())
        return TMDB_SEARCH

    # Store results
    context.user_data["tmdb_results"] = results

    # Show results
    kb = []
    for i, r in enumerate(results):
        year = f" ({r['year']})" if r.get("year") else ""
        rating = f" ⭐{r['rating']:.1f}" if r.get("rating") else ""
        label = f"{r['title']}{year}{rating}"
        kb.append([InlineKeyboardButton(label, callback_data=f"tmdb_sel:{i}")])
    kb.append([InlineKeyboardButton("❌ Batal", callback_data=CB_CANCEL)])

    await update.message.reply_text(
        "🔍 *Hasil TMDB*\n━━━━━━━━━━━━━━\n\nPilih drama:",
        parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(kb))
    return TMDB_SELECT


async def add_drama_tmdb_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User pilih drama dari hasil TMDB."""
    query = update.callback_query
    await query.answer()

    if query.data == CB_CANCEL:
        return await cancel_conversation(update, context)

    idx = int(query.data.split(":")[1])
    results = context.user_data.get("tmdb_results", [])
    if idx >= len(results):
        await query.edit_message_text("❌ Error\\.", parse_mode="MarkdownV2", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END

    r = results[idx]

    # Get detail for genres
    detail = await get_tmdb_detail(r["tmdb_id"], r["media_type"])
    genres = detail.get("genres", "") if detail else ""
    if not genres and r.get("genre_ids"):
        genres = await get_genre_names(r["genre_ids"], r["media_type"])

    drama_data = {
        "title": context.user_data.get("user_title", r["title"]),  # pakai judul yang diketik user
        "original_title": r.get("original_title", ""),
        "description": r.get("overview", ""),
        "genre": genres,
        "year": r.get("year", ""),
        "status": STATUS_ONGOING,
        "poster_url": r.get("poster_url", ""),
        "rating": r.get("rating", 0),
        "vote_count": r.get("vote_count", 0),
        "tmdb_id": r.get("tmdb_id", 0),
    }
    context.user_data["new_drama"] = drama_data

    # Show preview
    rating_str = f"⭐ {esc(str(round(drama_data['rating'], 1)))}\\/10" if drama_data['rating'] else ""
    text = (f"✅ *Konfirmasi Drama*\n━━━━━━━━━━━━━━\n\n"
            f"📝 {esc(drama_data['title'])}\n"
            f"{rating_str}\n"
            f"📅 {esc(str(drama_data['year']))}\n"
            f"🎭 {esc(drama_data['genre'])}\n"
            f"🖼️ Poster: {'✅' if drama_data['poster_url'] else '❌'}\n\n"
            f"Simpan drama ini?")

    await query.edit_message_text(text, parse_mode="MarkdownV2",
        reply_markup=confirm_keyboard("confirm_add_drama", CB_CANCEL))
    return ADD_CONFIRM


async def add_drama_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == CB_CANCEL:
        return await cancel_conversation(update, context)

    d = context.user_data.pop("new_drama", {})
    context.user_data.pop("tmdb_results", None)

    drama_id = await add_drama(
        title=d.get("title", ""), original_title=d.get("original_title", ""),
        description=d.get("description", ""), genre=d.get("genre", ""),
        year=d.get("year", ""), status=d.get("status", STATUS_ONGOING),
        poster_url=d.get("poster_url", ""), rating=d.get("rating", 0),
        vote_count=d.get("vote_count", 0), tmdb_id=d.get("tmdb_id", 0))

    text = f"✅ *{esc(d.get('title',''))}* berhasil ditambahkan\\!"
    await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=admin_menu_keyboard())
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("new_drama", None)
    context.user_data.pop("new_episode", None)
    context.user_data.pop("tmdb_results", None)
    await query.edit_message_text("❌ Dibatalkan\\.", parse_mode="MarkdownV2", reply_markup=admin_menu_keyboard())
    return ConversationHandler.END


# ========================
#   MANAGE DRAMAS
# ========================

async def admin_drama_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌", show_alert=True)
        return
    await query.answer()
    page = int(query.data.split(":")[1]) if ":" in query.data else 1
    dramas, total = await list_dramas(page=page, page_size=PAGE_SIZE)
    if not dramas:
        await _safe_edit(query, "📋 Belum ada drama\\.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin", callback_data=CB_ADMIN_MENU)]]))
        return
    await _safe_edit(query, "📋 *Kelola Drama*\n━━━━━━━━━━━━━━\n\nPilih drama:",
        drama_list_keyboard(dramas, page, total, prefix=CB_ADMIN_DRAMA_SELECT))


async def admin_drama_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌", show_alert=True)
        return
    await query.answer()
    drama_id = int(query.data.split(":")[1])
    drama = await get_drama(drama_id)
    if not drama:
        await _safe_edit(query, "❌ Drama tidak ditemukan\\.", admin_menu_keyboard())
        return
    episodes = await get_episodes(drama_id)
    text = format_drama_info(drama, episode_count=len(episodes))
    text += "\n\n⚙️ Pilih aksi:"
    await _safe_edit(query, text, admin_drama_detail_keyboard(drama_id))


async def admin_drama_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌", show_alert=True)
        return
    await query.answer()
    drama_id = int(query.data.split(":")[1])
    drama = await get_drama(drama_id)
    text = f"🗑️ Hapus *{esc(drama['title'])}*?\n\n⚠️ Semua episode akan ikut terhapus\\!"
    await _safe_edit(query, text,
        confirm_keyboard(f"{CB_ADMIN_DRAMA_DELETE_CONFIRM}:{drama_id}", f"{CB_ADMIN_DRAMA_SELECT}:{drama_id}"))


async def admin_drama_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌", show_alert=True)
        return
    await query.answer()
    drama_id = int(query.data.split(":")[1])
    drama = await get_drama(drama_id)
    title = drama["title"] if drama else "Unknown"
    await delete_drama(drama_id)
    await _safe_edit(query, f"✅ *{esc(title)}* dihapus\\.", admin_menu_keyboard())


# ========================
#   EPISODE LIST (ADMIN)
# ========================

async def admin_ep_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌", show_alert=True)
        return
    await query.answer()
    drama_id = int(query.data.split(":")[1])
    drama = await get_drama(drama_id)
    episodes = await get_episodes(drama_id)
    if not episodes:
        await _safe_edit(query, f"📺 *{esc(drama['title'])}*\n\nBelum ada episode\\.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Upload Episode", callback_data=f"{CB_ADMIN_ADD_EP}:{drama_id}")],
                [InlineKeyboardButton("🔙 Kembali", callback_data=f"{CB_ADMIN_DRAMA_SELECT}:{drama_id}")]]))
        return
    await _safe_edit(query, f"📺 *{esc(drama['title'])}*\n━━━━━━━━━━━━━━\n\nKlik episode untuk hapus:",
        admin_episode_list_keyboard(episodes, drama_id))


async def admin_ep_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌", show_alert=True)
        return
    await query.answer()
    ep_id = int(query.data.split(":")[1])
    ep = await get_episode(ep_id)
    if not ep:
        await _safe_edit(query, "❌ Episode tidak ditemukan\\.", admin_menu_keyboard())
        return
    drama = await get_drama(ep["drama_id"])
    text = f"🗑️ Hapus Episode {ep['episode_number']} dari *{esc(drama['title'])}*?"
    await _safe_edit(query, text,
        confirm_keyboard(f"{CB_ADMIN_EP_DELETE_CONFIRM}:{ep_id}", f"{CB_ADMIN_EP_LIST}:{ep['drama_id']}"))


async def admin_ep_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌", show_alert=True)
        return
    await query.answer()
    ep_id = int(query.data.split(":")[1])
    ep = await get_episode(ep_id)
    drama_id = ep["drama_id"] if ep else 0
    await delete_episode(ep_id)
    await _safe_edit(query, "✅ Episode dihapus\\.",
        InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"{CB_ADMIN_EP_LIST}:{drama_id}")]]))


# ========================
#   ADD EPISODE (SIMPLIFIED)
# ========================

async def add_ep_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("❌", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    data = query.data.split(":")
    if len(data) > 1 and data[1]:
        drama_id = int(data[1])
        drama = await get_drama(drama_id)
        context.user_data["new_episode"] = {"drama_id": drama_id, "title": drama["title"]}
        await _safe_edit(query,
            f"📤 *Upload Episode*\n\nDrama: *{esc(drama['title'])}*\n\n📺 Masukkan nomor episode:",
            cancel_keyboard())
        return EP_NUMBER

    dramas = await get_all_dramas()
    if not dramas:
        await _safe_edit(query, "❌ Belum ada drama\\. Tambahkan dulu\\.", admin_menu_keyboard())
        return ConversationHandler.END

    kb = [[InlineKeyboardButton(d["title"], callback_data=f"epd:{d['id']}")] for d in dramas]
    kb.append([InlineKeyboardButton("❌ Batal", callback_data=CB_CANCEL)])
    await _safe_edit(query, "📤 *Upload Episode*\n━━━━━━━━━━━━━━\n\nPilih drama:", InlineKeyboardMarkup(kb))
    return EP_SELECT_DRAMA


async def add_ep_select_drama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == CB_CANCEL:
        return await cancel_conversation(update, context)
    drama_id = int(query.data.split(":")[1])
    drama = await get_drama(drama_id)
    context.user_data["new_episode"] = {"drama_id": drama_id, "title": drama["title"]}
    await query.edit_message_text(
        f"📤 *Upload Episode*\n\nDrama: *{esc(drama['title'])}*\n\n📺 Masukkan nomor episode\n\\(atau range, contoh: `1-16`\\):",
        parse_mode="MarkdownV2", reply_markup=cancel_keyboard())
    return EP_NUMBER


async def add_ep_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Support range like "1-16"
    if "-" in text:
        try:
            parts = text.split("-")
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            context.user_data["new_episode"]["ep_range"] = list(range(start, end + 1))
            context.user_data["new_episode"]["ep_index"] = 0
            ep_num = context.user_data["new_episode"]["ep_range"][0]
            context.user_data["new_episode"]["episode_number"] = ep_num
            title = context.user_data["new_episode"]["title"]
            await update.message.reply_text(
                f"📤 *{esc(title)}*\n\nEpisode *{ep_num}*\n🔗 Paste link URL:",
                parse_mode="MarkdownV2", reply_markup=cancel_keyboard())
            return EP_LINK
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Format salah\\. Contoh: `1\\-16`", parse_mode="MarkdownV2",
                reply_markup=cancel_keyboard())
            return EP_NUMBER

    try:
        ep_num = int(text)
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka\\.", parse_mode="MarkdownV2", reply_markup=cancel_keyboard())
        return EP_NUMBER

    context.user_data["new_episode"]["episode_number"] = ep_num
    title = context.user_data["new_episode"]["title"]
    await update.message.reply_text(
        f"📤 *{esc(title)}* \\- Episode *{ep_num}*\n\n🔗 Paste link URL:",
        parse_mode="MarkdownV2", reply_markup=cancel_keyboard())
    return EP_LINK


async def add_ep_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ URL harus http:// atau https://", reply_markup=cancel_keyboard())
        return EP_LINK

    ep_data = context.user_data.get("new_episode", {})
    drama_id = ep_data["drama_id"]
    ep_num = ep_data["episode_number"]

    await add_episode(drama_id, ep_num, url)

    # Check if there's a range
    ep_range = ep_data.get("ep_range")
    if ep_range:
        idx = ep_data.get("ep_index", 0) + 1
        if idx < len(ep_range):
            # Next episode in range
            ep_data["ep_index"] = idx
            next_ep = ep_range[idx]
            ep_data["episode_number"] = next_ep
            await update.message.reply_text(
                f"✅ Ep {ep_num} disimpan\\!\n\n📤 *{esc(ep_data['title'])}* \\- Episode *{next_ep}*\n🔗 Paste link URL:",
                parse_mode="MarkdownV2", reply_markup=cancel_keyboard())
            return EP_LINK
        else:
            # Range complete
            context.user_data.pop("new_episode", None)
            await update.message.reply_text(
                f"✅ Semua episode \\({ep_range[0]}\\-{ep_range[-1]}\\) berhasil disimpan\\!",
                parse_mode="MarkdownV2", reply_markup=admin_menu_keyboard())
            return ConversationHandler.END

    context.user_data.pop("new_episode", None)
    await update.message.reply_text(
        f"✅ Episode {ep_num} berhasil disimpan\\!",
        parse_mode="MarkdownV2", reply_markup=admin_menu_keyboard())
    return ConversationHandler.END


async def _safe_edit(query, text, reply_markup):
    """Edit message safely — handle photo messages."""
    try:
        await query.edit_message_text(text, parse_mode="MarkdownV2", reply_markup=reply_markup)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(text, parse_mode="MarkdownV2", reply_markup=reply_markup)
