"""
main.py — Entry point for the Expense Tracker Bot
Starts the FastAPI webhook server that receives Telegram messages.
"""

import uvicorn
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters

from config.settings import TELEGRAM_TOKEN, WEBHOOK_URL, PORT
from agents.orchestrator import OrchestratorAgent

# ─── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Expense Tracker Bot")

# ─── Telegram Application ─────────────────────────────────────────────────────
telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
orchestrator = OrchestratorAgent()


# ─── Command Handlers ─────────────────────────────────────────────────────────
async def start_command(update: Update, context):
    """Handles /start — greets the user."""
    await update.message.reply_text(
        "👋 Hi! I'm your *Expense Tracker Bot*.\n\n"
        "Just type naturally:\n"
        "• `spent 250 on lunch`\n"
        "• `paid 1200 electricity`\n"
        "• `summary` — weekly report\n"
        "• `budget` — check remaining limits\n\n"
        "I'll log everything to your Google Sheet automatically! 📊",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context):
    """Routes every incoming message through the Orchestrator Agent."""
    user_id = str(update.effective_user.id)
    user_text = update.message.text.strip()

    # Show "typing…" indicator while processing
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # Hand off to the orchestrator — it coordinates all sub-agents
    reply = await orchestrator.handle(user_id=user_id, message=user_text)
    await update.message.reply_text(reply, parse_mode="Markdown")


# Register handlers
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ─── Webhook Endpoint ──────────────────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    """Receives Telegram updates via webhook and dispatches them."""
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}


@app.get("/")
async def health():
    return {"status": "Expense Tracker Bot is running 🚀"}


# ─── Startup: register webhook with Telegram ──────────────────────────────────
@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print(f"✅ Webhook set to {WEBHOOK_URL}/webhook")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
