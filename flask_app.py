"""
Flask Webhook wrapper untuk deploy di PythonAnywhere.
"""

import asyncio
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application
import urllib.request

from config import BOT_TOKEN, WEBHOOK_SECRET
from bot import setup_application
from database import init_db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize PTB Application
ptb_app = Application.builder().token(BOT_TOKEN).build()
setup_application(ptb_app)

async def process_update(update_json):
    """Bridge for running PTB async in a synchronous Flask context"""
    async with ptb_app:
        # PENTING: Inisialisasi database sebelum memproses pesan
        await init_db()
        await ptb_app.initialize()
        
        update = Update.de_json(update_json, ptb_app.bot)
        await ptb_app.process_update(update)

@app.route("/", methods=["GET"])
def index():
    return "Bot is running on PythonAnywhere! 🤖🎬"

@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    if request.method == "POST":
        # Run the async bot logic menggunakan asyncio.run (cara standar PythonAnywhere)
        asyncio.run(process_update(request.get_json(force=True)))
        return "OK", 200
    return "Not allowed", 405

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    """Jalankan endpoint ini 1x via browser untuk mendaftarkan Webhook ke Telegram"""
    host = request.host_url.rstrip('/')
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={host}/webhook/{WEBHOOK_SECRET}"
    try:
        req = urllib.request.urlopen(url)
        return "✅ Webhook Berhasil di-set! Respon Telegram:<br><br>" + req.read().decode('utf-8')
    except Exception as e:
        return f"❌ Gagal set webhook: {str(e)}"
