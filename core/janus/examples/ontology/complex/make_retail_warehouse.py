"""Create a retail star schema across two schemas: sales and crm.

What makes it realistic, and what the demo exercises:
  * dimension tables named with a warehouse prefix (dim_store, dim_product, ...)
  * no declared foreign keys anywhere
  * a cross-schema reference: sales.dim_customer.account_id -> crm.accounts
  * a legacy duplicate: crm.company and crm.companies both have company_id, so
    crm.accounts.company_id is genuinely ambiguous
  * a pure bridge table: sales.bridge_promo_product links promotions and products
"""

import sys
from pathlib import Path

import duckdb

target = Path(sys.argv[1])
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists():
    target.unlink()

conn = duckdb.connect(str(target))
conn.execute("CREATE SCHEMA sales; CREATE SCHEMA crm;")
conn.execute("""
CREATE TABLE sales.dim_date (date_key INTEGER PRIMARY KEY, full_date DATE,
                             year INTEGER, month INTEGER);
CREATE TABLE sales.dim_store (store_key INTEGER PRIMARY KEY, store_name VARCHAR,
                              region_code VARCHAR);
CREATE TABLE sales.dim_product (product_key INTEGER PRIMARY KEY, sku VARCHAR,
                                product_name VARCHAR, category VARCHAR,
                                unit_cost DECIMAL(10, 2));
CREATE TABLE sales.dim_customer (customer_key INTEGER PRIMARY KEY, account_id INTEGER,
                                 full_name VARCHAR, segment VARCHAR);
CREATE TABLE sales.dim_promo (promo_id INTEGER PRIMARY KEY, promo_name VARCHAR);
CREATE TABLE sales.bridge_promo_product (promo_id INTEGER, product_key INTEGER,
                                         PRIMARY KEY (promo_id, product_key));
CREATE TABLE sales.fact_sales (sale_id INTEGER PRIMARY KEY, date_key INTEGER,
                               store_key INTEGER, product_key INTEGER,
                               customer_key INTEGER, qty INTEGER,
                               net_amount DECIMAL(12, 2), discount_pct DECIMAL(5, 2));
CREATE TABLE crm.companies (company_id INTEGER PRIMARY KEY, company_name VARCHAR);
CREATE TABLE crm.company (company_id INTEGER PRIMARY KEY, company_name VARCHAR);
CREATE TABLE crm.accounts (id INTEGER PRIMARY KEY, name VARCHAR,
                           company_id INTEGER, owner_employee_id INTEGER);

INSERT INTO sales.dim_date VALUES (20250101, DATE '2025-01-01', 2025, 1),
                                  (20250201, DATE '2025-02-01', 2025, 2);
INSERT INTO sales.dim_store VALUES (1, 'Berlin Mitte', 'DE'), (2, 'Lyon Centre', 'FR'),
                                   (3, 'Austin Downtown', 'US');
INSERT INTO sales.dim_product VALUES
  (10, 'LMP-01', 'Desk lamp', 'Lighting', 9.50),
  (11, 'DSK-02', 'Standing desk', 'Furniture', 260.00),
  (12, 'CHR-03', 'Office chair', 'Furniture', 140.00),
  (13, 'LMP-04', 'Floor lamp', 'Lighting', 35.00);
INSERT INTO crm.companies VALUES (100, 'Northwind GmbH'), (200, 'Contoso SAS');
INSERT INTO crm.company VALUES (100, 'Northwind GmbH (legacy)'), (200, 'Contoso SAS (legacy)');
INSERT INTO crm.accounts VALUES (500, 'Northwind Berlin', 100, 7),
                                (501, 'Contoso Lyon', 200, 8),
                                (502, 'Northwind Austin', 100, 7);
INSERT INTO sales.dim_customer VALUES (1, 500, 'Ada Lovelace', 'Enterprise'),
                                      (2, 501, 'Gustave Eiffel', 'SMB'),
                                      (3, 502, 'Grace Hopper', 'Enterprise');
INSERT INTO sales.dim_promo VALUES (1, 'Spring lighting week'), (2, 'Back to office');
INSERT INTO sales.bridge_promo_product VALUES (1, 10), (1, 13), (2, 11), (2, 12);
INSERT INTO sales.fact_sales VALUES
  (1, 20250101, 1, 10, 1, 2, 19.00, 0.00),
  (2, 20250101, 2, 11, 2, 1, 260.00, 10.00),
  (3, 20250201, 3, 12, 3, 1, 140.00, 0.00),
  (4, 20250201, 1, 13, 1, 3, 105.00, 15.00),
  (5, 20250201, 2, 10, 2, 4, 38.00, 0.00);
""")
conn.close()
print("wrote", target)
