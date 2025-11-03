"""
OrangeCarrier -> Telegram Bridge (Socket.IO + WebSocket only, fully auto reconnect)
"""
import os, json, time, sqlite3, threading
from datetime import datetime
from pathlib import Path
from telegram import Bot, InputFile
from telegram.ext import Updater, CommandHandler
from flask import Flask
import socketio


# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
ORANGE_TOKEN = os.getenv("ORANGE_TOKEN")


if not BOT_TOKEN or not TARGET_CHAT_ID or not ORANGE_TOKEN: 
    
    raise RuntimeError("❌ BOT_TOKEN, TARGET_CHAT_ID, ORANGE_TOKEN must be set in Railway environment variables!")


print(f"🔐 BOT_TOKEN={BOT_TOKEN[:5]}..., CHAT_ID={TARGET_CHAT_ID}, ORANGE_TOKEN={ORANGE_TOKEN[:10]}...")

WS_URL = f"https://hub.orangecarrier.com/socket.io/?EIO=4&transport=websocket&token={ORANGE_TOKEN}"

# ================ PATHS ==================
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
    """Send message or audio file to Telegram"""
    try:
        if audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as f:
                bot.send_audio(chat_id=TARGET_CHAT_ID, audio=InputFile(f), caption=text)
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text=text)
    except Exception as e:
        print("⚠️ Telegram send failed:", e)

# ================ HELPER =================
def is_seen(item_id):
    cur.execute("SELECT 1 FROM seen WHERE id=?", (item_id,))
    return cur.fetchone() is not None

def mark_seen(item_id):
    try:
        cur.execute("INSERT INTO seen (id, first_seen) VALUES (?, ?)", (item_id, datetime.now().isoformat()))
        conn.commit()
    except Exception:
        pass

# ================ SOCKET.IO HANDLER =================
sio = socketio.Client(reconnection=True, reconnection_attempts=9999)

@sio.event
def connect():
    print("🟢 Connected successfully to OrangeCarrier Socket.IO!")
    send_to_telegram("🟢 Connected to OrangeCarrier WebSocket successfully!")

@sio.event
def disconnect():
    print("🔴 WebSocket disconnected. Reconnecting...")
    send_to_telegram("🔴 Lost connection. Reconnecting...")

@sio.event
def connect_error(e):
    print("❌ Connection error:", e)

@sio.on("call")
def on_call(data):
    """Handle new call event"""
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

def start_socket():
    while True:
        try:
            sio.connect(WS_URL, transports=["websocket"])
            sio.wait()
        except Exception as e:
            print("💥 Socket connection error:", e)
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
    return "✅ OrangeCarrier WebSocket Bridge is active and running on Railway."

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run_flask, daemon=True).start()

# ================ START =================
if __name__ == "__main__":
    print("🚀 Starting OrangeCarrier WebSocket bridge...")
    send_to_telegram("🚀 Bot started... Connecting to OrangeCarrier WebSocket...")
    start_socket()
