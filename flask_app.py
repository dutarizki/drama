"""
Flask Webhook + Player + Proxy untuk Railway.
"""

import asyncio
import logging
import urllib.parse
import requests as req_lib
from flask import Flask, request, Response, render_template_string
from telegram import Update
from telegram.ext import Application
import urllib.request

from config import BOT_TOKEN, WEBHOOK_SECRET, PORT
from bot import setup_application
from database import init_db

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

ptb_app = Application.builder().token(BOT_TOKEN).build()
setup_application(ptb_app)

async def process_update(update_json):
    async with ptb_app:
        await init_db()
        await ptb_app.initialize()
        update = Update.de_json(update_json, ptb_app.bot)
        await ptb_app.process_update(update)

PLAYER_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>{{ title }} - Ep {{ ep }}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #000; color: #fff; font-family: 'Segoe UI', sans-serif; height: 100vh; overflow: hidden; }
  #header {
    background: linear-gradient(to bottom, rgba(0,0,0,0.9), transparent);
    padding: 12px 16px; display: flex; align-items: center; gap: 12px;
    position: absolute; top: 0; left: 0; right: 0; z-index: 10; transition: opacity 0.3s;
  }
  #header h1 { font-size: 15px; font-weight: 600; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  #header span { font-size: 13px; color: #e50914; font-weight: 700; background: rgba(229,9,20,0.15); padding: 3px 8px; border-radius: 4px; }
  #player-wrap { width: 100%; height: 100vh; }
  iframe#player { width: 100%; height: 100%; border: none; display: block; }
  #fs-btn {
    position: fixed; bottom: 20px; right: 16px; z-index: 100;
    background: rgba(229,9,20,0.9); color: #fff; border: none; border-radius: 50px;
    padding: 10px 18px; font-size: 14px; font-weight: 600; cursor: pointer;
    box-shadow: 0 4px 15px rgba(229,9,20,0.4);
  }
  #loading {
    position: fixed; inset: 0; background: #000;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    z-index: 50; gap: 16px; transition: opacity 0.5s;
  }
  .logo { font-size: 28px; font-weight: 800; color: #e50914; }
  .spinner { width: 36px; height: 36px; border: 3px solid rgba(255,255,255,0.1); border-top-color: #e50914; border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  #loading.hidden { opacity: 0; pointer-events: none; }
</style>
</head>
<body>
<div id="loading">
  <div class="logo">🎬</div>
  <div class="spinner"></div>
  <p style="font-size:13px;color:rgba(255,255,255,0.5)">Memuat video...</p>
</div>
<div id="header">
  <h1>{{ title }}</h1>
  <span>Ep {{ ep }}</span>
</div>
<div id="player-wrap">
  <iframe id="player" src="/proxy?url={{ src_encoded }}" allowfullscreen allow="fullscreen; autoplay" scrolling="no"></iframe>
</div>
<button id="fs-btn" onclick="goFullscreen()">⛶ Fullscreen</button>
<script>
  document.getElementById("player").onload = () => {
    setTimeout(() => document.getElementById("loading").classList.add("hidden"), 800);
  };
  function goFullscreen() {
    const el = document.getElementById("player-wrap");
    if (el.requestFullscreen) el.requestFullscreen();
    else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    else document.getElementById("player").requestFullscreen();
  }
</script>
</body>
</html>"""


@app.route("/", methods=["GET"])
def index():
    return "Bot is running! 🤖🎬"


@app.route("/player", methods=["GET"])
def player():
    src = request.args.get("src", "")
    title = request.args.get("title", "Drama")
    ep = request.args.get("ep", "1")
    src_encoded = urllib.parse.quote(src, safe="")
    return render_template_string(PLAYER_HTML, title=title, ep=ep, src_encoded=src_encoded)


@app.route("/proxy", methods=["GET"])
def proxy():
    url = request.args.get("url", "")
    if not url:
        return "URL tidak ditemukan", 400
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Referer": "https://playeriframe.sbs/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = req_lib.get(url, headers=headers, timeout=15)
        excluded = ['content-encoding', 'content-length', 'transfer-encoding',
                    'connection', 'x-frame-options', 'content-security-policy']
        response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
        return Response(resp.content, status=resp.status_code,
                        content_type=resp.headers.get('content-type', 'text/html'),
                        headers=response_headers)
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    if request.method == "POST":
        asyncio.run(process_update(request.get_json(force=True)))
        return "OK", 200
    return "Not allowed", 405


@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    host = request.host_url.rstrip('/')
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={host}/webhook/{WEBHOOK_SECRET}"
    try:
        req = urllib.request.urlopen(url)
        return "✅ Webhook Berhasil di-set! Respon Telegram:<br><br>" + req.read().decode('utf-8')
    except Exception as e:
        return f"❌ Gagal set webhook: {str(e)}"


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
