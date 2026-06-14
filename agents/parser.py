"""
agents/parser.py — Extracts structured data from a free-text expense message.

Input:  "spent 250 on lunch with colleagues yesterday"
Output: {"amount": 250.0, "category": "Food", "description": "lunch with colleagues", "date": "2026-06-13"}

The LLM is prompted to return strict JSON. A regex fallback handles edge cases
where the model returns a malformed response.
"""

import json
import re
from datetime import date, timedelta
from typing import Optional, Dict

from utils.llm import ask_llm


def _build_system_prompt():
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))
    return f"""
You are an expense parsing assistant.
Today's date is {today}. Use this exact date when the message says "today" or has no date.
Extract expense details from the user's message and return ONLY this JSON:

{{
  "amount": <number>,
  "category": "<one of: Food, Travel, Bills, Shopping, Health, Entertainment, Other>",
  "description": "<short clean description>",
  "date": "<YYYY-MM-DD>"
}}

Rules:
- "amount" must be a positive number (no currency symbols).
- "category" must be exactly one of the listed options.
- "description" is a 2–5 word summary.
- "date": if the message says "today" or no date → use {today}.
         If "yesterday" → use {yesterday}. If a specific date is given → use it.
- If no expense is found, return: {{"error": "not an expense"}}
"""


class ParserAgent:
    async def parse(self, message: str) -> Optional[Dict]:
        """
        Parses a natural-language expense message.
        Returns a dict with amount/category/description/date, or None on failure.
        """
        raw = await ask_llm(_build_system_prompt(), message, expect_json=True)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Regex fallback: try to extract just the amount
            data = self._regex_fallback(message)
            if not data:
                return None

        if "error" in data:
            return None

        # Validate required fields
        if not data.get("amount") or float(data["amount"]) <= 0:
            return None

        # Normalise types
        data["amount"] = float(data["amount"])
        data["date"]   = data.get("date") or str(date.today())

        return data

    # ── Fallback ───────────────────────────────────────────────────────────────
    def _regex_fallback(self, message: str) -> Optional[Dict]:
        """
        Last-resort: pull a number from the message and mark category as Other.
        E.g. "250 lunch" → amount=250, description="lunch", category="Other"
        """
        match = re.search(r"\b(\d+(?:\.\d+)?)\b", message)
        if not match:
            return None
        return {
            "amount":      float(match.group(1)),
            "category":    "Other",
            "description": message[:50],
            "date":        str(date.today()),
        }