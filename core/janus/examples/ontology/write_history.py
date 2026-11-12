"""Write confirmed NL->SQL pairs to knowledge/sql/ (the demo's query history)."""

import sys
from pathlib import Path

from janus.memory.markdown import write_query_markdown

project = Path(sys.argv[1])
pairs = [
    ("shipped revenue", "SELECT SUM(amount) FROM orders WHERE status = 'shipped'"),
    ("shipped revenue by customer",
     "SELECT cust_id, SUM(amount) FROM orders WHERE status = 'shipped' GROUP BY cust_id"),
    ("orders per status", "SELECT status, COUNT(*) FROM orders GROUP BY status"),
]
for nl, sql in pairs:
    write_query_markdown(project, nl, sql)
print(f"wrote {len(pairs)} confirmed queries to {project / 'knowledge' / 'sql'}")
