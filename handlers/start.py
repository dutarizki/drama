"""Handler /start dan menu utama."""

from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboard import main_menu_keyboard
from database import track_user


WELCOME = (
    "🎬 *Selamat Datang di Drama Bot\\!*\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Temukan dan tonton drama favoritmu di sini\\! 🍿\n\n"
    "Pilih menu di bawah:"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await track_user(user.id, user.username or "", user.first_name or "")
    await update.message.reply_text(WELCOME, parse_mode="MarkdownV2", reply_markup=main_menu_keyboard())


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Clear any conversation state
    context.user_data.pop("awaiting_search", None)
    await query.edit_message_text(WELCOME, parse_mode="MarkdownV2", reply_markup=main_menu_keyboard())
