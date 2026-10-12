from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Transaction:
    date: date
    payee: str
    amount: float
    category: str = "uncategorized"
