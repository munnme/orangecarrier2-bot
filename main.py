"""
OrangeCarrier -> Telegram Bridge (Improved Socket.IO Client)
✅ Auto reconnect
✅ Auth event system added
✅ Clean debug + Telegram notifications
✅ /ping command added
"""

import os, json, time, sqlite3, threading, urllib.parse
from datetime import datetime
from pathlib import Path
from telegram import Bot, InputFile, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from flask import Flask
import socketio

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
ORANGE_TOKEN = os.getenv("ORANGE_TOKEN")

if not BOT_TOKEN or not TARGET_CHAT_ID or not ORANGE_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN, TARGET_CHAT_ID, ORANGE_TOKEN must be set in Railway environment variables!")

# ✅ Encode token safely
encoded_token = urllib.parse.quote(ORANGE_TOKEN, safe='')
SERVER_URL = f"https://hub.orangecarrier.com?token={encoded_token}"

print(f"🚀 Starting OrangeCarrier Socket.IO bridge...")
print(f"🌐 Connecting to: {SERVER_URL}")

# ================ DATA STORAGE ================
DATA_DIR = Path("/tmp/orangecarrier_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "seen.sqlite"
conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, first_seen TEXT)")
conn.commit()

# ================ TELEGRAM BOT ================
bot = Bot(token=BOT_TOKEN)

def send_to_telegram(text, audio_path=None):
    try:
        if audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as f:
                bot.send_audio(chat_id=TARGET_CHAT_ID, audio=InputFile(f), caption=text)
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text=text)
    except Exception as e:
        print("⚠️ Telegram send failed:", e)

# ================ HELPER ================
def is_seen(item_id):
    cur.execute("SELECT 1 FROM seen WHERE id=?", (item_id,))
    return cur.fetchone() is not None

def mark_seen(item_id):
    try:
        cur.execute("INSERT INTO seen (id, first_seen) VALUES (?, ?)", (item_id, datetime.now().isoformat()))
        conn.commit()
    except Exception:
        pass

# ================ SOCKET.IO CLIENT ================
sio = socketio.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=5, logger=False, engineio_logger=False)

@sio.event
def connect():
    print("✅ [SIO] Connected successfully!")
    send_to_telegram("✅ Connected to OrangeCarrier WebSocket!")
    print("🔐 [SIO] Sending auth event...")
    sio.emit("auth", {"token": ORANGE_TOKEN})

@sio.event
def disconnect():
    print("🔴 [SIO] Disconnected! Retrying...")
    send_to_telegram("🔴 Lost connection. Reconnecting...")

@sio.event
def connect_error(e):
    print(f"💥 [SIO] Connection error: {e}")

@sio.on("auth_response")
def on_auth_response(data):
    print("🧠 [SIO] Auth response received:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    send_to_telegram(f"🧠 Auth Response:\n{data}")

@sio.on("call")
def on_call(data):
    try:
        if isinstance(data, dict):
            call_id = str(data.get("id", time.time()))
            if is_seen(call_id):
                return
            mark_seen(call_id)
            text = json.dumps(data, indent=2, ensure_ascii=False)
            send_to_telegram(f"📞 New Call Received:\n{text}")
        else:
            send_to_telegram(f"📡 Event Data:\n{data}")
    except Exception as e:
        print("⚠️ Parse error:", e)

@sio.on("*")
def catch_all(event, data=None):
    print(f"📩 [SIO] Event received → {event}: {data}")

def start_socket():
    while True:
        try:
            print("🚀 Attempting to connect via Socket.IO...")
            sio.connect(SERVER_URL, transports=["websocket"])
            sio.wait()
        except Exception as e:
            print(f"⚠️ [SIO] Connection lost: {e}")
            print("🔁 Retrying in 5s...\n")
            time.sleep(5)

# ================ TELEGRAM COMMANDS ================
def status_command(update: Update, context: CallbackContext):
    connected = sio.connected
    update.message.reply_text(
        f"🤖 Bot is running!\n"
        f"Socket: {'🟢 Connected' if connected else '🔴 Disconnected'}"
    )

def ping_command(update: Update, context: CallbackContext):
    update.message.reply_text("🏓 Pong! Bot is alive and connected.")

# Register commands
updater = Updater(BOT_TOKEN)
dp = updater.dispatcher
dp.add_handler(CommandHandler("status", status_command))
dp.add_handler(CommandHandler("ping", ping_command))

# Start polling
updater.start_polling()
print("🤖 Telegram bot running...")

# ================ FLASK SERVER (keep alive) ================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ OrangeCarrier WebSocket Bridge active on Railway."

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run_flask, daemon=True).start()

# ================ START =================
if __name__ == "__main__":
    print("🚀 Launching OrangeCarrier WebSocket bridge...")
    send_to_telegram("🚀 Bot started... Connecting to OrangeCarrier WebSocket...")
    start_socket()

if is_seen(call_id):
    return
mark_seen(call_id)
            text = json.dumps(data, indent=2, ensure_ascii=False)
            send_to_telegram(f"📞 New Call Received:\n{text}")
        else:
            send_to_telegram(f"📡 Event Data:\n{data}")
    except Exception as e:
        print("⚠️ Parse error:", e)

@sio.on("*")
def catch_all(event, data=None):
    print(f"📩 [SIO] Event received → {event}: {data}")

def start_socket():
    while True:
        try:
            print("🚀 Attempting to connect via Socket.IO...")
            sio.connect(SERVER_URL, transports=["websocket"])
            sio.wait()
        except Exception as e:
            print(f"⚠️ [SIO] Connection lost: {e}")
            print("🔁 Retrying in 5s...\n")
            time.sleep(5)

# ================ TELEGRAM COMMAND ================
def status_command(update, context):
    update.message.reply_text("🤖 Bot is running and WebSocket connected!")

updater = Updater(BOT_TOKEN)
dp = updater.dispatcher
dp.add_handler(CommandHandler("status", status_command))
updater.start_polling()
print("🤖 Telegram bot running...")

# ================ FLASK SERVER (keep alive) ================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ OrangeCarrier WebSocket Bridge active on Railway."

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run_flask, daemon=True).start()

# ================ START =================
if __name__ == "__main__":
    print("🚀 Launching OrangeCarrier WebSocket bridge...")
    send_to_telegram("🚀 Bot started... Connecting to OrangeCarrier WebSocket...")
    start_socket()
