"""
agents/parser.py — Smart NLP Expense Parser v2

Understands:
  ✅ "spent 300 on dinner"
  ✅ "had lunch for 100 bucks"
  ✅ "100 rupees kharcha hua lunch pe"
  ✅ "paid 1200 electricity bill yesterday"
  ✅ "coffee 80"
  ✅ "dinner cost me 500"
  ✅ "50 pe chai pee"
"""

import json
import re
from datetime import date, timedelta
from typing import Optional, Dict

from utils.llm import ask_llm

LLAMA_MODEL = "llama-3.1-8b-instant"


def _build_system_prompt():
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))
    return f"""You are a multilingual expense parsing assistant. You understand English, Hindi, and Hinglish.
Today's date is {today}.

Extract expense details from the user's message and return ONLY this JSON:

{{
  "amount": <number>,
  "category": "<one of: Food, Travel, Bills, Shopping, Health, Entertainment, Other>",
  "description": "<short clean description in English>",
  "date": "<YYYY-MM-DD>"
}}

Rules:
- "amount": positive number only (no currency symbols). Handle: "100 rupees", "₹200", "50 bucks", "Rs 300"
- "category": classify based on context:
    Food = meals, restaurants, groceries, chai, coffee, lunch, dinner, breakfast, khana
    Travel = petrol, fuel, auto, cab, uber, ola, bus, train, flight
    Bills = electricity, rent, wifi, internet, mobile, recharge, EMI
    Shopping = clothes, shoes, electronics, amazon, flipkart, mall
    Health = medicine, doctor, hospital, pharmacy, gym
    Entertainment = movie, game, netflix, concert, party
    Other = anything else
- "description": 2-5 word English summary of what was spent on
- "date": today={today}, yesterday={yesterday}, any relative date → calculate

Hinglish examples:
- "100 rupees kharcha hua lunch pe" → amount=100, category=Food, description="lunch"
- "50 pe chai pee" → amount=50, category=Food, description="tea/chai"
- "petrol mein 500 lagaye" → amount=500, category=Travel, description="petrol"
- "bijli ka bill 1200 diya" → amount=1200, category=Bills, description="electricity bill"

If no expense found, return: {{"error": "not an expense"}}"""


class ParserAgent:
    async def parse(self, message: str) -> Optional[Dict]:
        """
        Parses any natural-language expense message (English/Hindi/Hinglish).
        Returns a dict with amount/category/description/date, or None on failure.
        """
        # Quick regex pre-check — if no number in message, skip LLM
        if not re.search(r'\d', message):
            return None

        try:
            raw = await ask_llm(_build_system_prompt(), message, expect_json=True)
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = self._regex_fallback(message)
            if not data:
                return None
        except Exception:
            data = self._regex_fallback(message)
            if not data:
                return None

        if "error" in data:
            return None

        if not data.get("amount") or float(data["amount"]) <= 0:
            return None

        data["amount"] = float(data["amount"])
        data["date"]   = data.get("date") or str(date.today())
        data["category"] = data.get("category", "Other")
        data["description"] = data.get("description", message[:50])

        return data

    def _regex_fallback(self, message: str) -> Optional[Dict]:
        """
        Extracts amount from any message as a last resort.
        Handles: "₹300", "Rs 200", "300 rupees", "300"
        """
        # Try to find amount with currency indicators
        patterns = [
            r'₹\s*(\d+(?:\.\d+)?)',        # ₹300
            r'rs\.?\s*(\d+(?:\.\d+)?)',     # Rs 300 or rs300
            r'(\d+(?:\.\d+)?)\s*rupees?',  # 300 rupees
            r'(\d+(?:\.\d+)?)\s*bucks?',   # 300 bucks
            r'\b(\d+(?:\.\d+)?)\b',        # plain number
        ]
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                amount = float(match.group(1))
                if amount > 0:
                    return {
                        "amount":      amount,
                        "category":    "Other",
                        "description": message[:50].strip(),
                        "date":        str(date.today()),
                    }
        return None
