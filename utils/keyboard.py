"""Keyboard builder utilities — simplified, no resolution."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import (
    CB_DRAMA_LIST, CB_DRAMA_VIEW, CB_EPISODE_LIST, CB_WATCH,
    CB_GENRE_LIST, CB_GENRE_DRAMAS, CB_SEARCH, CB_BACK_MAIN,
    CB_ADMIN_MENU, CB_ADMIN_ADD_DRAMA, CB_ADMIN_DRAMA_LIST,
    CB_ADMIN_DRAMA_SELECT, CB_ADMIN_DRAMA_DELETE, CB_ADMIN_DRAMA_DELETE_CONFIRM,
    CB_ADMIN_ADD_EP, CB_ADMIN_EP_LIST, CB_ADMIN_EP_DELETE, CB_ADMIN_EP_DELETE_CONFIRM,
    CB_ADMIN_STATS, CB_CANCEL,
    PAGE_SIZE, STATUS_ONGOING
)


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 Daftar Drama", callback_data=f"{CB_DRAMA_LIST}:1")],
        [InlineKeyboardButton("🔍 Cari Drama", callback_data=CB_SEARCH)],
        [InlineKeyboardButton("🎭 Genre", callback_data=CB_GENRE_LIST)],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Drama Baru", callback_data=CB_ADMIN_ADD_DRAMA)],
        [InlineKeyboardButton("📤 Upload Episode", callback_data=CB_ADMIN_ADD_EP)],
        [InlineKeyboardButton("📋 Kelola Drama", callback_data=f"{CB_ADMIN_DRAMA_LIST}:1")],
        [InlineKeyboardButton("📊 Statistik", callback_data=CB_ADMIN_STATS)],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data=CB_BACK_MAIN)],
    ]
    return InlineKeyboardMarkup(keyboard)


def drama_list_keyboard(dramas, page, total, page_size=PAGE_SIZE, prefix=CB_DRAMA_VIEW, admin=False):
    keyboard = []
    for drama in dramas:
        emoji = "🟢" if drama.get("status") == STATUS_ONGOING else "🔵"
        rating = drama.get("rating", 0)
        star = f" ⭐{rating:.1f}" if rating else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {drama['title']}{star}",
                callback_data=f"{prefix}:{drama['id']}")
        ])

    total_pages = max(1, (total + page_size - 1) // page_size)
    nav_buttons = []
    list_prefix = CB_ADMIN_DRAMA_LIST if admin else CB_DRAMA_LIST

    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{list_prefix}:{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"{list_prefix}:{page + 1}"))
    if total_pages > 1:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=CB_BACK_MAIN)])
    return InlineKeyboardMarkup(keyboard)


def drama_detail_keyboard(drama_id, has_episodes=True):
    keyboard = []
    if has_episodes:
        keyboard.append([InlineKeyboardButton("📺 Lihat Episode", callback_data=f"{CB_EPISODE_LIST}:{drama_id}:1")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Daftar", callback_data=f"{CB_DRAMA_LIST}:1")])
    return InlineKeyboardMarkup(keyboard)


def episode_list_keyboard(episodes, drama_id, page=1, page_size=12):
    """Episode list — klik langsung play (kirim link)."""
    keyboard = []
    total = len(episodes)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    page_episodes = episodes[start:end]

    # 3 episodes per row
    row = []
    for ep in page_episodes:
        row.append(InlineKeyboardButton(
            f"▶️ Ep {ep['episode_number']}",
            callback_data=f"{CB_WATCH}:{ep['id']}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    if total_pages > 1:
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"{CB_EPISODE_LIST}:{drama_id}:{page - 1}"))
        nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"{CB_EPISODE_LIST}:{drama_id}:{page + 1}"))
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Drama", callback_data=f"{CB_DRAMA_VIEW}:{drama_id}")])
    return InlineKeyboardMarkup(keyboard)


def genre_list_keyboard(genres):
    keyboard = []
    row = []
    for genre in genres:
        row.append(InlineKeyboardButton(f"🏷️ {genre}", callback_data=f"{CB_GENRE_DRAMAS}:{genre}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=CB_BACK_MAIN)])
    return InlineKeyboardMarkup(keyboard)


def search_result_keyboard(dramas):
    keyboard = []
    for drama in dramas[:15]:
        emoji = "🟢" if drama.get("status") == STATUS_ONGOING else "🔵"
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {drama['title']}", callback_data=f"{CB_DRAMA_VIEW}:{drama['id']}")])
    keyboard.append([InlineKeyboardButton("🏠 Menu Utama", callback_data=CB_BACK_MAIN)])
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(yes_data, no_data="cancel"):
    keyboard = [[
        InlineKeyboardButton("✅ Ya", callback_data=yes_data),
        InlineKeyboardButton("❌ Batal", callback_data=no_data),
    ]]
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data=CB_CANCEL)]])


def admin_drama_detail_keyboard(drama_id):
    keyboard = [
        [InlineKeyboardButton("📤 Upload Episode", callback_data=f"{CB_ADMIN_ADD_EP}:{drama_id}")],
        [InlineKeyboardButton("📺 Lihat Episode", callback_data=f"{CB_ADMIN_EP_LIST}:{drama_id}")],
        [InlineKeyboardButton("🗑️ Hapus Drama", callback_data=f"{CB_ADMIN_DRAMA_DELETE}:{drama_id}")],
        [InlineKeyboardButton("🔙 Kembali", callback_data=f"{CB_ADMIN_DRAMA_LIST}:1")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_episode_list_keyboard(episodes, drama_id):
    keyboard = []
    for ep in episodes:
        keyboard.append([InlineKeyboardButton(
            f"🗑️ Ep {ep['episode_number']}",
            callback_data=f"{CB_ADMIN_EP_DELETE}:{ep['id']}")])
    keyboard.append([InlineKeyboardButton("📤 Upload Episode", callback_data=f"{CB_ADMIN_ADD_EP}:{drama_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data=f"{CB_ADMIN_DRAMA_SELECT}:{drama_id}")])
    return InlineKeyboardMarkup(keyboard)
