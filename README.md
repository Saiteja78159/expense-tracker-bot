# 💸 Expense Tracker Bot

A **Multi-Agent AI System** for effortless daily finance tracking via Telegram.

Built with: Python · FastAPI · Telegram Bot API · Llama 3 (Groq) · Google Sheets · Railway

---

## 📁 Project Structure

```
expense_tracker_bot/
│
├── main.py                   # FastAPI app + Telegram webhook entry point
│
├── agents/
│   ├── orchestrator.py       # Master coordinator — routes messages to sub-agents
│   ├── parser.py             # Extracts amount / category / date from free text
│   ├── classifier.py         # Maps description → spending category (LLM fallback)
│   ├── budget_checker.py     # Compares new expense against monthly limits
│   ├── storage.py            # Writes expense row to Google Sheets
│   └── reply.py              # Composes the final Telegram reply
│
├── utils/
│   ├── llm.py                # Thin wrapper around the Llama API (via Groq)
│   └── sheets.py             # Google Sheets read/write helpers
│
├── config/
│   └── settings.py           # All env vars + constants in one place
│
├── requirements.txt
├── Procfile                  # For Railway / Render deployment
└── .env.example              # Template — copy to .env and fill in values
```

---

## 🤖 How the 5-Agent Pipeline Works

```
User types "spent 250 on lunch"
        │
        ▼
┌─────────────────────┐
│  Orchestrator Agent │  Detects intent (expense / summary / budget)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│    Parser Agent     │  LLM call → {amount:250, category:"Food",
└────────┬────────────┘              description:"lunch", date:"2026-06-12"}
         │
         ▼
┌─────────────────────┐
│  Classifier Agent   │  Only called if parser returned no category.
└────────┬────────────┘  LLM maps description → one fixed category.
         │
         ▼
┌─────────────────────┐
│ Budget Checker Agent│  Reads current month spending from Sheets,
└────────┬────────────┘  computes remaining budget & warning flag.
         │
         ▼
┌─────────────────────┐
│   Storage Agent     │  Appends one row to the Google Sheets "Expenses" tab.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│    Reply Agent      │  Formats the final message and returns it.
└─────────────────────┘
        │
        ▼
"Food ₹250 logged ✓
 ₹3,200 left in Food budget.
 You're 64% through this month."
```

---

## 🛠️ Setup Guide

### 1. Clone & install dependencies

```bash
git clone https://github.com/yourname/expense-tracker-bot.git
cd expense-tracker-bot
pip install -r requirements.txt
```

### 2. Create a Telegram Bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot`, follow the prompts
3. Copy the **API token** → paste as `TELEGRAM_TOKEN` in `.env`

### 3. Get a free Llama API key (Groq)

1. Sign up at https://console.groq.com
2. Create an API key → paste as `GROQ_API_KEY` in `.env`

### 4. Set up Google Sheets

1. Create a new Google Sheet with two tabs: **Expenses** and **Budget**

**Expenses tab headers (Row 1):**
```
Timestamp | UserID | Date | Category | Amount | Description
```

**Budget tab headers (Row 1):**
```
UserID | Category | Limit
```
Fill in rows for each user + category with your desired monthly limits.

2. Go to **Google Cloud Console** → create a Service Account → download JSON key
3. Share your Google Sheet with the service account email (Editor access)
4. Paste the entire JSON as a single line in `GOOGLE_CREDENTIALS_JSON`
5. Copy your Sheet ID from the URL → `SPREADSHEET_ID`

### 5. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your real values
```

### 6. Deploy to Railway (free tier)

```bash
# Push to GitHub, then connect repo on railway.app
# Set all env vars in Railway dashboard
# Railway auto-detects Procfile and starts the server
```

After deployment, Railway gives you a public HTTPS URL.  
Set that as `WEBHOOK_URL` in your env vars and redeploy.

### 7. Run locally (for testing)

```bash
# For local testing use ngrok to get a public URL:
ngrok http 8000

# Set WEBHOOK_URL=https://xxxx.ngrok.io in .env, then:
python main.py
```

---

## 💬 Supported Commands

| What you type | What happens |
|---|---|
| `spent 250 on lunch` | Logs ₹250 under Food |
| `paid 1200 electricity` | Logs ₹1200 under Bills |
| `bought shoes 2500` | Logs ₹2500 under Shopping |
| `budget` | Shows all category budgets & remaining |
| `summary` | Shows last 7 days spending by category |
| `/start` | Welcome message |

---

## ⚙️ Customising Budgets

Edit the **Budget** tab in your Google Sheet:

| UserID | Category | Limit |
|---|---|---|
| 123456789 | Food | 6000 |
| 123456789 | Travel | 4000 |

Changes take effect immediately — no redeploy needed.

---

## 🔑 Key Design Decisions

| Decision | Reason |
|---|---|
| **Webhook over polling** | No busy-loop, works on free Railway tier with sleep |
| **Groq for LLM** | Free, fast (~1s latency), runs Llama 3 |
| **Google Sheets as DB** | Zero infra, user can view/edit their own data |
| **Separate agents** | Easy to swap/test each piece independently |
| **Async throughout** | Handles concurrent users without blocking |
