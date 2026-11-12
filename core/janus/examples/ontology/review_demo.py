"""Queue a correction the way an agent would. Prints the correction id last.

Usage: python review_demo.py <project_dir>
"""

import sys
from pathlib import Path

from janus.context_corrections import propose_correction

project = Path(sys.argv[1])
cid = propose_correction(
    project,
    model="orders",
    problem="amount is the gross value; reports need the net value",
    proposed_change="description: Order amount, as invoiced",
)
print(f"queued correction {cid}")
print(cid)
