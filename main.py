"""
main.py — Entry point for the Expense Tracker Bot

New features:
  ✅ Multiple expenses in one message ("200 meals, 300 electricity bill")
  ✅ Voice message support via Groq Whisper transcription
"""

import io
import logging
import uvicorn
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters

from config.settings import TELEGRAM_TOKEN, WEBHOOK_URL, PORT, LLAMA_API_KEY
from agents.orchestrator import OrchestratorAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Expense Tracker Bot")

# ─── Telegram Application ─────────────────────────────────────────────────────
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
orchestrator = OrchestratorAgent()

GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


# ─── Voice transcription ───────────────────────────────────────────────────────
async def transcribe_voice(file_bytes: bytes, filename: str = "audio.ogg") -> str:
    """Transcribes a voice message using Groq Whisper API."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GROQ_WHISPER_URL,
            headers={"Authorization": f"Bearer {LLAMA_API_KEY}"},
            files={"file": (filename, io.BytesIO(file_bytes), "audio/ogg")},
            data={"model": "whisper-large-v3-turbo", "language": "en"},
        )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()


# ─── Multi-expense splitter ────────────────────────────────────────────────────
def split_multi_expense(message: str) -> list[str]:
    """
    Splits a message with multiple expenses into individual parts.

    Examples:
      "200 meals, 300 electricity bill"  → ["200 meals", "300 electricity bill"]
      "spent 100 on lunch and 50 on tea" → ["spent 100 on lunch", "50 on tea"]
      "paid 500 rent"                    → ["paid 500 rent"]  (single, no split)
    """
    import re

    # Separators: comma, semicolon, " and ", " & "
    parts = re.split(r",\s*|;\s*|\s+and\s+|\s+&\s+", message, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]

    # Only split if each part looks like it has a number (expense amount)
    valid_parts = [p for p in parts if re.search(r'\d', p)]
    return valid_parts if len(valid_parts) > 1 else [message]


# ─── Command Handlers ──────────────────────────────────────────────────────────
async def start_command(update: Update, context):
    await update.message.reply_text(
        "👋 Hi! I'm your *Expense Tracker Bot*.\n\n"
        "Just type naturally:\n"
        "• `spent 250 on lunch`\n"
        "• `paid 1200 electricity`\n"
        "• `200 meals, 300 electricity bill` *(multiple at once!)*\n"
        "• `summary` — weekly report\n"
        "• `budget` — check remaining limits\n"
        "• `insights` — spending trends\n"
        "• 🎤 *Send a voice message* — I'll transcribe it!\n\n"
        "I'll log everything to your Google Sheet automatically! 📊",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context):
    """Routes text messages — supports multiple expenses in one message."""
    user_id = str(update.effective_user.id)
    user_text = update.message.text.strip()

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Check if this is a single-intent message (summary/budget/insights/query)
    # If so, pass directly without splitting
    lower = user_text.lower()
    single_intent_keywords = [
        "summary", "budget", "insight", "report", "weekly", "how much",
        "kitna", "trend", "analysis", "remaining", "left", "bacha"
    ]
    is_single_intent = any(w in lower for w in single_intent_keywords)

    if is_single_intent:
        reply = await orchestrator.handle(user_id=user_id, message=user_text)
        await update.message.reply_text(reply, parse_mode="Markdown")
        return

    # Try splitting into multiple expenses
    parts = split_multi_expense(user_text)

    if len(parts) == 1:
        # Single expense — normal flow
        reply = await orchestrator.handle(user_id=user_id, message=user_text)
        await update.message.reply_text(reply, parse_mode="Markdown")
    else:
        # Multiple expenses — process each and combine replies
        replies = []
        for part in parts:
            try:
                reply = await orchestrator.handle(user_id=user_id, message=part)
                replies.append(reply)
            except Exception as e:
                logger.error(f"Error processing part '{part}': {e}")
                replies.append(f"⚠️ Could not process: `{part}`")

        combined = f"📝 *Logged {len(parts)} expenses:*\n\n" + "\n\n".join(replies)
        await update.message.reply_text(combined, parse_mode="Markdown")


async def handle_voice(update: Update, context):
    """Handles voice messages — transcribes then processes as text."""
    user_id = str(update.effective_user.id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if not LLAMA_API_KEY:
        await update.message.reply_text("⚠️ Voice transcription not configured.")
        return

    try:
        # Download voice file from Telegram
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        file_bytes = await file.download_as_bytearray()

        # Transcribe using Groq Whisper
        transcribed = await transcribe_voice(bytes(file_bytes))

        if not transcribed:
            await update.message.reply_text("🎤 Couldn't understand the audio. Please try again.")
            return

        # Show what was transcribed
        await update.message.reply_text(f"🎤 *Heard:* _{transcribed}_", parse_mode="Markdown")

        # Process transcribed text as normal message
        parts = split_multi_expense(transcribed)

        if len(parts) == 1:
            reply = await orchestrator.handle(user_id=user_id, message=transcribed)
        else:
            replies = []
            for part in parts:
                reply = await orchestrator.handle(user_id=user_id, message=part)
                replies.append(reply)
            reply = f"📝 *Logged {len(parts)} expenses:*\n\n" + "\n\n".join(replies)

        await update.message.reply_text(reply, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Voice handling error: {e}")
        await update.message.reply_text(
            "⚠️ Voice processing failed. Please type your expense instead."
        )


# ─── Register handlers ─────────────────────────────────────────────────────────
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
telegram_app.add_handler(MessageHandler(filters.VOICE, handle_voice))


# ─── Webhook Endpoint ──────────────────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}


@app.get("/")
async def health():
    return {"status": "Expense Tracker Bot is running 🚀"}


@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print(f"✅ Webhook set to {WEBHOOK_URL}/webhook")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)