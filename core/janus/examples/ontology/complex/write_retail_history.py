"""Write eight confirmed NL->SQL pairs to knowledge/sql/ (the demo's history)."""

import sys
from pathlib import Path

from janus.memory.markdown import write_query_markdown

project = Path(sys.argv[1])
pairs = [
    ("net revenue", "SELECT SUM(net_amount) FROM sales.fact_sales"),
    ("net revenue by category",
     "SELECT p.category, SUM(f.net_amount) FROM fact_sales f JOIN dim_product p "
     "ON f.product_key = p.product_key GROUP BY p.category"),
    ("net revenue by region",
     "SELECT s.region_code, SUM(f.net_amount) FROM fact_sales f JOIN dim_store s "
     "ON f.store_key = s.store_key GROUP BY s.region_code"),
    ("discounted sales", "SELECT COUNT(*) FROM fact_sales WHERE discount_pct > 0"),
    ("enterprise revenue",
     "SELECT SUM(f.net_amount) FROM fact_sales f JOIN dim_customer c "
     "ON f.customer_key = c.customer_key WHERE c.segment = 'Enterprise'"),
    ("lighting units",
     "SELECT SUM(qty) FROM fact_sales f JOIN dim_product p ON f.product_key = p.product_key "
     "WHERE p.category = 'Lighting'"),
    ("revenue in march", "SELECT SUM(net_amount) FROM fact_sales WHERE date_key = 20250301"),
    ("units per product", "SELECT product_key, SUM(qty) FROM fact_sales GROUP BY product_key"),
]
for nl, sql in pairs:
    write_query_markdown(project, nl, sql)
print(f"wrote {len(pairs)} confirmed queries")
