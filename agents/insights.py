"""
agents/insights.py — Spending Insights & Conversational Query Agent

Handles:
  - "How much did I spend on food this week?"
  - "What's my biggest expense category?"
  - "Show me my spending trends"
  - "Kitna kharcha hua is hafte?"
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List
from utils.sheets import get_monthly_expenses, get_spending_by_category, get_budgets
from utils.llm import ask_llm

logger = logging.getLogger(__name__)


class InsightsAgent:

    async def spending_insights(self, user_id: str) -> str:
        """Returns a rich spending analysis with trends."""
        expenses = get_monthly_expenses(user_id)
        budgets  = get_budgets(user_id)

        if not expenses:
            return "📭 No expenses recorded this month yet.\n\nStart by sending: `spent 100 on lunch`"

        # Category breakdown
        by_category: Dict[str, float] = {}
        for e in expenses:
            cat = e["category"]
            by_category[cat] = by_category.get(cat, 0.0) + e["amount"]

        total = sum(by_category.values())
        sorted_cats = sorted(by_category.items(), key=lambda x: -x[1])

        # Week-over-week comparison
        now = datetime.utcnow().date()
        this_week_cutoff = (now - timedelta(days=7)).isoformat()
        last_week_cutoff = (now - timedelta(days=14)).isoformat()

        this_week_total = sum(
            e["amount"] for e in expenses
            if e["date"] >= this_week_cutoff
        )
        last_week_total = sum(
            e["amount"] for e in expenses
            if last_week_cutoff <= e["date"] < this_week_cutoff
        )

        lines = ["📊 *Spending Insights — This Month*\n"]

        # Top categories
        lines.append("*🏆 Top Categories:*")
        for i, (cat, amt) in enumerate(sorted_cats[:5], 1):
            pct = (amt / total * 100) if total else 0
            budget_limit = budgets.get(cat, 0)
            bar = self._mini_bar(pct)
            over = " ⚠️" if budget_limit and amt > budget_limit else ""
            lines.append(f"  {i}. *{cat}*: ₹{amt:,.0f} ({pct:.0f}%){over}\n     {bar}")

        lines.append(f"\n💸 *Total this month:* ₹{total:,.0f}")

        # Week comparison
        lines.append("\n*📅 Week-over-week:*")
        if last_week_total > 0:
            change = ((this_week_total - last_week_total) / last_week_total) * 100
            arrow = "📈" if change > 0 else "📉"
            lines.append(
                f"  This week: ₹{this_week_total:,.0f}\n"
                f"  Last week: ₹{last_week_total:,.0f}\n"
                f"  {arrow} {abs(change):.0f}% {'more' if change > 0 else 'less'} than last week"
            )
        else:
            lines.append(f"  This week: ₹{this_week_total:,.0f}")

        # Biggest single expense
        if expenses:
            biggest = max(expenses, key=lambda e: e["amount"])
            lines.append(
                f"\n*💰 Biggest expense:* ₹{biggest['amount']:,.0f} on "
                f"{biggest['description']} ({biggest['date']})"
            )

        # Daily average
        days_this_month = now.day
        daily_avg = total / days_this_month if days_this_month > 0 else 0
        lines.append(f"\n*📆 Daily average:* ₹{daily_avg:,.0f}/day")

        return "\n".join(lines)

    async def answer_query(self, user_id: str, message: str) -> str:
        """Answers natural language questions about spending using LLM + real data."""
        expenses = get_monthly_expenses(user_id)
        budgets  = get_budgets(user_id)

        if not expenses:
            return "📭 No expenses recorded this month. Start logging expenses first!"

        # Prepare a data summary for the LLM
        by_category: Dict[str, float] = {}
        for e in expenses:
            cat = e["category"]
            by_category[cat] = by_category.get(cat, 0.0) + e["amount"]

        now = datetime.utcnow().date()
        this_week_cutoff = (now - timedelta(days=7)).isoformat()
        this_week: Dict[str, float] = {}
        for e in expenses:
            if e["date"] >= this_week_cutoff:
                cat = e["category"]
                this_week[cat] = this_week.get(cat, 0.0) + e["amount"]

        data_summary = {
            "this_month_by_category": by_category,
            "this_month_total": sum(by_category.values()),
            "this_week_by_category": this_week,
            "this_week_total": sum(this_week.values()),
            "budgets": budgets,
            "num_transactions": len(expenses),
        }

        system = f"""You are a helpful personal finance assistant. Answer the user's question 
about their spending using this data:

{data_summary}

Rules:
- Be concise and friendly
- Use ₹ for amounts
- Format numbers with commas (e.g. ₹1,200)
- If the data doesn't have what they need, say so
- Keep response under 150 words
- If message is in Hinglish, reply in Hinglish mix too"""

        try:
            answer = await ask_llm(system, message)
            return f"💬 {answer}"
        except Exception as e:
            logger.error(f"Query LLM failed: {e}")
            # Fallback: direct answer from data
            total = sum(by_category.values())
            top = max(by_category, key=by_category.get) if by_category else "N/A"
            return (
                f"📊 This month so far:\n"
                f"• Total spent: ₹{total:,.0f}\n"
                f"• Top category: {top} (₹{by_category.get(top, 0):,.0f})\n"
                f"• This week: ₹{sum(this_week.values()):,.0f}"
            )

    def _mini_bar(self, percent: float, width: int = 8) -> str:
        filled = round(min(percent, 100) / 100 * width)
        return "█" * filled + "░" * (width - filled)
