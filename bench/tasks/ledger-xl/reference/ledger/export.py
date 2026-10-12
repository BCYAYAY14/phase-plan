import csv
import io


def to_csv(txns) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["date", "payee", "amount", "category"])
    for t in txns:
        writer.writerow([t.date.isoformat(), t.payee, str(t.amount), t.category])
    return buf.getvalue()
