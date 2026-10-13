# janus-core-wasm

🌐 [English](./README.md) · **简体中文**

基于 [Apache DataFusion](https://datafusion.apache.org/) 编译为 WebAssembly 的浏览器原生语义 SQL 引擎。

无需服务器，即可通过语义层（MDL）直接在浏览器中查询 Parquet 文件。

## 安装

```bash
npm install @janusai/janus-core-wasm
```

或通过 CDN 直接使用：

```html
<script type="module">
  import { JanusEngine } from 'https://unpkg.com/@janusai/janus-core-wasm@0.3.0/dist/index.js';
</script>
```

> **注意：** 请使用 **unpkg**，而不是 jsDelivr。jsDelivr 免费 CDN 对单个文件有 50 MB 的限制，而 WASM 二进制文件原始大小约为 68 MB。

## 快速开始

### 内联模式（推荐用于本地开发和打包的仪表盘）

直接从 JavaScript 注册数据——无需服务器，也没有 Range/CORS 相关的陷阱。对于数据总量在约 50 MB 以下的情况，这是最省事的方式。

```javascript
import { JanusEngine } from '@janusai/janus-core-wasm';

const engine = await JanusEngine.init();

// 将 JSON 数据注册为表
await engine.registerJson('orders', [
  { id: 1, customer: 'Alice', amount: 100 },
  { id: 2, customer: 'Alice', amount: 250 },
  { id: 3, customer: 'Bob',   amount: 120 },
]);

// 或从 ArrayBuffer 注册 Parquet
const response = await fetch('orders.parquet');
await engine.registerParquet('orders', await response.arrayBuffer());

// 或注册 CSV——字符串或字节，可选 schema / 分隔符 / 引号
await engine.registerCsv('orders', 'id,customer,amount\n1,Alice,100\n2,Bob,200');

const mdl = {
  catalog: 'janus',
  schema: 'public',
  models: [
    {
      name: 'Orders',
      tableReference: { table: 'orders' },
      columns: [
        { name: 'id', type: 'INTEGER' },
        { name: 'customer', type: 'VARCHAR' },
        { name: 'amount', type: 'DOUBLE' },
      ],
      primaryKey: 'id',
    },
  ],
  relationships: [],
  views: [],
};

// 使用空 source 加载 MDL（使用预先注册的表）
await engine.loadMDL(mdl, { source: '' });

const rows = await engine.query('SELECT * FROM "Orders" LIMIT 10');
```

### URL 模式（远程 Parquet，适用于数据量大或已部署在 CDN 上的情况）

数据位于 HTTP 服务器上。DataFusion 通过 **HTTP 范围请求**读取每个 Parquet 文件（先读文件尾，再读行组）。服务器**必须支持 `Range:` 请求头**——参见下方的[选择本地开发服务器](#choosing-a-local-dev-server)；否则请优先使用内联模式。

```javascript
await engine.loadMDL(mdl, { source: 'https://your-cdn.com/data/' });

const rows = await engine.query('SELECT customer, sum(amount) AS total FROM "Orders" GROUP BY customer');
console.table(rows);
// [{ customer: 'Alice', total: 350 }, { customer: 'Bob', total: 120 }]
```

### Node.js 用法

`JanusEngine.init()` 默认通过 `import.meta.url` 获取 WASM 二进制文件，在 Node 中该 URL 会解析为 `file://` 地址。Node 的 `undici` fetch 不支持 `file://`，因此 `init()` 会抛出异常。请以 `BufferSource` 的形式直接传入二进制文件：

```javascript
import { readFileSync } from 'node:fs';
import { JanusEngine } from '@janusai/janus-core-wasm';

const buf = readFileSync(
  'node_modules/@janusai/janus-core-wasm/dist/janus_core_wasm_bg.wasm'
);
const engine = await JanusEngine.init({
  wasmUrl: buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
});
```

适用于单元测试、CI 冒烟检查以及任何非浏览器环境（`node --test`）。

## 选择本地开发服务器

URL 模式使用 DataFusion 的 `ListingTable`，它通过 HTTP 范围请求读取 Parquet。如果开发服务器不支持 `Range:` 请求头，请求会在读取文件尾之后静默挂起。

| 服务器 | Range 支持 | 说明 |
|---|---|---|
| `python -m http.server` | ❌ 不支持 | 内置服务器——URL 模式请避免使用 |
| `python -m RangeHTTPServer` | ✅ 支持 | `pip install rangehttpserver` |
| `npx serve` | ⚠️ 仅单段范围 | 基于 `sirv` 构建；对超出文件末尾的范围可能返回 `416` |
| `npx http-server` | ✅ 支持 | 默认启用 CORS |
| `caddy file-server` | ✅ 支持 | 可用于生产环境 |
| Vite | ⚠️ 仅单段范围 | 同样基于 `sirv`；存在与 `npx serve` 相同的 `416` 边界情况 |
| `webpack-dev-server` | ⚠️ 仅单段范围 | 多段范围请求会退回为返回整个资源 |

**快速检查：** `curl -I -H "Range: bytes=0-1023" http://localhost:PORT/file.parquet` 应返回 `HTTP/1.1 206 Partial Content`（而不是 `200`）。

如果你只能使用不支持范围请求的服务器，请改用**内联模式**——用 `fetch()` 获取每个文件一次，然后通过 `registerParquet` 注册。

## 示例

`examples/` 目录提供了可直接运行的浏览器演示。它们从 `pkg/` 导入本地 WASM 构建，因此始终反映当前源码——在迭代 Rust 或 TypeScript 代码时非常有用。

```bash
# 构建 WASM 二进制文件（示例使用 debug 构建即可）
just build-wasm-dev

# 启动带 CORS + Range 支持的静态开发服务器
just serve
```

服务器启动时会打印每个演示的 URL。在浏览器中打开任意一个即可：

| 演示 | URL | 展示内容 |
|---|---|---|
| 内联数据 | http://localhost:8787/examples/inline.html | `registerJson` + 原始 SQL `query()` |
| URL 模式 | http://localhost:8787/examples/url-mode.html | 通过 HTTP 范围请求读取远程 Parquet |
| CDN 冒烟测试 | http://localhost:8787/examples/test-cdn.html | 从 unpkg 加载已发布的包 |
| **Cube 快速入门** | http://localhost:8787/examples/cube-quickstart.html | 最简 `cubeQuery()`——三个预设查询（分组、过滤、时间分桶） |
| **Cube 浏览器** | http://localhost:8787/examples/cube-explorer.html | `CubeQuery` 的表单式构建器——选择度量/维度、添加过滤器、选择粒度和日期范围 |
| **CSV 快速入门** | http://localhost:8787/examples/csv-quickstart.html | 针对 `data/` 中真实文件的 `registerCsv()`——推断 schema、自定义分隔符（TSV），以及带显式 schema 的无表头 CSV |

### Cube 快速入门 vs 浏览器

- **快速入门** 加载单个 `order_metrics` cube，点击按钮时触发硬编码的 `cubeQuery()` 调用。阅读源码即可看到最小的端到端 cube 示例。
- **浏览器** 是交互式的：复选框/下拉框表单会实时生成 `CubeQuery` JSON（显示在结果旁边），你可以添加任意数量的过滤器，支持全部 12 个 `FilterOperator` 值。演示数据分布在不同地区/客户/月份之间，因此分组结果具有实际意义。

修改 Rust 代码后，请重新运行 `just build-wasm-dev` 并刷新页面——示例直接从 `pkg/janus_core_wasm.js` 导入。

## API 参考

### `JanusEngine.init(options?)`

初始化引擎并加载 WASM 二进制文件。

```typescript
static async init(options?: JanusEngineOptions): Promise<JanusEngine>
```

| 选项 | 类型 | 说明 |
|--------|------|-------------|
| `wasmUrl` | `string \| URL \| BufferSource` | WASM 二进制文件来源。默认通过 `import.meta.url` 指向同级的 `janus_core_wasm_bg.wasm`。 |

### `engine.loadMDL(mdl, profile)`

加载 MDL 清单以启用语义层查询改写。

```typescript
async loadMDL(mdl: object, profile: JanusProfile): Promise<void>
```

| 参数 | 类型 | 说明 |
|-----------|------|-------------|
| `mdl` | `object` | MDL 清单（将被 JSON 序列化） |
| `profile.source` | `string` | URL 模式为 `"https://..."`，预注册表为 `""` |

### `engine.registerParquet(name, data)`

将 Parquet 文件注册为命名表。内联模式下请在 `loadMDL` 之前调用。

```typescript
async registerParquet(name: string, data: ArrayBuffer): Promise<void>
```

### `engine.registerJson(name, data)`

将 JSON 数据注册为命名表。内联模式下请在 `loadMDL` 之前调用。

```typescript
async registerJson(name: string, data: object[]): Promise<void>
```

### `engine.registerCsv(name, data, options?)`

将 CSV 数据注册为命名表。接受字符串（按 UTF-8 处理）或任意 `BufferSource`（ArrayBuffer / TypedArray / Node Buffer）。默认第一行为表头，并根据前 1000 行推断 schema。

```typescript
async registerCsv(
  name: string,
  data: string | BufferSource,
  options?: CsvReadOptions,
): Promise<void>
```

| 选项（camelCase） | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `header` | `boolean` | `true` | 第一行为表头。 |
| `delimiter` | `string` | `","` | 字段分隔符（单个 ASCII 字符）。 |
| `quote` | `string` | `"\""` | 引号字符（单个 ASCII 字符）。 |
| `escape` | `string` | 未设置 | 转义字符（单个 ASCII 字符）。 |
| `terminator` | `string` | `\n`、`\r\n` 中的任意一个 | 记录终止符（单个 ASCII 字符）。 |
| `batchSize` | `number` | `8192` | RecordBatch 大小。 |
| `inferRows` | `number` | `1000` | 用于推断的扫描行数。设置 `schema` 时忽略。 |
| `schema` | `CsvSchemaColumn[]` | 推断 | 显式 Arrow schema `{ name, type, nullable? }[]`。 |

Schema 列类型（不区分大小写）：`int8`/`int16`/`int32`/`int64`、`uint8`/`uint16`/`uint32`/`uint64`、`float32`/`float64`、`boolean`、`string`（别名 `utf8`/`varchar`/`text`）、`date`/`date32`/`date64`、`timestamp` 以及 `timestamp_{s,ms,us,ns}`。

### `engine.query(sql)`

通过语义层执行 SQL 查询。返回解析后的结果对象。

```typescript
async query(sql: string): Promise<Record<string, unknown>[]>
```

### `engine.free()`

释放 WASM 内存。引擎不再需要时调用。

## 从源码构建

前置条件：Rust 工具链、`wasm-pack`、Node.js 16+。

```bash
cd janus-core-wasm

# 安装 TypeScript 开发依赖
npm install

# 构建 WASM 二进制文件（需要 wasm32-unknown-unknown 目标）
wasm-pack build --target web --release

# 构建 TypeScript 封装并组装 dist/
npm run build:dist

# 运行集成测试
npm test

# 仅进行类型检查
npm run typecheck
```

### macOS 注意事项

在 macOS 上，WASM 构建可能需要 LLVM 来编译 C 依赖：

```bash
brew install llvm

CC_wasm32_unknown_unknown=/opt/homebrew/opt/llvm/bin/clang \
AR_wasm32_unknown_unknown=/opt/homebrew/opt/llvm/bin/llvm-ar \
CFLAGS_wasm32_unknown_unknown="--target=wasm32-unknown-unknown" \
wasm-pack build --target web --release
```

## 注意事项

- `query()` 返回 `Record<string, unknown>[]`——可直接用于 Chart.js、D3、Recharts 等。
- MDL 的 `tableReference` 使用裸表名（例如 `"orders"`），而不是完整 URL。
- 本地开发数据量在约 50 MB 以下时，建议优先使用**内联模式**——它可以消除 HTTP Range/CORS 类问题。
- URL 模式要求 HTTP 服务器同时支持 CORS **和**范围请求（参见[选择本地开发服务器](#choosing-a-local-dev-server)）。
- 在 Node 中，请向 `JanusEngine.init()` 传入 `wasmUrl: BufferSource`——Node 的 fetch 无法加载 `file://` URL。
- WASM 二进制文件原始大小约 68 MB，gzip 压缩后约 14 MB。

