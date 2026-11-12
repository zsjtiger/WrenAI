"""Stage a draft that will fail validation, so `draft apply` rolls it back.

The draft points at the same table as dim_store, with an invalid certification
value. Applying it must refuse and leave models/ and the draft unchanged.

Usage: python failed_apply.py <project_dir>
"""

import sys
from pathlib import Path

import yaml

project = Path(sys.argv[1])
meta = yaml.safe_load((project / "models" / "dim_store" / "metadata.yml").read_text(encoding="utf-8"))
meta["name"] = "dim_store_candidate"
meta["properties"] = {"draft": "true", "certified": "maybe"}
folder = project / "draft" / "models" / "dim_store_candidate"
folder.mkdir(parents=True, exist_ok=True)
(folder / "metadata.yml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
print("staged draft dim_store_candidate with certified: maybe")
