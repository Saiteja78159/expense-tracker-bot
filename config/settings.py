"""
config/settings.py — All environment variables and constants in one place.
Load from a .env file locally; on Railway/Render set them in the dashboard.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env when running locally

# ── Telegram ───────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN: str = os.environ["TELEGRAM_TOKEN"]       # Bot token from @BotFather
WEBHOOK_URL: str = os.environ["WEBHOOK_URL"]             # Public HTTPS URL of your server
PORT: int = int(os.getenv("PORT", 8000))

# ── Llama (via Groq or Ollama) ─────────────────────────────────────────────────
LLAMA_API_KEY: str = os.getenv("GROQ_API_KEY", "")      # Groq free tier for Llama 3
LLAMA_MODEL: str = os.getenv("LLAMA_MODEL", "llama3-8b-8192")
LLAMA_BASE_URL: str = os.getenv("LLAMA_BASE_URL", "https://api.groq.com/openai/v1")

# ── Google Sheets ───────────────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_JSON: str = os.environ["GOOGLE_CREDENTIALS_JSON"]  # Full JSON string
SPREADSHEET_ID: str = os.environ["SPREADSHEET_ID"]       # From the Google Sheet URL
EXPENSES_SHEET: str = "Expenses"                          # Tab name for expense rows
BUDGET_SHEET: str = "Budget"                              # Tab name for monthly limits

# ── Budget defaults (₹) — overridden by the Budget sheet ──────────────────────
DEFAULT_BUDGETS: dict = {
    "Food":        5000,
    "Travel":      3000,
    "Bills":       4000,
    "Shopping":    3000,
    "Health":      2000,
    "Entertainment": 1500,
    "Other":       2000,
}

# ── Warning threshold ──────────────────────────────────────────────────────────
BUDGET_WARN_PERCENT: float = 0.80   # Alert when 80 % of any category is used
