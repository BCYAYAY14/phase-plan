import csv
import io
from datetime import date

from .model import Transaction


def parse_csv(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    out = []
    for row in rows:
        out.append(Transaction(
            date=date.fromisoformat(row["date"].strip()),
            payee=row["payee"].strip(),
            amount=float(row["amount"]),
            category=(row.get("category") or "uncategorized").strip().lower(),
        ))
    return out
