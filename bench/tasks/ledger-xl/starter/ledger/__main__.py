import sys

from .parse import parse_csv
from .reports import balance

with open(sys.argv[1]) as f:
    print(f"Balance: {balance(parse_csv(f.read()))}")
