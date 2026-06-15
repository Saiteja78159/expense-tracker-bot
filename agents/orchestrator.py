"""
agents/orchestrator.py — Intelligent Master Coordinator v2

NEW FEATURES:
  ✅ Smart NLP — understands any natural language, not just keywords
  ✅ Hinglish support — "100 rupees kharcha hua lunch pe" works
  ✅ Conversational queries — "how much did I spend on food?"
  ✅ Spending insights & trends
  ✅ Budget alerts — warns at 80%, alerts at 100%
  ✅ Graceful fallback — never crashes on LLM failure
"""

import json
import logging
from agents.parser import ParserAgent
from agents.classifier import ClassifierAgent
from agents.budget_checker import BudgetCheckerAgent
from agents.storage import StorageAgent
from agents.reply import ReplyAgent
from agents.insights import InsightsAgent
from utils.llm import ask_llm

logger = logging.getLogger(__name__)

# ── Intent detection ───────────────────────────────────────────────────────────
SUMMARY_KEYWORDS = ["summary", "report", "week", "weekly", "last 7", "past week"]
BUDGET_KEYWORDS  = ["budget", "limit", "remaining", "kitna bacha", "left", "how much left"]
INSIGHT_KEYWORDS = ["insight", "trend", "analysis", "compare", "spending pattern",
                    "most spent", "category wise", "breakdown", "sabse zyada"]
QUERY_KEYWORDS   = ["how much did", "kitna spent", "total spent", "spent on",
                    "did i spend", "expense on", "what did i spend", "how much have i"]


class OrchestratorAgent:
    def __init__(self):
        self.parser         = ParserAgent()
        self.classifier     = ClassifierAgent()
        self.budget_checker = BudgetCheckerAgent()
        self.storage        = StorageAgent()
        self.reply          = ReplyAgent()
        self.insights       = InsightsAgent()

    async def handle(self, user_id: str, message: str) -> str:
        intent, meta = await self._detect_intent(message)
        logger.info(f"Intent: {intent} | message: {message[:60]}")

        if intent == "summary":
            return await self.reply.weekly_summary(user_id)

        if intent == "budget":
            return await self.reply.budget_status(user_id)

        if intent == "insights":
            return await self.insights.spending_insights(user_id)

        if intent == "query":
            return await self.insights.answer_query(user_id, message)

        # ── Expense flow ───────────────────────────────────────────────────────
        parsed = await self.parser.parse(message)
        if not parsed:
            return (
                "🤔 I couldn't understand that.\n\n"
                "Try:\n"
                "• `spent 300 on dinner`\n"
                "• `100 rupees kharcha hua lunch pe`\n"
                "• `paid 1200 electricity bill`\n"
                "• `had coffee for 80 bucks`\n\n"
                "Or ask: `how much did I spend this week?`"
            )

        if not parsed.get("category"):
            parsed["category"] = await self.classifier.classify(
                parsed.get("description", message)
            )

        budget_info = await self.budget_checker.check(
            user_id=user_id,
            category=parsed["category"],
            amount=parsed["amount"],
        )

        await self.storage.save(user_id=user_id, expense=parsed)

        reply = await self.reply.expense_logged(parsed, budget_info)

        # ── Proactive budget alert ─────────────────────────────────────────────
        alert = self._budget_alert(budget_info, parsed["category"])
        if alert:
            reply += f"\n\n{alert}"

        return reply

    # ── Intent detection ───────────────────────────────────────────────────────
    async def _detect_intent(self, message: str):
        """
        Returns (intent, meta) where intent is one of:
        expense | summary | budget | insights | query

        Uses keyword fast-path first, then LLM for ambiguous messages.
        Never crashes — defaults to 'expense' on any error.
        """
        lower = message.lower().strip()

        if any(w in lower for w in SUMMARY_KEYWORDS):
            return "summary", {}
        if any(w in lower for w in BUDGET_KEYWORDS):
            return "budget", {}
        if any(w in lower for w in INSIGHT_KEYWORDS):
            return "insights", {}
        if any(w in lower for w in QUERY_KEYWORDS):
            return "query", {}

        # Common expense patterns — skip LLM
        expense_triggers = [
            # English
            "spent", "spend", "paid", "pay", "bought", "buy",
            "had lunch", "had dinner", "had breakfast", "had coffee",
            "cost me", "for lunch", "for dinner", "for breakfast",
            "₹", "dinner", "lunch", "breakfast", "coffee", "bill",
            "petrol", "fuel", "medicine", "movie", "ticket",
            # Hinglish / Hindi
            "kharcha hua", "kharach hua", "kharcha kiya", "lagaya", "lagaye",
            "diya", "rupees", "rs ", "pe lunch", "pe dinner", "pe chai",
            "pe breakfast", "mein lagaye", "ka bill", "ki fees",
        ]
        if any(w in lower for w in expense_triggers):
            return "expense", {}

        # LLM fallback for ambiguous messages
        try:
            system = """You classify a user message about personal finance into one of these intents:
- 'expense': user is logging money they spent (e.g. "had lunch for 100", "50 pe chai pee")
- 'summary': user wants a spending summary/report
- 'budget': user wants to check budget limits/remaining
- 'insights': user wants spending trends or analysis
- 'query': user is asking a specific question about their spending

Reply with ONLY one word: expense, summary, budget, insights, or query."""
            intent = await ask_llm(system, message)
            intent = intent.strip().lower()
            if intent in ("expense", "summary", "budget", "insights", "query"):
                return intent, {}
        except Exception as e:
            logger.warning(f"LLM intent detection failed: {e}")

        return "expense", {}

    # ── Budget alerts ──────────────────────────────────────────────────────────
    def _budget_alert(self, budget_info: dict, category: str) -> str:
        percent = budget_info.get("percent", 0)
        remaining = budget_info.get("remaining", 0)

        if budget_info.get("over_budget"):
            return (
                f"🚨 *Budget Alert!* You've exceeded your *{category}* limit!\n"
                f"Consider reviewing your spending in this category."
            )
        elif percent >= 90:
            return (
                f"⚠️ *Warning!* You've used *{percent:.0f}%* of your {category} budget.\n"
                f"Only ₹{remaining:,.0f} left!"
            )
        elif percent >= 80:
            return (
                f"💡 *Heads up!* {category} budget is *{percent:.0f}% used*.\n"
                f"₹{remaining:,.0f} remaining this month."
            )
        return ""