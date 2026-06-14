"""
utils/sheets.py — Google Sheets read/write helpers.
Uses a service-account JSON stored as an environment variable (no file on disk).
"""

import json
from datetime import datetime, date
from typing import List, Dict, Optional

import gspread
from google.oauth2.service_account import Credentials

from config.settings import (
    GOOGLE_CREDENTIALS_JSON,
    SPREADSHEET_ID,
    EXPENSES_SHEET,
    BUDGET_SHEET,
    DEFAULT_BUDGETS,
)

# ── Auth ───────────────────────────────────────────────────────────────────────
_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _get_client() -> gspread.Client:
    """Creates an authenticated gspread client from the env-variable JSON."""
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)
    return gspread.authorize(creds)


def _get_sheet(tab_name: str) -> gspread.Worksheet:
    client = _get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet.worksheet(tab_name)


# ── Write expense ──────────────────────────────────────────────────────────────

def append_expense(user_id: str, amount: float, category: str, description: str, expense_date: date) -> None:
    """
    Appends one expense row to the Expenses sheet.
    Columns: Timestamp | UserID | Date | Category | Amount | Description
    """
    sheet = _get_sheet(EXPENSES_SHEET)
    row = [
        datetime.utcnow().isoformat(timespec="seconds"),  # logged-at
        user_id,
        expense_date.strftime("%Y-%m-%d"),
        category,
        amount,
        description,
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")


# ── Read expenses for current month ───────────────────────────────────────────

def get_monthly_expenses(user_id: str) -> List[Dict]:
    """
    Returns all expense rows for `user_id` in the current calendar month.
    Each dict has: date, category, amount, description.
    """
    sheet = _get_sheet(EXPENSES_SHEET)
    records = sheet.get_all_records()   # list of dicts keyed by header row

    current_month = datetime.utcnow().strftime("%Y-%m")
    user_expenses = []

    for row in records:
        if str(row.get("UserID")) != user_id:
            continue
        row_date = str(row.get("Date", ""))
        if not row_date.startswith(current_month):
            continue
        user_expenses.append({
            "date":        row_date,
            "category":    row.get("Category", "Other"),
            "amount":      float(row.get("Amount", 0)),
            "description": row.get("Description", ""),
        })

    return user_expenses


def get_spending_by_category(user_id: str) -> Dict[str, float]:
    """Aggregates monthly expenses into {category: total_spent}."""
    expenses = get_monthly_expenses(user_id)
    totals: Dict[str, float] = {}
    for e in expenses:
        cat = e["category"]
        totals[cat] = totals.get(cat, 0.0) + e["amount"]
    return totals


# ── Read budgets ───────────────────────────────────────────────────────────────

def get_budgets(user_id: str) -> Dict[str, float]:
    """
    Reads per-user monthly budget limits from the Budget sheet.
    Falls back to DEFAULT_BUDGETS if the sheet has no row for that user.
    Budget sheet columns: UserID | Category | Limit
    """
    try:
        sheet = _get_sheet(BUDGET_SHEET)
        records = sheet.get_all_records()
        budgets = dict(DEFAULT_BUDGETS)  # start with defaults
        for row in records:
            if str(row.get("UserID")) == user_id:
                cat = row.get("Category")
                limit = row.get("Limit")
                if cat and limit:
                    budgets[cat] = float(limit)
        return budgets
    except Exception:
        return dict(DEFAULT_BUDGETS)
