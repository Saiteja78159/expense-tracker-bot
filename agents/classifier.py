"""
agents/classifier.py — Maps a description to one of the fixed spending categories.

This agent is only called when the Parser did NOT return a category
(rare fallback path). It uses the LLM to do semantic classification.

Categories: Food | Travel | Bills | Shopping | Health | Entertainment | Other
"""

from utils.llm import ask_llm

_CATEGORIES = ["Food", "Travel", "Bills", "Shopping", "Health", "Entertainment", "Other"]

_SYSTEM_PROMPT = f"""
You are an expense categoriser.
Given a short expense description, reply with ONLY one word — the best matching category.

Valid categories: {', '.join(_CATEGORIES)}

Examples:
  "lunch at restaurant"   → Food
  "uber to office"        → Travel
  "electricity bill"      → Bills
  "new sneakers"          → Shopping
  "doctor consultation"   → Health
  "netflix subscription"  → Entertainment
  "miscellaneous"         → Other
"""


class ClassifierAgent:
    async def classify(self, description: str) -> str:
        """Returns a category string for the given description."""
        result = await ask_llm(_SYSTEM_PROMPT, description)
        result = result.strip().title()
        return result if result in _CATEGORIES else "Other"
