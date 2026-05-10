"""
Flask Webhook + Smart Proxy + Ad Blocker untuk Railway.
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

AD_BLOCKER_JS = """
<style>
[id*="ad"],[class*="ad"],[id*="pop"],[class*="pop"],
[id*="banner"],[class*="banner"],[id*="overlay"],[class*="overlay"],
[id*="interstitial"],[class*="interstitial"],[id*="sponsor"],[class*="sponsor"],
ins.adsbygoogle,.advertisement,.advertise {
  display:none!important;visibility:hidden!important;
  height:0!important;width:0!important;pointer-events:none!important;
}
body,html{margin:0;padding:0;background:#000;overflow:hidden;}
video,iframe{width:100%!important;height:100%!important;}
</style>
<script>
(function(){
  // Blokir popup/popunder
  window.open = function(){return {focus:function(){},blur:function(){}};};
  window.alert = function(){};
  window.confirm = function(){return false;};
  
  // Override setTimeout untuk blokir popup delay
  var _st = window.setTimeout;
  window.setTimeout = function(fn, d){
    if(typeof fn==='string') return;
    try{
      var s = fn.toString();
      if(s.includes('open(') || s.includes('popunder') || s.includes('popup')) return;
    }catch(e){}
    return _st(fn, d);
  };

  // Blokir script iklan yang di-inject
  var _ce = document.createElement.bind(document);
  document.createElement = function(tag){
    var el = _ce(tag);
    if(tag.toLowerCase()==='script'){
      Object.defineProperty(el,'src',{
        set:function(v){
          var blocked = """ + str(AD_DOMAINS).replace("'", '"') + """;
          for(var i=0;i<blocked.length;i++){
            if(v && v.includes(blocked[i])) return;
          }
          Object.getOwnPropertyDescriptor(HTMLScriptElement.prototype,'src').set.call(this,v);
        },
        get:function(){
          return Object.getOwnPropertyDescriptor(HTMLScriptElement.prototype,'src').get.call(this);
        }
      });
    }
    return el;
  };

  // Observer hapus iklan dinamis
  var obs = new MutationObserver(function(ms){
    ms.forEach(function(m){
      m.addedNodes.forEach(function(n){
        if(n.nodeType===1){
          var id=(n.id||'').toLowerCase();
          var cls=(n.className||'').toLowerCase();
          if(id.match(/ad|pop|banner|overlay|interstitial|sponsor/) ||
             cls.match(/ad|pop|banner|overlay|interstitial|sponsor/)){
            n.remove();
          }
        }
      });
    });
  });
  obs.observe(document.documentElement,{childList:true,subtree:true});
})();
</script>
"""

PLAYER_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>{{ title }} Ep{{ ep }}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000;overflow:hidden}
#wrap{width:100vw;height:100vh;position:relative}
iframe{width:100%;height:100%;border:none;display:block}
#info{position:fixed;top:0;left:0;right:0;padding:8px 12px;
  background:linear-gradient(rgba(0,0,0,.8),transparent);
  color:#fff;font-family:sans-serif;font-size:13px;font-weight:600;
  z-index:99;display:flex;justify-content:space-between;align-items:center;
  transition:opacity .3s}
#ep{background:#e50914;padding:2px 8px;border-radius:4px;font-size:12px}
#fsBtn{position:fixed;bottom:16px;right:16px;z-index:99;
  background:#e50914;color:#fff;border:none;border-radius:24px;
  padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;
  box-shadow:0 2px 12px rgba(229,9,20,.5)}
</style>
</head>
<body>
<div id="info">
  <span id="ttl">{{ title }}</span>
  <span id="ep">Ep {{ ep }}</span>
</div>
<div id="wrap">
  <iframe id="fr" 
    src="/smartproxy?url={{ src_encoded }}&base={{ base_encoded }}"
    allowfullscreen
    allow="autoplay; fullscreen; picture-in-picture"
    scrolling="no">
  </iframe>
</div>
<button id="fsBtn" onclick="fs()">⛶ Fullscreen</button>
<script>
function fs(){
  var el=document.getElementById('wrap');
  if(el.requestFullscreen) el.requestFullscreen();
  else if(el.webkitRequestFullscreen) el.webkitRequestFullscreen();
  else if(el.mozRequestFullScreen) el.mozRequestFullScreen();
  else{
    var fr=document.getElementById('fr');
    if(fr.requestFullscreen) fr.requestFullscreen();
    else if(fr.webkitRequestFullscreen) fr.webkitRequestFullscreen();
  }
}
// Auto hide info bar
var t;
document.addEventListener('touchstart',function(){
  document.getElementById('info').style.opacity='1';
  clearTimeout(t);
  t=setTimeout(function(){document.getElementById('info').style.opacity='0';},3000);
});
// Try auto fullscreen on first tap
var firstTap=true;
document.getElementById('wrap').addEventListener('click',function(){
  if(firstTap){firstTap=false;fs();}
});
</script>
</body>
</html>"""


def rewrite_urls(content, base_url, proxy_base):
    """Rewrite semua URL di HTML supaya lewat proxy."""
    parsed = urllib.parse.urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    
    def make_proxy_url(url):
        if not url or url.startswith('data:') or url.startswith('#') or url.startswith('javascript:'):
            return url
        if url.startswith('//'):
            url = parsed.scheme + ':' + url
        elif url.startswith('/'):
            url = origin + url
        elif not url.startswith('http'):
            url = origin + '/' + url
        # Cek apakah domain iklan
        for ad in AD_DOMAINS:
            if ad in url:
                return 'about:blank'
        return f"{proxy_base}?url={urllib.parse.quote(url, safe='')}&base={urllib.parse.quote(origin, safe='')}"
    
    # Rewrite src dan href
    def replace_src(m):
        attr = m.group(1)
        url = m.group(2)
        new_url = make_proxy_url(url)
        return f'{attr}="{new_url}"'
    
    content = re.sub(r'(src)=["\']([^"\']+)["\']', replace_src, content)
    content = re.sub(r'(href)=["\']([^"\'#javascript][^"\']*)["\']', replace_src, content)
    
    return content


def strip_ads_from_html(content):
    """Strip iklan dari HTML."""
    # Hapus script dari domain iklan
    for domain in AD_DOMAINS:
        de = domain.replace('.', r'\.')
        content = re.sub(rf'<script[^>]*src=["\'][^"\']*{de}[^"\']*["\'][^>]*>.*?</script>', 
                        '', content, flags=re.IGNORECASE|re.DOTALL)

    # Hapus meta redirect
    content = re.sub(r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*>', '', content, flags=re.IGNORECASE)
    
    # Inject ad blocker
    if '</head>' in content:
        content = content.replace('</head>', AD_BLOCKER_JS + '</head>', 1)
    else:
        content = AD_BLOCKER_JS + content
    
    return content


@app.route("/", methods=["GET"])
def index():
    return "Bot is running! 🤖🎬"


@app.route("/watch", methods=["GET"])
def watch():
    src = request.args.get("src", "")
    title = request.args.get("title", "Drama")
    ep = request.args.get("ep", "1")
    parsed = urllib.parse.urlparse(src)
    base = f"{parsed.scheme}://{parsed.netloc}"
    src_encoded = urllib.parse.quote(src, safe="")
    base_encoded = urllib.parse.quote(base, safe="")
    return render_template_string(PLAYER_HTML, title=title, ep=ep, 
                                   src_encoded=src_encoded, base_encoded=base_encoded)


@app.route("/smartproxy", methods=["GET"])
def smart_proxy():
    url = request.args.get("url", "")
    base = request.args.get("base", "")
    if not url:
        return "URL tidak ditemukan", 400
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
            "Referer": base or "https://playeriframe.sbs/",
            "Origin": base or "https://playeriframe.sbs",
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        }
        resp = req_lib.get(url, headers=headers, timeout=20, allow_redirects=True)
        excluded = ['content-encoding','content-length','transfer-encoding',
                    'connection','x-frame-options','content-security-policy',
                    'x-content-type-options','strict-transport-security']
        resp_headers = {k:v for k,v in resp.headers.items() if k.lower() not in excluded}
        
        content_type = resp.headers.get('content-type','')
        
        if 'text/html' in content_type:
            content = resp.text
            proxy_base = request.host_url.rstrip('/') + '/smartproxy'
            content = strip_ads_from_html(content)
            content = rewrite_urls(content, url, proxy_base)
            return Response(content, status=resp.status_code,
                           content_type=content_type, headers=resp_headers)
        elif 'javascript' in content_type or 'text/css' in content_type:
            content = resp.text
            # Blokir domain iklan di JS
            for domain in AD_DOMAINS:
                content = re.sub(rf'https?://[^\s"\']*{re.escape(domain)}[^\s"\']*', 
                                'about:blank', content)
            return Response(content, status=resp.status_code,
                           content_type=content_type, headers=resp_headers)
        else:
            return Response(resp.content, status=resp.status_code,
                           content_type=content_type, headers=resp_headers)
    except Exception as e:
        logger.error(f"Proxy error: {e}")
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
