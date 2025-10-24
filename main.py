# main.py
"""
Orangecarrier -> Telegram bridge with cookie login check
Deployable on Railway / Replit / GitHub Actions
"""
import sys, types
sys.modules['imghdr'] = types.ModuleType('imghdr')
import os, time, json, re, requests, sqlite3
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import InputFile, Bot

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
OC_SESSION_COOKIE = os.getenv("OC_SESSION_COOKIE")  # e.g. "laravel_session=abcd123; XSRF-TOKEN=xyz"
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "15"))

BASE_URL = "https://www.orangecarrier.com"
LIVE_CALLS_PATH = "/live/calls"

if not BOT_TOKEN or not TARGET_CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN and TARGET_CHAT_ID must be set.")

# ================ PATHS ==================
DATA_DIR = Path("/tmp/orangecarrier_data")
VOICES_DIR = DATA_DIR / "voices"
DATA_DIR.mkdir(parents=True, exist_ok=True)
VOICES_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "seen.sqlite"
conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, first_seen TEXT)")
conn.commit()

# ================ HELPERS =================
def is_seen(item_id):
    cur.execute("SELECT 1 FROM seen WHERE id=?", (item_id,))
    return cur.fetchone() is not None

def mark_seen(item_id):
    try:
        cur.execute("INSERT INTO seen (id, first_seen) VALUES (?, ?)", (item_id, datetime.now(datetime.UTC).isoformat()))
        conn.commit()
    except Exception:
        pass

def get_session():
    s = requests.Session()
    if OC_SESSION_COOKIE:
        s.headers.update({
            "Cookie": OC_SESSION_COOKIE,
            "User-Agent": "Mozilla/5.0"
        })
    return s

def check_login(session):
    try:
        r = session.get(BASE_URL + "/dashboard", timeout=15)
        if "Logout" in r.text or "logout" in r.text or "Dashboard" in r.text:
            return True
        return False
    except Exception:
        return False

AUDIO_RX = re.compile(r"https?://[^\s'\"<>]+(?:\.mp3|\.ogg|\.m4a)", re.IGNORECASE)

def fetch_live_items(session):
    url = BASE_URL + LIVE_CALLS_PATH
    try:
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("Live calls HTTP", r.status_code)
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        blocks = soup.find_all(["div","li","p"])
        parsed, seen_texts = [], set()
        for b in blocks:
            txt = b.get_text(" ", strip=True)
            if len(txt) < 10:
                continue
            aud = None
            for m in AUDIO_RX.findall(str(b)):
                aud = m
                break
            key = (aud or "") + "|" + txt[:120]
            if key in seen_texts:
                continue
            seen_texts.add(key)
            parsed.append({"id": key, "text": txt, "audio": aud})
        return parsed
    except Exception as e:
        print("fetch_live_items error:", e)
        return []

def download_file(session, url, dest):
    try:
        r = session.get(url, stream=True, timeout=40)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print("Download failed:", e)
        return False

# ================ TELEGRAM =================
bot = Bot(token=BOT_TOKEN)

def send_to_telegram(item, audio_path=None):
    body = f"🔔 New call item\n{item.get('text','')[:800]}"
    try:
        if audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as f:
                bot.send_audio(chat_id=TARGET_CHAT_ID, audio=InputFile(f), caption=body)
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text=body)
    except Exception as e:
        print("Telegram send failed:", e)

# ================ MAIN LOOP =================
def main_loop():
    session = get_session()
    bot.send_message(chat_id=TARGET_CHAT_ID, text="🚀 Bot started... Checking OrangeCarrier login...")

    if not OC_SESSION_COOKIE:
        bot.send_message(chat_id=TARGET_CHAT_ID, text="⚠️ No cookie found! Please set OC_SESSION_COOKIE in Secrets.")
    else:
        if check_login(session):
            bot.send_message(chat_id=TARGET_CHAT_ID, text="✅ OrangeCarrier login successful.")
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text="❌ OrangeCarrier not logged in or cookie expired.")

    print("Polling every", POLL_INTERVAL, "seconds...")
    while True:
        try:
            items = fetch_live_items(session)
            if not items:
                time.sleep(POLL_INTERVAL)
                continue
            for it in items:
                iid = it.get("id")
                if is_seen(iid):
                    continue
                mark_seen(iid)
                audio_path = None
                if it.get("audio"):
                    aurl = it["audio"]
                    if aurl.startswith("/"):
                        aurl = BASE_URL + aurl
                    fname = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.mp3"
                    dest = VOICES_DIR / fname
                    if download_file(session, aurl, dest):
                        audio_path = str(dest)
                send_to_telegram(it, audio_path)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Loop error:", e)
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    print("Starting bridge...")
    main_loop()
