"""
agents/reply.py — Composes the final message the user sees in Telegram.

Three reply types:
  1. expense_logged  — confirmation + budget remaining
  2. budget_status   — full breakdown of all categories
  3. weekly_summary  — last 7 days totals + comparison
"""

from typing import Dict
from datetime import datetime, timedelta
from utils.sheets import get_monthly_expenses, get_spending_by_category, get_budgets


class ReplyAgent:

    # ── 1. Expense confirmation ────────────────────────────────────────────────
    async def expense_logged(self, expense: Dict, budget: Dict) -> str:
        """
        Returns a short confirmation message with budget status.

        Example:
          Food ₹250 logged ✓
          ₹3,200 left in Food budget.
          You're 64% through this month.
        """
        cat       = expense["category"]
        amount    = expense["amount"]
        remaining = budget["remaining"]
        percent   = budget["percent"]

        lines = [f"*{cat}* ₹{amount:,.0f} logged ✓"]

        if budget["over_budget"]:
            lines.append(f"⚠️ *Over budget!* You've exceeded your {cat} limit.")
        elif budget["warning"]:
            lines.append(
                f"Heads up: {cat} budget *{percent:.0f}% used!*\n"
                f"₹{remaining:,.0f} remaining."
            )
        else:
            lines.append(
                f"₹{remaining:,.0f} left in {cat} budget.\n"
                f"You're {percent:.0f}% through this month."
            )

        return "\n".join(lines)

    # ── 2. Budget status ───────────────────────────────────────────────────────
    async def budget_status(self, user_id: str) -> str:
        """
        Returns a full table of category → spent / limit / remaining.
        """
        spending = get_spending_by_category(user_id)
        budgets  = get_budgets(user_id)

        lines = ["📊 *Monthly Budget Status*\n"]
        total_spent = 0.0
        total_limit = 0.0

        for cat, limit in budgets.items():
            spent     = spending.get(cat, 0.0)
            remaining = max(limit - spent, 0.0)
            percent   = (spent / limit * 100) if limit else 0
            bar       = self._progress_bar(percent)
            status    = "⚠️" if percent >= 80 else "✅"
            lines.append(
                f"{status} *{cat}*\n"
                f"  {bar} {percent:.0f}%\n"
                f"  Spent ₹{spent:,.0f} / Limit ₹{limit:,.0f}  (₹{remaining:,.0f} left)\n"
            )
            total_spent += spent
            total_limit += limit

        lines.append(
            f"💰 *Total:* ₹{total_spent:,.0f} of ₹{total_limit:,.0f} spent this month."
        )
        return "\n".join(lines)

    # ── 3. Weekly summary ──────────────────────────────────────────────────────
    async def weekly_summary(self, user_id: str) -> str:
        """
        Returns last-7-days spending by category.
        """
        all_expenses = get_monthly_expenses(user_id)
        cutoff       = (datetime.utcnow() - timedelta(days=7)).date().isoformat()

        week_totals: Dict[str, float] = {}
        week_total  = 0.0

        for e in all_expenses:
            if e["date"] >= cutoff:
                cat = e["category"]
                week_totals[cat] = week_totals.get(cat, 0.0) + e["amount"]
                week_total       += e["amount"]

        if not week_totals:
            return "📭 No expenses recorded in the last 7 days."

        lines = ["📅 *Weekly Expense Summary* (last 7 days)\n"]
        for cat, total in sorted(week_totals.items(), key=lambda x: -x[1]):
            lines.append(f"  • *{cat}*: ₹{total:,.0f}")

        lines.append(f"\n💸 *Total this week:* ₹{week_total:,.0f}")
        return "\n".join(lines)

    # ── Utility ────────────────────────────────────────────────────────────────
    def _progress_bar(self, percent: float, width: int = 10) -> str:
        """Returns a simple ASCII progress bar: ██████░░░░"""
        filled = round(min(percent, 100) / 100 * width)
        return "█" * filled + "░" * (width - filled)
