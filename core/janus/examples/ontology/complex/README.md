# Complex ontology demo

A larger, messier version of the [basic demo](../README.md): a retail star schema
across two schemas, built to meet the problems a real warehouse has.

```bash
./run_complex_demo.sh
JANUS="python -m janus.cli" PYTHON=python ./run_complex_demo.sh   # from a source checkout
```

No network, server, or model key is needed. Output goes to `work/` (git-ignored).

## The warehouse

| Schema | Tables | What it tests |
|---|---|---|
| `sales` | `fact_sales`, `dim_date`, `dim_store`, `dim_product`, `dim_customer`, `dim_promo` | A star schema. The `dim_` prefix means foreign-key matching has to look past it (`store_key` -> `dim_store`). |
| `sales` | `bridge_promo_product` | A pure bridge: promotions and products, both keys, nothing else. |
| `crm` | `accounts`, `companies`, `company` | `company` is a legacy copy of `companies`. `accounts.company_id` could point at either, so the suggestion is ambiguous. |

Cross-schema references are inferred too: `sales.dim_customer.account_id`
points at `crm.accounts`. No foreign key is declared anywhere.

## The steps

| Step | What it shows |
|---|---|
| 3. Draft | Drafts per schema, with composite keys noted (MDL keys are single columns). |
| 4. Infer keys | Prefixed names match. The bridge is detected. `accounts.company_id` is **ambiguous**, with both candidates listed. |
| 5. Terms and attributes | Eight confirmed queries. `sum(f.net_amount)` and `sum(net_amount)` count as one measure. |
| 6. Human decision | A person picks `companies`, not the legacy copy. The decision goes into `draft/relationships.yml`, so it waits for both models to exist. |
| 7. Promote | The drafts are promoted in an order that does not matter. The relationship lands once both ends exist. |
| 8. Diff | Each schema is checked against the warehouse: no drift. The composite key is noted, not compared. |
| 9. Query | Semantic-layer queries over the star and over the bridge. These use MDL model names, not physical schema names. |
| 10. Certify | `fact_sales`, `dim_product`, and `dim_store` are certified. A multi-hop query warns about the uncertified models it reads. With `require_certified`, the same query is refused at planning time, and the message names the model. |
| 11. Review | Three agent proposals: one is queued and approved, one is refused because it touches `table_reference`, and one is queued and rejected with a reason. |
| 12. Rollback | A draft that fails validation (`certified: "maybe"`) is refused, and `models/` is unchanged. |

## Files

- `make_retail_warehouse.py`: builds the two-schema DuckDB warehouse.
- `write_retail_history.py`: writes eight confirmed NL→SQL pairs.
- `declare_relationship.py`: records the human decision on the ambiguous key.
- `certify_and_query.py`: certification, provenance, and `require_certified` through the engine API.
- `corrections_demo.py`: queues three agent proposals.
- `failed_apply.py`: stages a draft that fails validation.
- `run_complex_demo.sh`: runs the steps in order.

## Problems this demo found, and what changed

Running the demo found these, and each was fixed in the code, with a test:

- **Prefixed names were not matched.** `store_key` did not find `dim_store`. Matching now ignores warehouse prefixes, as term naming already did.
- **A model's own key was suggested as a foreign key.** `companies.company_id` pointed at `company`, because both tables use the same key name. A model's own single primary key is no longer suggested.
- **Attributes split one measure in two.** `sum(f.net_amount)` and `sum(net_amount)` are now the same expression.
- **A human decision broke every other apply.** Recording it in `relationships.yml` before both models existed made validation fail. It now goes to `draft/relationships.yml`.
