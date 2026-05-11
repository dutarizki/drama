"""
Flask Webhook + HLS Player untuk Railway.
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
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>{{ title }} - Ep {{ ep }}</title>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;overflow:hidden}
#wrap{width:100vw;height:100vh;position:relative;display:flex;align-items:center;justify-content:center}
video{width:100%;height:100%;object-fit:contain;background:#000}
#info{position:fixed;top:0;left:0;right:0;padding:10px 14px;
  background:linear-gradient(rgba(0,0,0,.85),transparent);
  color:#fff;font-family:sans-serif;font-size:14px;font-weight:600;
  z-index:99;display:flex;justify-content:space-between;align-items:center;
  transition:opacity .4s}
#ep-badge{background:#e50914;padding:3px 10px;border-radius:4px;font-size:12px}
#controls{position:fixed;bottom:0;left:0;right:0;padding:12px 14px;
  background:linear-gradient(transparent,rgba(0,0,0,.85));
  z-index:99;display:flex;align-items:center;gap:10px;
  transition:opacity .4s}
#fsBtn{margin-left:auto;background:#e50914;color:#fff;border:none;
  border-radius:20px;padding:7px 16px;font-size:13px;font-weight:700;cursor:pointer}
#loading{position:fixed;inset:0;background:#000;display:flex;flex-direction:column;
  align-items:center;justify-content:center;z-index:50;gap:12px}
.spinner{width:40px;height:40px;border:3px solid rgba(255,255,255,.1);
  border-top-color:#e50914;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#loading.hidden{display:none}
#err{position:fixed;inset:0;background:#000;display:none;flex-direction:column;
  align-items:center;justify-content:center;color:#fff;font-family:sans-serif;gap:12px}
#err.show{display:flex}
</style>
</head>
<body>
<div id="loading">
  <div class="spinner"></div>
  <p style="color:rgba(255,255,255,.6);font-family:sans-serif;font-size:13px">Memuat video...</p>
</div>
<div id="err">
  <span style="font-size:32px">😞</span>
  <p style="font-size:15px">Video tidak dapat dimuat</p>
  <p style="font-size:12px;color:rgba(255,255,255,.5)" id="errMsg"></p>
</div>
<div id="info">
  <span>{{ title }}</span>
  <span id="ep-badge">Ep {{ ep }}</span>
</div>
<div id="wrap">
  <video id="vid" playsinline webkit-playsinline controls></video>
</div>
<div id="controls">
  <button id="fsBtn" onclick="fs()">⛶ Fullscreen</button>
</div>
<script>
var src = "{{ src }}";
var vid = document.getElementById('vid');
var loading = document.getElementById('loading');
var errDiv = document.getElementById('err');

function showErr(msg){
  loading.classList.add('hidden');
  errDiv.classList.add('show');
  document.getElementById('errMsg').textContent = msg || '';
}

function initPlayer(){
  if(Hls.isSupported()){
    var hls = new Hls({
      enableWorker: true,
      lowLatencyMode: false,
    });
    hls.loadSource(src);
    hls.attachMedia(vid);
    hls.on(Hls.Events.MANIFEST_PARSED, function(){
      loading.classList.add('hidden');
      vid.play().catch(function(){});
    });
    hls.on(Hls.Events.ERROR, function(e, data){
      if(data.fatal) showErr(data.type + ': ' + data.details);
    });
  } else if(vid.canPlayType('application/vnd.apple.mpegurl')){
    vid.src = src;
    vid.addEventListener('loadedmetadata', function(){
      loading.classList.add('hidden');
      vid.play().catch(function(){});
    });
    vid.addEventListener('error', function(){
      showErr('Format tidak didukung browser ini');
    });
  } else {
    showErr('Browser tidak support HLS');
  }
}

initPlayer();

function fs(){
  var el = document.getElementById('wrap');
  if(el.requestFullscreen) el.requestFullscreen();
  else if(el.webkitRequestFullscreen) el.webkitRequestFullscreen();
  else if(vid.webkitEnterFullscreen) vid.webkitEnterFullscreen();
}

// Auto hide controls
var hideTimer;
function showControls(){
  document.getElementById('info').style.opacity='1';
  document.getElementById('controls').style.opacity='1';
  clearTimeout(hideTimer);
  hideTimer = setTimeout(function(){
    document.getElementById('info').style.opacity='0';
    document.getElementById('controls').style.opacity='0';
  }, 3000);
}
document.addEventListener('touchstart', showControls);
document.addEventListener('mousemove', showControls);
</script>
</body>
</html>"""


@app.route("/", methods=["GET"])
def index():
    return "Bot is running! 🤖🎬"


@app.route("/watch", methods=["GET"])
def watch():
    src = request.args.get("src", "")
    title = request.args.get("title", "Drama")
    ep = request.args.get("ep", "1")
    return render_template_string(PLAYER_HTML, title=title, ep=ep, src=src)


@app.route("/proxy", methods=["GET"])
def proxy():
    """Proxy untuk file m3u8 dan ts supaya bypass hotlink."""
    url = request.args.get("url", "")
    if not url:
        return "URL tidak ditemukan", 400
    try:
        referer = request.args.get("ref", "https://playeriframe.sbs/")
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
            "Referer": referer,
            "Origin": urllib.parse.urlparse(referer).scheme + "://" + urllib.parse.urlparse(referer).netloc,
        }
        resp = req_lib.get(url, headers=headers, timeout=20, stream=True)
        excluded = ['content-encoding','transfer-encoding','connection',
                    'x-frame-options','content-security-policy']
        resp_headers = {k:v for k,v in resp.headers.items() if k.lower() not in excluded}
        resp_headers['Access-Control-Allow-Origin'] = '*'
        
        return Response(resp.iter_content(chunk_size=8192),
                       status=resp.status_code,
                       content_type=resp.headers.get('content-type','application/octet-stream'),
                       headers=resp_headers)
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
