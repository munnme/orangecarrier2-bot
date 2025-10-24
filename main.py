"""
Orangecarrier → Telegram Bridge (Full Version with Startup Message + Cookie Check)
Deployable on Railway
"""

import os, time, json, re, requests, sqlite3
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Bot, InputFile

# ---- ENVIRONMENT VARIABLES ----
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Telegram bot token
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")  # Chat or group ID
OC_SESSION_COOKIE = os.getenv("OC_SESSION_COOKIE")  # Orangecarrier cookie
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "20"))

BASE_URL = "https://www.orangecarrier.com"
LIVE_CALLS_PATH = "/live/calls"

# ---- BASIC CHECK ----
if not BOT_TOKEN or not TARGET_CHAT_ID:
    raise RuntimeError("Set BOT_TOKEN and TARGET_CHAT_ID in Railway Environment Variables!")

bot = Bot(token=BOT_TOKEN)

# ---- DATA FOLDERS ----
DATA_DIR = Path("/tmp/orangecarrier_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
VOICES_DIR = DATA_DIR / "voices"
VOICES_DIR.mkdir(parents=True, exist_ok=True)

# ---- DATABASE ----
DB_PATH = DATA_DIR / "seen.sqlite"
conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, first_seen TEXT)")
conn.commit()

def is_seen(item_id):
    cur.execute("SELECT 1 FROM seen WHERE id=?", (item_id,))
    return cur.fetchone() is not None

def mark_seen(item_id):
    try:
        cur.execute("INSERT INTO seen (id, first_seen) VALUES (?, ?)", (item_id, datetime.utcnow().isoformat()))
        conn.commit()
        return True
    except:
        return False

# ---- SESSION SETUP ----
def get_session():
    s = requests.Session()
    if OC_SESSION_COOKIE:
        s.headers.update({"Cookie": OC_SESSION_COOKIE, "User-Agent": "Mozilla/5.0"})
    return s

def check_login(session):
    try:
        r = session.get(BASE_URL + "/dashboard", timeout=15)
        if "Logout" in r.text or "Dashboard" in r.text:
            return True
        else:
            return False
    except Exception as e:
        print("Login check failed:", e)
        return False

# ---- FETCH LIVE CALL DATA ----
AUDIO_RX = re.compile(r"https?://[^\s'\"<>]+(?:\.mp3|\.ogg|\.m4a)", re.IGNORECASE)

def fetch_live_items(session):
    url = BASE_URL + LIVE_CALLS_PATH
    try:
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("Live page status", r.status_code)
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        blocks = soup.find_all(["div","li","p"])
        parsed = []
        seen_texts = set()
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
        print("HTML parse error:", e)
        return []

def download_file(session, url, dest: Path):
    try:
        r = session.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print("Download failed:", e)
        return False

# ---- TELEGRAM SEND ----
def send_to_telegram(item, audio_path=None):
    header = f"🔔 New Call Item\nID: {item.get('id')}\n"
    text = item.get("text") or ""
    body = header + (text[:800] + ("..." if len(text) > 800 else ""))
    try:
        if audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as f:
                bot.send_audio(chat_id=TARGET_CHAT_ID, audio=InputFile(f), caption=body)
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text=body)
    except Exception as e:
        print("Telegram send failed:", e)

# ---- MAIN LOOP ----
def main_loop():
    # 🔹 Step 1: Notify bot startup
    try:
        bot.send_message(chat_id=TARGET_CHAT_ID, text="🤖 Bot started successfully on Railway!")
    except Exception as e:
        print("Startup message failed:", e)

    # 🔹 Step 2: Session setup
    session = get_session()

    # 🔹 Step 3: Cookie validation
    if not OC_SESSION_COOKIE:
        bot.send_message(chat_id=TARGET_CHAT_ID, text="⚠️ Orange Carrier cookie missing — please set OC_SESSION_COOKIE!")
        print("Cookie missing.")
        return

    if check_login(session):
        bot.send_message(chat_id=TARGET_CHAT_ID, text="✅ Orange Carrier account login successfully!")
    else:
        bot.send_message(chat_id=TARGET_CHAT_ID, text="❌ Orange Carrier not login or cookie invalid.")
        print("Login check failed.")
        return

    print("Session ready. Poll interval:", POLL_INTERVAL)

    # 🔹 Step 4: Fetch and send data
    while True:
        try:
            items = fetch_live_items(session)
            if not items:
                time.sleep(POLL_INTERVAL)
                continue
            for it in items:
                item_id = it["id"]
                if is_seen(item_id):
                    continue
                mark_seen(item_id)
                audio_url = it.get("audio")
                audio_path = None
                if audio_url:
                    if audio_url.startswith("/"):
                        audio_url = BASE_URL + audio_url
                    fname = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{abs(hash(audio_url))%100000}.mp3"
                    dest = VOICES_DIR / fname
                    if download_file(session, audio_url, dest):
                        audio_path = str(dest)
                send_to_telegram(it, audio_path)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Main loop exception:", e)
            time.sleep(POLL_INTERVAL)

# ---- ENTRY POINT ----
if __name__ == "__main__":
    print("Starting Orangecarrier → Telegram bridge")
    main_loop()            for m in AUDIO_RX.findall(str(b)):
                aud = m
                break
            key = (aud or "") + "|" + txt[:120]
            if key in seen_texts:
                continue
            seen_texts.add(key)
            parsed.append({"id": key, "text": txt, "audio": aud})
        return parsed
    except Exception as e:
        print("Fetch error:", e)
        return []

def download_file(session, url, dest: Path):
    try:
        r = session.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print("Download failed:", e)
        return False

bot = Bot(token=BOT_TOKEN)

def send_to_telegram(item, audio_path=None):
    header = f"🔔 New call item\nid: {item.get('id')}\n"
    text = item.get("text") or ""
    body = header + (text[:800] + ("..." if len(text) > 800 else ""))
    try:
        if audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as f:
                bot.send_audio(chat_id=TARGET_CHAT_ID, audio=InputFile(f), caption=body)
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text=body)
    except Exception as e:
        print("Telegram send failed:", e)

def main_loop():
    session = get_session()
    print("✅ Session ready. Poll interval:", POLL_INTERVAL, "sec")
    while True:
        try:
            items = fetch_live_items(session)
            for it in items:
                item_id = str(it.get("id"))
                if is_seen(item_id):
                    continue
                mark_seen(item_id)
                audio_url = it.get("audio")
                audio_path = None
                if audio_url:
                    if audio_url.startswith("/"):
                        audio_url = BASE_URL + audio_url
                    fname = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{abs(hash(audio_url))%100000}.mp3"
                    dest = VOICES_DIR / fname
                    if download_file(session, audio_url, dest):
                        audio_path = str(dest)
                send_to_telegram(it, audio_path)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("Stopped manually.")
            break
        except Exception as e:
            print("Main loop error:", e)
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    print("🚀 Starting Orangecarrier -> Telegram bridge")
    main_loop()
