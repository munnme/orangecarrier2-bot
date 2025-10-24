import os
import time
import json
import re
import requests
import sqlite3
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Bot, InputFile

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
OC_SESSION_COOKIE = os.getenv("OC_SESSION_COOKIE")  # cookie string from browser
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "15"))

BASE_URL = "https://www.orangecarrier.com"
LIVE_CALLS_PATH = "/live/calls"

if not BOT_TOKEN or not TARGET_CHAT_ID:
    raise RuntimeError("Set BOT_TOKEN and TARGET_CHAT_ID first")

bot = Bot(token=BOT_TOKEN)

# ================= FOLDERS =================
DATA_DIR = Path("/tmp/orangecarrier_data")
VOICES_DIR = DATA_DIR / "voices"
DATA_DIR.mkdir(parents=True, exist_ok=True)
VOICES_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "seen.sqlite"
conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, first_seen TEXT)")
conn.commit()

# ================= UTILITIES =================
def is_seen(item_id):
    cur.execute("SELECT 1 FROM seen WHERE id=?", (item_id,))
    return cur.fetchone() is not None

def mark_seen(item_id):
    try:
        cur.execute("INSERT INTO seen (id, first_seen) VALUES (?, ?)",
                    (item_id, datetime.utcnow().isoformat()))
        conn.commit()
    except:
        pass

def send_message(text):
    """Send message to Telegram"""
    try:
        bot.send_message(chat_id=TARGET_CHAT_ID, text=text)
        print("TG:", text)
    except Exception as e:
        print("TG send error:", e)

def get_session():
    """Create authenticated session"""
    s = requests.Session()
    if OC_SESSION_COOKIE:
        s.headers.update({
            "Cookie": OC_SESSION_COOKIE,
            "User-Agent": "Mozilla/5.0 (compatible; OrangeCarrierBot)"
        })
    return s

AUDIO_RX = re.compile(r"https?://[^\s'\"<>]+(?:\.mp3|\.ogg|\.m4a)", re.I)

def check_cookie(session):
    """Test cookie validity"""
    try:
        r = session.get(BASE_URL, timeout=10)
        if r.status_code == 200:
            send_message("✅ Orange account login successfully!")
            return True
        else:
            send_message(f"⚠️ Orange carrier not login (Status {r.status_code})")
            return False
    except Exception as e:
        send_message(f"❌ Cookie check failed: {e}")
        return False

def fetch_live_items(session):
    """Fetch current live call data"""
    url = BASE_URL + LIVE_CALLS_PATH
    try:
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            print("Fetch failed:", r.status_code)
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        blocks = soup.find_all(["div", "li", "p"])
        items = []
        for b in blocks:
            txt = b.get_text(" ", strip=True)
            if len(txt) < 8:
                continue
            audio = None
            for m in AUDIO_RX.findall(str(b)):
                audio = m
                break
            key = (audio or "") + "|" + txt[:120]
            items.append({"id": key, "text": txt, "audio": audio})
        return items
    except Exception as e:
        print("Fetch error:", e)
        return []

def download_file(session, url, dest):
    """Download audio file"""
    try:
        r = session.get(url, stream=True, timeout=40)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print("Download error:", e)
        return False

def send_to_telegram(item, audio_path=None):
    """Send call info or audio to Telegram"""
    text = f"📞 New Call\n\n{item.get('text','')}"
    try:
        if audio_path:
            with open(audio_path, "rb") as f:
                bot.send_audio(chat_id=TARGET_CHAT_ID, audio=InputFile(f), caption=text)
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text=text)
    except Exception as e:
        print("Send error:", e)

# ================= MAIN LOOP =================
def main_loop():
    send_message("🚀 Bot started successfully!")
    session = get_session()
    check_cookie(session)

    while True:
        try:
            items = fetch_live_items(session)
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
                    fname = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
                    dest = VOICES_DIR / fname
                    if download_file(session, audio_url, dest):
                        audio_path = str(dest)
                send_to_telegram(it, audio_path)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Loop error:", e)
            time.sleep(POLL_INTERVAL)

# ================= ENTRYPOINT =================
if __name__ == "__main__":
    main_loop()            items.append({"id": key, "text": txt, "audio": audio})
        return items
    except Exception as e:
        print("Fetch error:", e)
        return []

def download_file(session, url, dest):
    try:
        r = session.get(url, stream=True, timeout=40)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print("Download error:", e)
        return False

def send_to_telegram(item, audio_path=None):
    text = f"📞 New Call\n\n{item.get('text','')}"
    try:
        if audio_path:
            with open(audio_path, "rb") as f:
                bot.send_audio(chat_id=TARGET_CHAT_ID, audio=InputFile(f), caption=text)
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text=text)
    except Exception as e:
        print("Send error:", e)

# ================= MAIN LOOP =================
def main_loop():
    send_message("🚀 Bot started successfully!")
    session = get_session()
    check_cookie(session)

    while True:
        try:
            items = fetch_live_items(session)
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
                    fname = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
                    dest = VOICES_DIR / fname
                    if download_file(session, audio_url, dest):
                        audio_path = str(dest)
                send_to_telegram(it, audio_path)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Loop error:", e)
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main_loop()        r = session.get(url, stream=True, timeout=40)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print("Download error:", e)
        return False

def send_to_telegram(item, audio_path=None):
    text = f"📞 New Call\n\n{item.get('text','')}"
    try:
        if audio_path:
            with open(audio_path, "rb") as f:
                bot.send_audio(chat_id=TARGET_CHAT_ID, audio=InputFile(f), caption=text)
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text=text)
    except Exception as e:
        print("Send error:", e)

# ================= MAIN LOOP =================
def main_loop():
    send_message("🚀 Bot started successfully!")
    session = get_session()
    cookie_ok = check_cookie(session)

    while True:
        try:
            items = fetch_live_items(session)
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
                    fname = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
                    dest = VOICES_DIR / fname
                    if download_file(session, audio_url, dest):
                        audio_path = str(dest)
                send_to_telegram(it, audio_path)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Loop error:", e)
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main_loop()
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
