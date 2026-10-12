import sys
from datetime import date

from .expand import occurrences
from .rule import parse_rrule

for d in occurrences(parse_rrule(sys.argv[1]), date.fromisoformat(sys.argv[2])):
    print(d.isoformat())
