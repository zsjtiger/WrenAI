"""Add the access rules to the generated orders model.

The rules are data-team work, so they live in the model YAML:
- amount is visible only when session_level is at least 2 (a column rule);
- a row is visible when customer_id matches session_customer, or the caller's
  session_level is 3 or more (a row rule).

    python add_rules.py <project>/models/orders/metadata.yml
"""

import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
model = yaml.safe_load(path.read_text(encoding="utf-8"))
for column in model["columns"]:
    if column["name"] == "amount":
        column["column_level_access_control"] = {
            "name": "amount_for_managers",
            "required_properties": [{"name": "session_level", "required": True}],
            "operator": "GREATER_THAN_OR_EQUALS",
            "threshold": "2",
        }
model["row_level_access_controls"] = [
    {
        "name": "own_or_manager",
        "required_properties": [
            {"name": "session_customer", "required": True},
            {"name": "session_level", "required": True},
        ],
        "condition": "customer_id = @session_customer OR @session_level >= 3",
    }
]
path.write_text(
    yaml.safe_dump(model, sort_keys=False, allow_unicode=True), encoding="utf-8"
)
print(f"added access rules to {path}")
