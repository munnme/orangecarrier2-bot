# 📞 Orangecarrier → Telegram Bridge Bot

A Telegram bot that monitors your [OrangeCarrier](https://www.orangecarrier.com) account for live call data and sends updates (audio/text) to a Telegram group or channel.

---

## 🚀 Features
- Sends a startup message when the bot launches
- Checks if your OrangeCarrier session cookie is valid
- Posts a success or error message accordingly
- Polls for new call data and sends them to Telegram

---

## 🛠 Setup on Railway

1. Fork or upload this repo to your GitHub.
2. Go to [Railway.app](https://railway.app/new).
3. Connect your GitHub repository.
4. Add the following environment variables in Railway:

BOT_TOKEN=your_telegram_bot_token TARGET_CHAT_ID=-100xxxxxxxxxx OC_SESSION_COOKIE=your_orangecarrier_cookie POLL_INTERVAL=20

5. Deploy 🚀  
Once running, your bot will send:
- “🤖 Bot started successfully”
- “✅ Orange Carrier account login successfully!” (if cookie valid)
- Or “❌ Orange Carrier not login or cookie invalid.”

---

## 🧩 Requirements

requests beautifulsoup4 python-telegram-bot==13.15

---
