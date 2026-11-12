"""A person's decision on an ambiguous suggestion: point accounts.company_id at
crm.companies (the current table), not crm.company (the legacy copy).

The decision goes into draft/relationships.yml, not relationships.yml. It then
takes effect when both models have been applied, the same way inferred
relationships do. Writing it to relationships.yml early would make every apply
fail until both models exist.

Usage: python declare_relationship.py <project_dir>
"""

import sys
from pathlib import Path

import yaml

project = Path(sys.argv[1])
path = project / "draft" / "relationships.yml"
path.parent.mkdir(parents=True, exist_ok=True)
doc = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
rels = (doc or {}).get("relationships") or []
rels.append({
    "name": "accounts_companies_company_id",
    "models": ["accounts", "companies"],
    "join_type": "many_to_one",
    "condition": "accounts.company_id = companies.company_id",
})
path.write_text(yaml.safe_dump({"relationships": rels}, sort_keys=False), encoding="utf-8")
print("recorded accounts.company_id -> companies.company_id in draft/relationships.yml")
