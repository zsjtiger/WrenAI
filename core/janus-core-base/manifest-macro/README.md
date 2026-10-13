# Janus Core Manifest Macro
🌐 **English** · [简体中文](./README.zh-CN.md)
This is module to collect the generating macros for the manifest struct of Janus MDL.
They are used to generate the manifest struct for different bindings.
Currently, we have the following bindings:
- Python
- Rust

## Example
```rust
use janus_core_manifest_macro::manifest;

manifest!(true); // Generate the manifest struct for Python binding 
manifest!(false); // Generate the manifest struct for Rust binding
```