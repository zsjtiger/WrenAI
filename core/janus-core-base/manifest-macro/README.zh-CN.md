# Janus Core Manifest Macro
🌐 [English](./README.md) · **简体中文**

本模块收录了用于生成 Janus MDL manifest 结构体的宏。这些宏用于为不同的绑定生成 manifest 结构体。
目前支持以下绑定：
- Python
- Rust

## 示例
```rust
use janus_core_manifest_macro::manifest;

manifest!(true); // Generate the manifest struct for Python binding 
manifest!(false); // Generate the manifest struct for Rust binding
```
