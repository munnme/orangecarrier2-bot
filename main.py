"""
Orangecarrier -> Telegram bridge (WebSocket version, no cookie/login)
"""
import sys, types
sys.modules['imghdr'] = types.ModuleType('imghdr')

import os, time, json, sqlite3, threading
from pathlib import Path
from datetime import datetime
from telegram import InputFile, Bot
import websocket

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
WS_URL = os.getenv("WS_URL", "wss://www.orangecarrier.com/socket.io/?token=YOUR_TOKEN_HERE")

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
        cur.execute("INSERT INTO seen (id, first_seen) VALUES (?, ?)", (item_id, datetime.now().isoformat()))
        conn.commit()
    except Exception:
        pass

# ================ TELEGRAM =================
bot = Bot(token=BOT_TOKEN)

def send_to_telegram(item, audio_path=None):
    """
    Sends message or audio to Telegram
    """
    text = item.get("text", "")
    body = f"🔔 New WebSocket event\n\n{text[:1000]}"
    try:
        if audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as f:
                bot.send_audio(chat_id=TARGET_CHAT_ID, audio=InputFile(f), caption=body)
        else:
            bot.send_message(chat_id=TARGET_CHAT_ID, text=body)
    except Exception as e:
        print("Telegram send failed:", e)

# ================ WEBSOCKET LISTENER =================
def start_websocket():
    print("🔧 Loaded WS_URL:", WS_URL)
    """
    Connects to OrangeCarrier websocket and listens for real-time events
    """
    def on_message(ws, message):
        print("📩 Received:", message[:200])
        try:
            data = json.loads(message)
            if isinstance(data, list) and len(data) > 1:
                event_type = data[0]
                payload = data[1]

                if event_type == "call" and isinstance(payload, dict):
                    calls_data = payload.get("calls", {}).get("calls", [])
                    for call in calls_data:
                        call_id = str(call.get("id", time.time()))
                        if is_seen(call_id):
                            continue
                        mark_seen(call_id)
                        text = json.dumps(call, indent=2, ensure_ascii=False)
                        send_to_telegram({"text": f"📞 New Call Received:\n{text}"})
                else:
                    send_to_telegram({"text": f"📡 Event: {event_type}\n\n{json.dumps(payload, indent=2, ensure_ascii=False)}"})
        except Exception as e:
            print("⚠️ WebSocket parse error:", e)

    def on_error(ws, error):
        print("❌ WebSocket error:", error)

    def on_close(ws, code, msg):
        print("🔴 WebSocket closed:", code, msg)
        bot.send_message(chat_id=TARGET_CHAT_ID, text="🔴 WebSocket disconnected. Reconnecting in 5s...")
        time.sleep(5)
        start_websocket()

    def on_open(ws):
        print("🟢 Connected to OrangeCarrier WebSocket")
        bot.send_message(chat_id=TARGET_CHAT_ID, text="🟢 Connected to OrangeCarrier WebSocket!")

    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()

# ================ TELEGRAM COMMAND ================
from telegram.ext import Updater, CommandHandler

def status_command(update, context):
    update.message.reply_text("🤖 Bot is running and listening via WebSocket!")

updater = Updater(BOT_TOKEN)
dp = updater.dispatcher
dp.add_handler(CommandHandler("status", status_command))
updater.start_polling()
print("🤖 Telegram bot is running...")

# ================ MAIN =================
def main_loop():
    bot.send_message(chat_id=TARGET_CHAT_ID, text="🚀 Bot started... Connecting to WebSocket...")
    start_websocket()

# 🔹 Flask সার্ভার (optional)
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ OrangeCarrier WebSocket Bridge Bot is running."

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run_flask, daemon=True).start()

# 🔹 Start Main
if __name__ == "__main__":
    print("Starting bridge (WebSocket mode)...")
    main_loop()
