"""Print the access audit trail, one line per call.

A refused call has no role (it was refused before a role was chosen), so its
line shows the refusal code instead.
"""

import json
import sys

for line in open(sys.argv[1], encoding="utf-8"):
    entry = json.loads(line)
    who = f"role={entry['role']}" if entry.get("role") else f"code={entry.get('code')}"
    print(
        f"{entry['status']:6} token={entry.get('token')} {who} sql={entry.get('sql')!r}"
    )
