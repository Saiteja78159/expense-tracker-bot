"""
agents/storage.py — Writes a validated expense dict to Google Sheets.

This is intentionally a thin wrapper so the Orchestrator stays clean.
All actual Sheets logic lives in utils/sheets.py.
"""

from datetime import date
from typing import Dict
from utils.sheets import append_expense


class StorageAgent:
    async def save(self, user_id: str, expense: Dict) -> None:
        """
        Persists one expense row.

        Args:
            user_id:  Telegram user ID (string).
            expense:  Dict with keys: amount, category, description, date.
        """
        expense_date = date.fromisoformat(expense["date"])

        append_expense(
            user_id=user_id,
            amount=expense["amount"],
            category=expense["category"],
            description=expense.get("description", ""),
            expense_date=expense_date,
        )
