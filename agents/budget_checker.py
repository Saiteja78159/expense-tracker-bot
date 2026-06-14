"""
agents/budget_checker.py — Compares new expense against monthly budget limits.

Returns a dict that ReplyAgent uses to craft warning/confirmation messages:
{
    "category":    "Food",
    "spent":       3800.0,   # total spent this month INCLUDING new expense
    "limit":       5000.0,
    "remaining":   1200.0,
    "percent":     76.0,
    "over_budget": False,
    "warning":     False,    # True when percent >= BUDGET_WARN_PERCENT
}
"""

from typing import Dict
from config.settings import BUDGET_WARN_PERCENT
from utils.sheets import get_spending_by_category, get_budgets


class BudgetCheckerAgent:
    async def check(self, user_id: str, category: str, amount: float) -> Dict:
        """
        Fetches current month's spending + budget limits, then returns budget info
        AFTER adding the new `amount` (so the reply reflects the updated state).
        """
        # Current month spending (before this new expense)
        spending   = get_spending_by_category(user_id)
        budgets    = get_budgets(user_id)

        # Add this new expense to get the updated total
        previous   = spending.get(category, 0.0)
        new_total  = previous + amount

        limit      = budgets.get(category, 2000.0)
        remaining  = max(limit - new_total, 0.0)
        percent    = (new_total / limit * 100) if limit > 0 else 0.0

        return {
            "category":    category,
            "spent":       round(new_total, 2),
            "limit":       limit,
            "remaining":   round(remaining, 2),
            "percent":     round(percent, 1),
            "over_budget": new_total > limit,
            "warning":     percent >= (BUDGET_WARN_PERCENT * 100),
        }
