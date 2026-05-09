"""Konfigurasi bot."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Bot Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8742323386:AAE3t05y7BXIYEavfas8W33XqEDuIucEb3Y")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5232044579"))
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "59c4c22abeee90b431ba0c918e194622")

# --- Render.com Webhook Config ---
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")  # Auto-set by Render
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "drama-bot-secret-token")
MODE = os.getenv("MODE", "polling")  # "polling" for local, "webhook" for Render

# --- TMDB ---
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

# --- Constants ---
PAGE_SIZE = 8

# --- Status Drama ---
STATUS_ONGOING = "Ongoing"
STATUS_COMPLETED = "Completed"

# --- Callback Prefixes ---
CB_DRAMA_LIST = "dl"
CB_DRAMA_VIEW = "dv"
CB_EPISODE_LIST = "el"
CB_WATCH = "wt"             # Watch = langsung kirim link
CB_GENRE_LIST = "gl"
CB_GENRE_DRAMAS = "gd"
CB_SEARCH = "sr"
CB_BACK_MAIN = "bm"

# Admin callbacks
CB_ADMIN_MENU = "am"
CB_ADMIN_ADD_DRAMA = "aad"
CB_ADMIN_SEARCH_TMDB = "ast_tmdb"
CB_ADMIN_TMDB_SELECT = "ats"
CB_ADMIN_DRAMA_LIST = "adl"
CB_ADMIN_DRAMA_SELECT = "ads"
CB_ADMIN_DRAMA_DELETE = "add"
CB_ADMIN_DRAMA_DELETE_CONFIRM = "addc"
CB_ADMIN_ADD_EP = "aae"
CB_ADMIN_EP_LIST = "ael"
CB_ADMIN_EP_DELETE = "aed"
CB_ADMIN_EP_DELETE_CONFIRM = "aedc"
CB_ADMIN_STATS = "ast"
CB_CANCEL = "cancel"

# --- Conversation States ---
# Add Drama (via TMDB search)
TMDB_SEARCH = 0
TMDB_SELECT = 1
ADD_CONFIRM = 2
ADD_MANUAL_TITLE = 3

# Add Episode
EP_SELECT_DRAMA = 10
EP_NUMBER = 11
EP_LINK = 12

# Search
SEARCH_QUERY = 30
