"""
agents/orchestrator.py — The master coordinator.

Responsibilities:
  1. Decides whether the user is logging an expense or asking for a report.
  2. Calls the right sub-agents in sequence.
  3. Returns a single formatted reply string.

Flow for an expense message:
  Parser → Classifier → BudgetChecker → StorageAgent → ReplyAgent

Flow for "summary" / "budget":
  Directly queries sheets and delegates to ReplyAgent.
"""

import logging
import json
from agents.parser import ParserAgent
from agents.classifier import ClassifierAgent
from agents.budget_checker import BudgetCheckerAgent
from agents.storage import StorageAgent
from agents.reply import ReplyAgent
from utils.llm import ask_llm

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    def __init__(self):
        self.parser          = ParserAgent()
        self.classifier      = ClassifierAgent()
        self.budget_checker  = BudgetCheckerAgent()
        self.storage         = StorageAgent()
        self.reply           = ReplyAgent()

    async def handle(self, user_id: str, message: str) -> str:
        """Main entry point. Returns the final reply string."""

        # ── Step 1: Detect intent ──────────────────────────────────────────────
        intent = await self._detect_intent(message)

        if intent == "summary":
            return await self.reply.weekly_summary(user_id)

        if intent == "budget":
            return await self.reply.budget_status(user_id)

        # ── Step 2: Parse the expense ──────────────────────────────────────────
        parsed = await self.parser.parse(message)
        if not parsed:
            return (
                "🤔 I couldn't understand that. Try:\n"
                "`spent 250 on lunch`\n"
                "`paid 1200 electricity bill`"
            )

        # ── Step 3: Classify category (if parser didn't determine it) ──────────
        if not parsed.get("category"):
            parsed["category"] = await self.classifier.classify(
                parsed.get("description", message)
            )

        # ── Step 4: Check budget ───────────────────────────────────────────────
        budget_info = await self.budget_checker.check(
            user_id=user_id,
            category=parsed["category"],
            amount=parsed["amount"],
        )

        # ── Step 5: Store to Google Sheet ─────────────────────────────────────
        await self.storage.save(user_id=user_id, expense=parsed)

        # ── Step 6: Build reply ────────────────────────────────────────────────
        return await self.reply.expense_logged(parsed, budget_info)

    # ── Intent detection ───────────────────────────────────────────────────────
    async def _detect_intent(self, message: str) -> str:
        """
        Returns 'expense', 'summary', or 'budget'.
        Uses keyword matching first, then LLM fallback.
        If LLM fails (e.g. missing API key), defaults to 'expense'.
        """
        lower = message.lower().strip()

        # Fast path for obvious keywords — no LLM call needed
        if any(w in lower for w in ["summary", "report", "week", "weekly"]):
            return "summary"
        if any(w in lower for w in ["budget", "limit", "remaining", "left"]):
            return "budget"
        # Common expense keywords — skip LLM entirely
        if any(w in lower for w in ["spent", "paid", "bought", "spend", "pay", "purchased"]):
            return "expense"

        # LLM fallback for ambiguous phrasing
        try:
            system = (
                "You classify a user message into one of three intents: "
                "'expense' (logging money spent), 'summary' (asking for a spending report), "
                "or 'budget' (asking how much budget is left). "
                "Reply with ONLY one word: expense, summary, or budget."
            )
            intent = await ask_llm(system, message)
            intent = intent.strip().lower()
            return intent if intent in ("expense", "summary", "budget") else "expense"
        except Exception as e:
            logger.warning(f"LLM intent detection failed, defaulting to 'expense': {e}")
            return "expense"
