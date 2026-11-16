"""Create the demo warehouse: a DuckDB file with two small tables.

    python make_warehouse.py <path/to/warehouse.duckdb>
"""

import sys
from pathlib import Path

import duckdb

target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("warehouse.duckdb")
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists():
    target.unlink()

con = duckdb.connect(str(target))
con.execute(
    """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name VARCHAR,
        region VARCHAR
    )
    """
)
con.execute(
    """
    INSERT INTO customers VALUES
        (1, 'Ada', 'APAC'),
        (2, 'Ben', 'EU'),
        (3, 'Chen', 'APAC'),
        (4, 'Dana', 'US')
    """
)
con.execute(
    """
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        amount DECIMAL(10, 2),
        status VARCHAR
    )
    """
)
con.execute(
    """
    INSERT INTO orders VALUES
        (101, 1, 120.00, 'shipped'),
        (102, 1,  35.50, 'shipped'),
        (103, 2, 480.00, 'pending'),
        (104, 3,  75.25, 'shipped'),
        (105, 4, 210.00, 'cancelled'),
        (106, 2,  18.90, 'shipped')
    """
)
con.close()
print(f"wrote {target}")
