"""Create the demo warehouse: warehouse.duckdb in this directory.

Tables are deliberately left without declared foreign keys, so the demo can
show janus inferring them. customer_regions is a pure bridge table.
"""

import sys
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
target = HERE / "warehouse.duckdb"
if len(sys.argv) > 1:
    target = Path(sys.argv[1])
if target.exists():
    target.unlink()

conn = duckdb.connect(str(target))
conn.execute("""
CREATE TABLE customers (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, region_name VARCHAR);
CREATE TABLE regions (region_id INTEGER PRIMARY KEY, label VARCHAR);
CREATE TABLE customer_regions (customer_id INTEGER, region_id INTEGER,
                               PRIMARY KEY (customer_id, region_id));
CREATE TABLE dim_products (product_id INTEGER PRIMARY KEY, title VARCHAR,
                           unit_price DECIMAL(10, 2));
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, cust_id INTEGER,
                     amount DECIMAL(10, 2), status VARCHAR);
CREATE TABLE order_items (order_id INTEGER, product_id INTEGER, quantity INTEGER,
                          PRIMARY KEY (order_id, product_id));

INSERT INTO customers VALUES (1, 'Ada', 'EU'), (2, 'Grace', 'US'), (3, 'Linus', 'EU');
INSERT INTO regions VALUES (10, 'Europe'), (20, 'North America');
INSERT INTO customer_regions VALUES (1, 10), (2, 20), (3, 10);
INSERT INTO dim_products VALUES (100, 'Desk lamp', 19.90), (101, 'Standing desk', 449.00);
INSERT INTO orders VALUES (1000, 1, 19.90, 'shipped'), (1001, 2, 449.00, 'shipped'),
                          (1002, 3, 449.00, 'open'), (1003, 1, 19.90, 'shipped');
INSERT INTO order_items VALUES (1000, 100, 1), (1001, 101, 1), (1002, 101, 1), (1003, 100, 2);
""")
conn.close()
print("wrote", target)
