"""
Telegram Drama Bot — Entry point.
Supports both polling (local) and webhook (Render.com).
"""

import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)
from config import (
    BOT_TOKEN, MODE, PORT, RENDER_EXTERNAL_URL, WEBHOOK_SECRET,
    CB_DRAMA_LIST, CB_DRAMA_VIEW, CB_EPISODE_LIST, CB_WATCH,
    CB_GENRE_LIST, CB_GENRE_DRAMAS, CB_SEARCH, CB_BACK_MAIN,
    CB_ADMIN_MENU, CB_ADMIN_ADD_DRAMA, CB_ADMIN_DRAMA_LIST,
    CB_ADMIN_DRAMA_SELECT, CB_ADMIN_DRAMA_DELETE, CB_ADMIN_DRAMA_DELETE_CONFIRM,
    CB_ADMIN_ADD_EP, CB_ADMIN_EP_LIST, CB_ADMIN_EP_DELETE, CB_ADMIN_EP_DELETE_CONFIRM,
    CB_ADMIN_STATS, CB_CANCEL,
    TMDB_SEARCH, TMDB_SELECT, ADD_CONFIRM,
    EP_SELECT_DRAMA, EP_NUMBER, EP_LINK, SEARCH_QUERY
)
from database import init_db
from handlers.start import start_command, back_to_main
from handlers.user import (
    drama_list_callback, drama_view_callback, episode_list_callback,
    watch_callback, genre_list_callback, genre_dramas_callback,
    search_callback, search_query_handler, noop_callback
)
from handlers.admin import (
    admin_command, admin_menu_callback, stats_callback,
    add_drama_start, add_drama_tmdb_search, add_drama_tmdb_select, add_drama_confirm,
    cancel_conversation,
    admin_drama_list_callback, admin_drama_select_callback,
    admin_drama_delete_callback, admin_drama_delete_confirm,
    admin_ep_list_callback, admin_ep_delete_callback, admin_ep_delete_confirm,
    add_ep_start, add_ep_select_drama, add_ep_number, add_ep_link
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_application(app):
    """Register all handlers to the application."""
    # --- Conversation: Add Drama (TMDB) ---
    add_drama_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_drama_start, pattern=f"^{CB_ADMIN_ADD_DRAMA}$")],
        states={
            TMDB_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_drama_tmdb_search)],
            TMDB_SELECT: [CallbackQueryHandler(add_drama_tmdb_select, pattern=r"^(tmdb_sel:|cancel)")],
            ADD_CONFIRM: [CallbackQueryHandler(add_drama_confirm, pattern=r"^(confirm_add_drama|cancel)$")],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern=f"^{CB_CANCEL}$"),
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        ],
        per_message=False,
    )

    # --- Conversation: Add Episode ---
    add_ep_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_ep_start, pattern=f"^{CB_ADMIN_ADD_EP}")],
        states={
            EP_SELECT_DRAMA: [CallbackQueryHandler(add_ep_select_drama, pattern=r"^(epd:|cancel)")],
            EP_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ep_number)],
            EP_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ep_link)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern=f"^{CB_CANCEL}$"),
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        ],
        per_message=False,
    )

    # --- Conversation: Search ---
    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_callback, pattern=f"^{CB_SEARCH}$")],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_query_handler)],
        },
        fallbacks=[
            CallbackQueryHandler(back_to_main, pattern=f"^{CB_BACK_MAIN}$"),
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        ],
        per_message=False,
    )

    # Register conversations first
    app.add_handler(add_drama_conv)
    app.add_handler(add_ep_conv)
    app.add_handler(search_conv)

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))

    # Callbacks
    app.add_handler(CallbackQueryHandler(back_to_main, pattern=f"^{CB_BACK_MAIN}$"))
    app.add_handler(CallbackQueryHandler(drama_list_callback, pattern=f"^{CB_DRAMA_LIST}:"))
    app.add_handler(CallbackQueryHandler(drama_view_callback, pattern=f"^{CB_DRAMA_VIEW}:"))
    app.add_handler(CallbackQueryHandler(episode_list_callback, pattern=f"^{CB_EPISODE_LIST}:"))
    app.add_handler(CallbackQueryHandler(watch_callback, pattern=f"^{CB_WATCH}:"))
    app.add_handler(CallbackQueryHandler(genre_list_callback, pattern=f"^{CB_GENRE_LIST}$"))
    app.add_handler(CallbackQueryHandler(genre_dramas_callback, pattern=f"^{CB_GENRE_DRAMAS}:"))

    # Admin callbacks
    app.add_handler(CallbackQueryHandler(admin_menu_callback, pattern=f"^{CB_ADMIN_MENU}$"))
    app.add_handler(CallbackQueryHandler(stats_callback, pattern=f"^{CB_ADMIN_STATS}$"))
    app.add_handler(CallbackQueryHandler(admin_drama_list_callback, pattern=f"^{CB_ADMIN_DRAMA_LIST}:"))
    app.add_handler(CallbackQueryHandler(admin_drama_select_callback, pattern=f"^{CB_ADMIN_DRAMA_SELECT}:"))
    app.add_handler(CallbackQueryHandler(admin_drama_delete_callback, pattern=f"^{CB_ADMIN_DRAMA_DELETE}:"))
    app.add_handler(CallbackQueryHandler(admin_drama_delete_confirm, pattern=f"^{CB_ADMIN_DRAMA_DELETE_CONFIRM}:"))
    app.add_handler(CallbackQueryHandler(admin_ep_list_callback, pattern=f"^{CB_ADMIN_EP_LIST}:"))
    app.add_handler(CallbackQueryHandler(admin_ep_delete_callback, pattern=f"^{CB_ADMIN_EP_DELETE}:"))
    app.add_handler(CallbackQueryHandler(admin_ep_delete_confirm, pattern=f"^{CB_ADMIN_EP_DELETE_CONFIRM}:"))
    app.add_handler(CallbackQueryHandler(noop_callback, pattern="^noop$"))


def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        print("ERROR: Set BOT_TOKEN di file .env!")
        print("  1. Copy .env.example ke .env")
        print("  2. Isi BOT_TOKEN dari @BotFather")
        print("  3. Isi ADMIN_ID dari @userinfobot")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    setup_application(app)

    # Start bot
    if MODE == "webhook":
        # Webhook mode for Render.com
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        logger.info(f"Starting webhook mode on port {PORT}")
        logger.info(f"Webhook URL: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
    else:
        # Polling mode for local development
        logger.info("Starting polling mode...")
        app.run_polling(drop_pending_updates=True)


async def post_init(application):
    await init_db()
    logger.info("Database initialized")


if __name__ == "__main__":
    main()
