# 🎬 Telegram Drama Bot

Bot Telegram untuk katalog drama — otomatis ambil poster & rating dari TMDB. Deploy gratis 24/7 di Render.com.

## ✨ Fitur

### 👤 User
- 📋 Browse daftar drama (dengan poster & rating ⭐)
- 🔍 Search drama by judul
- 🎭 Filter by genre
- 📺 Pilih episode → langsung dapat link streaming ▶️

### 👑 Admin
- ➕ Tambah drama — **otomatis ambil poster, rating, genre, deskripsi dari TMDB**
- 📤 Upload episode — tinggal paste link URL per episode
- 📤 Batch upload — support range (contoh: `1-16`)
- 🗑️ Hapus drama/episode
- 📊 Statistik bot

## 🚀 Setup Cepat

### 1. Dapatkan 3 Token (GRATIS)

| Token | Dari mana | Link |
|-------|-----------|------|
| Bot Token | @BotFather di Telegram | Kirim `/newbot` |
| Admin ID | @userinfobot di Telegram | Kirim `/start` |
| TMDB API Key | themoviedb.org | [Daftar gratis](https://www.themoviedb.org/signup) → Settings → API |

### 2. Test Lokal

```bash
cd telegram-drama-bot

# Install dependencies
pip install -r requirements.txt

# Edit .env
# Isi BOT_TOKEN, ADMIN_ID, TMDB_API_KEY
notepad .env

# Jalankan
python bot.py
```

### 3. Deploy ke Render.com (GRATIS 24/7)

1. **Push ke GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/username/drama-bot.git
   git push -u origin main
   ```

2. **Buat akun di [render.com](https://render.com)** (gratis)

3. **New → Web Service → Connect GitHub repo**

4. **Settings:**
   - Runtime: **Docker**
   - Plan: **Free**

5. **Environment Variables** (di Render dashboard):
   | Key | Value |
   |-----|-------|
   | `BOT_TOKEN` | Token dari BotFather |
   | `ADMIN_ID` | User ID kamu |
   | `TMDB_API_KEY` | API key dari TMDB |
   | `MODE` | `webhook` |

6. **Deploy!** Bot akan online 24/7 🎉

> ⚠️ Free tier Render akan sleep setelah 15 menit tidak ada aktivitas. Bot akan bangun otomatis saat ada pesan masuk (delay ~30 detik pertama kali).

## 📱 Cara Pakai

### User
```
/start → Pilih "Daftar Drama" → Klik drama → Lihat poster & rating
→ Klik "Lihat Episode" → Pilih episode → Langsung dapat link streaming
```

### Admin
```
/admin → "Tambah Drama" → Ketik judul (contoh: "Lovely Runner")
→ Bot otomatis cari di TMDB → Pilih → Tersimpan dengan poster & rating!

/admin → "Upload Episode" → Pilih drama → Nomor episode (atau 1-16)
→ Paste link URL → Done!
```

## 📁 Struktur

```
telegram-drama-bot/
├── .env              # Config (TOKEN, API keys)
├── bot.py            # Entry point
├── config.py         # Constants
├── database.py       # SQLite database
├── tmdb.py           # TMDB API (auto poster & rating)
├── Dockerfile        # Untuk deploy Render
├── render.yaml       # Render config
├── handlers/
│   ├── start.py      # /start & menu
│   ├── user.py       # Browse, search, watch
│   └── admin.py      # CRUD drama & episode
└── utils/
    ├── keyboard.py   # Inline keyboards
    └── helpers.py    # Text formatting
```
