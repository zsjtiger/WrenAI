# janus-core-base

Shared Rust crate with manifest types used by both janus-core and janus-core-py. Defines the MDL (Modeling Definition Language) data model.

## Key Types (`src/mdl/`)

- `manifest.rs` — `Manifest`, `Model`, `Column`, `Metric`, `Relationship`, `View`, `RowLevelAccessControl`, `ColumnLevelAccessControl`
- `builder.rs` — Fluent `ManifestBuilder` API for constructing manifests in tests and tools

## Features

| Feature | Description |
|---|---|
| `default` | No optional features |
| `python-binding` | Enables PyO3 derive macros via `janus-manifest-macro` for auto-generating Pydantic-compatible Python classes |

## Dependencies

- `janus-manifest-macro` (path: `manifest-macro/`) — Proc macro crate for auto-generating Python bindings
- `sqlparser` — SQL type parsing
- `pyo3` (optional) — Python FFI

## Dev Commands

```bash
cargo check                    # Compile check
cargo test                     # Run tests
cargo fmt                      # Format
cargo clippy -- -D warnings    # Lint
taplo fmt                      # Format Cargo.toml
```

## Conventions

- Any change to manifest types affects both Rust (janus-core) and Python (janus-core-py) consumers
- When adding fields, ensure `serde` defaults are set for backward compatibility
- The `python-binding` feature must remain optional — janus-core does not need it
