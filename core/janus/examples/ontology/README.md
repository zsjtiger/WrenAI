# Ontology demos

A runnable walk through the ontology operations, on a small DuckDB warehouse
that is generated locally. Nothing here needs a network, a database server, or
a model key.

```bash
./run_demo.sh                                    # with `janus` on PATH
JANUS="python -m janus.cli" PYTHON=python ./run_demo.sh   # from a source checkout
```

Everything is written under `work/` (git-ignored): the project, a connection
profile, and the warehouse. The script starts from a clean `work/` each run.

## The warehouse

| Table | What the demo shows |
|---|---|
| `customers`, `regions`, `dim_products`, `orders`, `order_items` | Ordinary tables. **No foreign keys are declared**, so the relationships have to be inferred. `dim_products` shows term naming: the `dim_` prefix is dropped. |
| `customer_regions` | A **pure bridge table**: both columns are keys and nothing else is stored. |

## The steps

| Step | Command | What to look for |
|---|---|---|
| 3. Draft | `context draft --from-db` | One draft per unmodeled table, under `draft/`. Composite keys are noted, because MDL keys are single columns. |
| 4. Infer keys | `context infer-fks` | `customer_regions` and `order_items` get foreign keys. `orders.cust_id` scores 0.5, a partial match on `customers`. The bridge is detected. |
| 5. Terms | `context terms` | `customer_regions` becomes "Customer Region"; `dim_products` becomes "Product" (alias "Dim Products"). |
| 6. Attributes | `write_history.py`, then `context attributes` | `sum(amount)` and `status = 'shipped'` appear in two confirmed queries and are kept. The query that appears once is dropped (`--min-occurrences 2`). |
| 7. Apply | `context draft apply` | Parents first. Each applied model carries its term and display names, and its relationships come with it. |
| 8. Check | `context build`, `validate`, `context diff` | `diff` reports no drift. Composite keys are listed as notes, not as drift. |
| 9. Query | `janus --sql` | Revenue per customer, through the joins that were inferred and applied. |
| 10. Certify | `governance_demo.py` | With `orders` uncertified, a query returns rows with a warning. With `require_certified` on, the same query is refused during planning. |
| 11. Review | `review_demo.py`, `context review approve` | An agent-style correction is queued, then approved. `orders` gets its new description after validation. |

## Files

- `make_warehouse.py`: creates the DuckDB warehouse.
- `write_history.py`: writes three confirmed NL→SQL pairs to `knowledge/sql/`.
- `governance_demo.py`: certification, provenance, and `require_certified`, through the engine API.
- `review_demo.py`: queues a correction the way an agent would.
- `run_demo.sh`: runs the steps in order.
