"""
Flask Webhook + Player + Proxy + Ad Blocker untuk Railway.
"""

import asyncio
import logging
import urllib.parse
import re
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


# Domain iklan yang diblokir
AD_DOMAINS = [
    'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
    'adservice.google.com', 'amazon-adsystem.com', 'ads.yahoo.com',
    'adsrvr.org', 'adnxs.com', 'rubiconproject.com', 'openx.net',
    'pubmatic.com', 'taboola.com', 'outbrain.com', 'revcontent.com',
    'mgid.com', 'adform.net', 'criteo.com', 'serving-sys.com',
    'moatads.com', 'scorecardresearch.com', 'quantserve.com',
    'popads.net', 'popcash.net', 'propellerads.com', 'adcash.com',
    'exoclick.com', 'juicyads.com', 'trafficjunky.com', 'ero-advertising.com',
    'plugrush.com', 'hilltopads.net', 'adsterra.com', 'richpush.co',
    'clickadu.com', 'admaven.com', 'zeropark.com', 'traffic-media.co',
    'adxpansion.com', 'adspyglass.com', 'adskeeper.co.uk',
]

# Pattern script iklan
AD_SCRIPT_PATTERNS = [
    r'<script[^>]*src=["\'][^"\']*(?:' + '|'.join([
        'pop', 'push', 'ads?[.-]', 'advert', 'banner', 'sponsor',
        'adsense', 'adserver', 'adnetwork', 'admanager', 'dfp',
        'pagead', 'adsbygoogle', 'prebid', 'gpt\.js', 'pubads',
        'interstitial', 'overlay', 'popup', 'popunder',
    ]) + r'])[^"\']*["\'][^>]*>.*?</script>',
    r'<ins\s+class=["\']adsbygoogle["\'][^>]*>.*?</ins>',
    r'<!--\s*(?:Ad|Advertisement|Sponsored)\s*-->.*?<!--\s*End\s*(?:Ad|Advertisement)\s*-->',
    r'<div[^>]*(?:id|class)=["\'][^"\']*(?:ad[-_]|[-_]ad|advert|banner|sponsor|popup|overlay|interstitial)[^"\']*["\'][^>]*>.*?</div>',
]

# JS yang diblokir (inline)
AD_JS_PATTERNS = [
    r'(?:window\.open|open)\s*\([^)]*(?:http|//)[^)]*\)',
    r'popunder\s*\(',
    r'popup\s*\(',
    r'document\.createElement\s*\(\s*["\']script["\']\s*\)[^;]*(?:' + '|'.join(AD_DOMAINS[:10]) + r')',
]


def strip_ads(html_content):
    """Strip iklan dari konten HTML."""
    content = html_content

    # 1. Blokir script dari domain iklan
    for domain in AD_DOMAINS:
        domain_escaped = domain.replace('.', r'\.')
        pattern = rf'<script[^>]*src=["\'][^"\']*{domain_escaped}[^"\']*["\'][^>]*>.*?</script>'
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        # Juga blokir link/img dari domain iklan
        pattern2 = rf'<(?:link|img|iframe)[^>]*(?:href|src)=["\'][^"\']*{domain_escaped}[^"\']*["\'][^>]*/?>'
        content = re.sub(pattern2, '', content, flags=re.IGNORECASE)

    # 2. Hapus script iklan berdasarkan pattern
    for pattern in AD_SCRIPT_PATTERNS:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

    # 3. Inject CSS untuk sembunyikan elemen iklan + blokir popup
    ad_css = """
<style>
/* Ad Blocker */
[id*="ad-"],[id*="-ad"],[id*="ads-"],[id*="-ads"],
[class*="ad-"],[class*="-ad"],[class*="ads-"],[class*="-ads"],
[id*="banner"],[class*="banner"],
[id*="popup"],[class*="popup"],
[id*="overlay"],[class*="overlay"],
[id*="interstitial"],[class*="interstitial"],
[id*="sponsor"],[class*="sponsor"],
ins.adsbygoogle, .ad-container, .ad-wrapper,
.advertisement, .advertise, #ad, .ad {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
  height: 0 !important;
  width: 0 !important;
  overflow: hidden !important;
}
/* Pastikan video tetap fullscreen */
video { width: 100% !important; height: 100% !important; }
</style>
<script>
/* Blokir window.open (popup/popunder) */
window.open = function() { return null; };
window.alert = function() {};
/* Blokir setTimeout yang biasanya dipakai popup */
const _origTimeout = window.setTimeout;
window.setTimeout = function(fn, delay) {
  if (typeof fn === 'string' && (fn.includes('open') || fn.includes('pop'))) return;
  return _origTimeout(fn, delay);
};
/* Observer untuk hapus elemen iklan yang muncul dinamis */
const adObserver = new MutationObserver(function(mutations) {
  mutations.forEach(function(m) {
    m.addedNodes.forEach(function(node) {
      if (node.nodeType === 1) {
        const id = (node.id || '').toLowerCase();
        const cls = (node.className || '').toLowerCase();
        if (id.includes('ad') || cls.includes('ad') || 
            id.includes('popup') || cls.includes('popup') ||
            id.includes('overlay') || cls.includes('overlay') ||
            id.includes('banner') || cls.includes('banner')) {
          node.style.display = 'none';
          node.style.visibility = 'hidden';
        }
      }
    });
  });
});
adObserver.observe(document.documentElement, { childList: true, subtree: true });
</script>
"""
    # Inject sebelum </head> atau di awal body
    if '</head>' in content:
        content = content.replace('</head>', ad_css + '</head>', 1)
    elif '<body' in content:
        content = re.sub(r'(<body[^>]*>)', r'\1' + ad_css, content, count=1, flags=re.IGNORECASE)
    else:
        content = ad_css + content

    return content


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

        content_type = resp.headers.get('content-type', '')
        if 'text/html' in content_type:
            content = strip_ads(resp.text)
            return Response(content, status=resp.status_code,
                           content_type=content_type,
                           headers=response_headers)
        else:
            return Response(resp.content, status=resp.status_code,
                           content_type=content_type,
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
