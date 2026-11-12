"""Queue three agent proposals: one good, one that touches a protected field,
and one on an uncertified model. Prints the ids of the queued ones.

Usage: python corrections_demo.py <project_dir>
"""

import sys
from pathlib import Path

from janus.context_corrections import propose_correction

project = Path(sys.argv[1])
ids = []
for model, problem, change in [
    ("dim_product", "unit_cost is internal; reports should show list price",
     "description: Product catalogue with list prices"),
    ("accounts", "the agent wants to repoint the table",
     "table_reference:\n  schema: crm\n  table: accounts_v2"),
    ("dim_customer", "segment labels are inconsistent across regions",
     "description: Customer with a normalised segment"),
]:
    try:
        cid = propose_correction(project, model=model, problem=problem,
                                 proposed_change=change)
        ids.append(cid)
        print(f"queued {cid} for {model}")
    except ValueError as exc:
        print(f"refused for {model}: {exc}")
print("IDS " + " ".join(ids))
