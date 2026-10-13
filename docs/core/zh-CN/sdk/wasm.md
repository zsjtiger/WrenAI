# janus-core-wasm

浏览器原生的语义 SQL 引擎。Rust 实现的 janus-core 引擎被编译为 WebAssembly，并配有一个 TypeScript SDK，可在浏览器中完全通过 MDL 语义层运行查询，无需服务器，也没有往返请求。

**何时使用此 SDK**：当你要构建客户端分析界面、笔记本，或浏览器中的 LLM 应用，且数据位于静态 Parquet 文件中（或可以内联为 JSON/CSV），并希望智能体基于 MDL 模型编写 SQL 时。对于服务端 Python 智能体，请改用 [`janus-langchain`](./langchain.md) 或 [`janus-pydantic`](./pydantic.md)。它们封装的是同一个引擎，但连接的是你真实的数据库。

---

## 与其他 SDK 的区别

| | `janus-core-wasm` | `janus-langchain` / `janus-pydantic` |
|---|---|---|
| **运行时** | 浏览器（WebAssembly） | Python 服务器 |
| **数据源** | 远程 Parquet、内联 JSON/CSV，或上传的文件 | CLI 支持的任意数据源（Postgres、BigQuery 等） |
| **连接 profile** | 无；数据在客户端获取或注册 | 必需（通过 `janus profile add` 创建） |
| **MDL 来源** | 每次页面加载时以 JS 对象形式传入 | 每次工具调用时从 `target/mdl.json` 读取 |
| **记忆 / 智能体工具** | 不包含在 WASM SDK 中 | 内置工具（`janus_query`、`janus_recall_queries` 等） |
| **查询路径** | DataFusion 在浏览器中执行 SQL | 引擎规划 SQL，目标数据库执行 |

这里没有 `JanusToolkit`。WASM SDK 暴露的是引擎原语（`registerJson` / `registerParquet` / `registerCsv` / `loadMDL` / `query` / `cubeQuery` / `listCubes`），由你将它们接入自己的界面或智能体循环。

---

## 安装

### npm

```bash
npm install @janusai/janus-core-wasm
```

```javascript
import { JanusEngine } from '@janusai/janus-core-wasm';
```

### CDN

```html
<script type="module">
  import { JanusEngine } from 'https://unpkg.com/@janusai/janus-core-wasm@0.3.0/dist/index.js';
</script>
```

> ⚠️ 请使用 **unpkg**，而不是 jsDelivr。jsDelivr 免费 CDN 对单个文件有 50 MB 的上限，而 WASM 二进制文件原始大小约为 72 MB。打包工具（Vite、Webpack、esbuild）则没有问题，参见[打包工具配置](#bundler-configuration)。

---

## 快速开始

同一个 `JanusEngine` 实例可以处理三种数据加载模式。请根据你的数据选择合适的模式：

### 1. URL 模式（远程 Parquet）

DataFusion 通过 HTTP 范围请求获取 Parquet 文件，无需注册。

```javascript
const engine = await JanusEngine.init();

const mdl = {
  catalog: 'janus',
  schema: 'public',
  models: [{
    name: 'Orders',
    tableReference: { table: 'orders' },     // resolves to {source}/orders.parquet
    columns: [
      { name: 'id', type: 'INTEGER' },
      { name: 'customer', type: 'VARCHAR' },
      { name: 'amount', type: 'DOUBLE' },
    ],
    primaryKey: 'id',
  }],
  relationships: [], views: [],
};

await engine.loadMDL(mdl, { source: 'https://cdn.example.com/data/' });

const rows = await engine.query(
  'SELECT customer, SUM(amount) AS total FROM "Orders" GROUP BY customer'
);
console.table(rows);
```

### 2. 内联数据（JSON / CSV / Parquet）

在调用 `loadMDL` 之前，先注册所有表。传入 `source: ''`，让引擎自动检测没有 URL 前缀需要处理，并直接使用已注册的表（完整的模式对照表参见 [`loadMDL`](#engineloadmdlmdl-profile)）。

```javascript
const engine = await JanusEngine.init();

// JSON
await engine.registerJson('orders', [
  { id: 1, customer: 'Alice', amount: 150 },
  { id: 2, customer: 'Bob',   amount: 250 },
]);

// CSV — string or Uint8Array; options object is optional
await engine.registerCsv('events', csvString, {
  header: true,
  delimiter: ',',
  // optional explicit Arrow schema; omit to infer
  schema: [
    { name: 'id', type: 'int64' },
    { name: 'event_type', type: 'string' },
  ],
});

// Parquet — BufferSource (ArrayBuffer / Uint8Array / Node Buffer)
const file = await fetch('orders.parquet').then(r => r.arrayBuffer());
await engine.registerParquet('orders_pq', file);

await engine.loadMDL(mdl, { source: '' });   // auto-detect; uses the registered tables
```

### 3. Cube 查询（结构化聚合）

当 MDL 中定义了 [Cube](../guides/cubes.md) 时，请优先使用 `cubeQuery`，而不是手写 `GROUP BY` SQL。引擎会根据 JSON 请求组装 `DATE_TRUNC`、过滤条件和投影，对于不需要关心 SQL 语法的智能体来说非常实用。

```javascript
await engine.loadMDL(mdlWithCubes, { source: '' });

const cubes = engine.listCubes();   // discover what's queryable
const rows = await engine.cubeQuery({
  cube: 'order_metrics',
  measures: ['revenue', 'order_count'],
  dimensions: ['customer'],
  timeDimensions: [{
    dimension: 'created_at',
    granularity: 'month',
    dateRange: ['2024-01-01', '2024-04-01'],
  }],
  filters: [{ dimension: 'status', operator: 'eq', value: 'open' }],
});
```

交互式的表单式构建器请参见 [`examples/cube-explorer.html`](https://github.com/CrossNow/JanusAI/blob/main/core/janus-core-wasm/examples/cube-explorer.html)；三种 CSV 用法（推断模式、自定义分隔符、显式模式）请参见 [`examples/csv-quickstart.html`](https://github.com/CrossNow/JanusAI/blob/main/core/janus-core-wasm/examples/csv-quickstart.html)。

---

## API 参考

### `JanusEngine.init(options?)`

初始化引擎并加载 WASM 二进制文件。每个页面生命周期调用一次即可。

```typescript
static async init(options?: JanusEngineOptions): Promise<JanusEngine>
```

| 选项 | 类型 | 说明 |
|---|---|---|
| `wasmUrl` | `string \| URL \| BufferSource` | WASM 二进制文件的来源。默认通过 `import.meta.url` 解析同级的 `janus_core_wasm_bg.wasm`。 |

### `engine.loadMDL(mdl, profile)`

加载 MDL 清单，并使用 Janus 分析器规则重新配置会话。

```typescript
async loadMDL(mdl: object, profile: JanusProfile): Promise<void>
```

| `profile.source` | 模式 | 行为 |
|---|---|---|
| `"https://…/"` / `"http://…/"` | **URL 模式** | 为每个模型自动注册一个 `ListingTable`，路径为 `{source}/{table_name}.parquet`。无需预先注册。 |
| `""`（空字符串） | **自动检测模式** | 对每个模型，如果其 `tableReference` 看起来是 URL，则采用 URL 模式；否则期望该表已经注册。上面的内联快速开始即使用此模式。 |
| 其他任何值 | **严格本地模式** | 所有表都必须通过 `register*` 预先注册。任何缺失的表都会在 `loadMDL` 时立即抛出 `Unresolved models: [...]`，而不是推迟到查询时。 |

调用后，裸模型名会在 MDL 的 catalog/schema 下解析。如果你已经预先注册了所有内容，并希望尽早暴露缺失表的错误，请使用严格本地模式（任何非 URL、非空的 source 字符串）；如果要与内置浏览器示例的行为保持一致，请使用自动检测模式（`""`）。

### `engine.registerJson(name, data)`

将 JSON 数组注册为一个命名表。模式根据第一行推断。在使用自动检测或严格本地模式时，请在 `loadMDL` 之前调用。

```typescript
async registerJson(name: string, data: object[]): Promise<void>
```

### `engine.registerParquet(name, data)`

将 Parquet 文件注册为一个命名表。

```typescript
async registerParquet(name: string, data: BufferSource): Promise<void>
```

`BufferSource` 涵盖 `ArrayBuffer`、任意 `TypedArray`（`Uint8Array`）以及 Node.js 的 `Buffer`。视图的 `byteOffset` / `byteLength` 会被正确处理。

### `engine.registerCsv(name, data, options?)`

将 CSV 数据注册为一个命名表。接受字符串（UTF-8）或 `BufferSource`。

```typescript
async registerCsv(
  name: string,
  data: string | BufferSource,
  options?: CsvReadOptions,
): Promise<void>
```

| 选项（驼峰命名） | 类型 | 默认值 |
|---|---|---|
| `header` | `boolean` | `true` |
| `delimiter` | `string`（1 个 ASCII 字符） | `,` |
| `quote` | `string`（1 个 ASCII 字符） | `"` |
| `escape` | `string`（1 个 ASCII 字符） | 未设置 |
| `terminator` | `string`（1 个 ASCII 字符） | `\n` / `\r\n` |
| `batchSize` | `number` | `8192` |
| `inferRows` | `number` | `1000` |
| `schema` | `[{name, type, nullable?}]` | 推断 |

Schema 列类型（不区分大小写）：`int8`/`int16`/`int32`/`int64`、`uint8`/`uint16`/`uint32`/`uint64`、`float32`/`float64`、`boolean`、`string`（别名 `utf8`/`varchar`/`text`）、`date`/`date32`/`date64`、`timestamp` 以及 `timestamp_{s,ms,us,ns}`。

### `engine.query(sql)`

通过上下文层执行 SQL 查询，返回解析后的行。

```typescript
async query(sql: string): Promise<Record<string, unknown>[]>
```

### `engine.cubeQuery(query)`

针对已加载的 MDL 运行结构化的 Cube 查询。它会把 `CubeQuery` JSON 翻译为 SQL，然后走与 `query()` 相同的路径执行。需要先调用 `loadMDL`。

```typescript
async cubeQuery(query: CubeQueryInput): Promise<Record<string, unknown>[]>

interface CubeQueryInput {
  cube: string;
  measures: string[];
  dimensions?: string[];
  timeDimensions?: TimeDimensionInput[];
  filters?: CubeFilterInput[];
  orderBy?: CubeOrderByInput[];
  limit?: number;
  offset?: number;
}

export type SortDirection = "asc" | "desc";

export interface CubeOrderByInput {
  member: string;
  direction: SortDirection;
}
```

省略 `orderBy`（或传入空数组）时，默认按第一个时间维度排序。指定 `orderBy` 时，`member` 必须是该查询所选中的某个度量、维度或时间维度，并且每个成员最多只能出现一次。

完整的输入结构和过滤运算符列表，请参见 [Cube 指南](../guides/cubes.md)。

### `engine.listCubes()`

返回已加载 MDL 中定义的 Cube。这是同步方法，适合让智能体在调用 `cubeQuery` 之前先发现有哪些内容可以查询。

```typescript
listCubes(): CubeInfo[]
```

### `engine.free()`

释放 WASM 内存。当引擎不再需要时调用（例如 SPA 路由卸载时）。

---

## 集成模式

### 打包工具配置

打包工具必须把 `.wasm` 文件复制到输出目录中。大多数配置会自动处理；如果没有，请显式传入 URL：

```javascript
import wasmUrl from '@janusai/janus-core-wasm/dist/janus_core_wasm_bg.wasm?url';
const engine = await JanusEngine.init({ wasmUrl });
```

Vite 支持 `?url` 后缀。Webpack 5 需要开启 `experiments.asyncWebAssembly`。对于其他打包工具，请自行获取二进制文件并传入 `ArrayBuffer`。

### 单页面多个引擎

多次调用 `JanusEngine.init()` 是安全的，每次调用都会返回一个拥有独立 catalog 的引擎实例。这对于在同一页面上为每个租户沙箱化数据很有用。WASM 模块本身通过标准的 `import` 缓存共享，因此只有第一次 init 需要下载二进制文件。

### 以 Cube 作为智能体接口

对于由 LLM 驱动的界面，请优先使用 `cubeQuery`，而不是教智能体编写 SQL：

1. 在 `loadMDL` 之后调用一次 `listCubes()`，并将结果注入系统提示词，作为智能体可用聚合的"菜单"。
2. 让智能体输出一个 `CubeQueryInput` JSON 对象，无需了解 `GROUP BY` / `DATE_TRUNC`。
3. `cubeQuery()` 会在运行前根据 MDL 校验请求，因此拼写错误（例如 `measures: ['revnu']`）会抛出结构化错误，你可以将其反馈给 LLM。

---

## 示例

可运行的浏览器演示位于 [`examples/`](https://github.com/CrossNow/JanusAI/tree/main/core/janus-core-wasm/examples)：

| 演示 | 展示内容 |
|---|---|
| `inline.html` | `registerJson` + 原始 SQL |
| `url-mode.html` | 通过 HTTP 范围请求读取远程 Parquet |
| `csv-quickstart.html` | 三种 `registerCsv` 用法（推断 / TSV / 显式模式） |
| `cube-quickstart.html` | 最简 `cubeQuery`，包含三个预设查询 |
| `cube-explorer.html` | 表单驱动的 `CubeQuery` 构建器 |

```bash
cd core/janus-core-wasm
just build-wasm-dev
just serve              # http://localhost:8787
```

---

## 故障排查

| 现象 | 原因 | 修复方法 |
|---|---|---|
| `loadMDL` 报 `Unresolved models: [foo]` | 处于严格本地模式，但 `foo` 对应的物理表未预先注册 | 在 `loadMDL` 之前为每个模型调用 `register*`，或切换到 URL 模式 |
| `undefined is not an object (evaluating 'arg.length')` | 以错误的参数个数或类型调用原始 WASM API（例如在需要字节的地方传入了字符串） | 使用 TypeScript SDK 的重载（`engine.registerCsv(name, str)`）；原始 `pkg/` API 需要字节和显式的选项 JSON |
| `Cube query for 'X' must include at least one measure…` | `measures`、`dimensions` 和 `timeDimensions` 均为空 | Cube 查询必须投影出某些内容，至少添加一个字段 |
| `Unsupported CSV column type 'bogus'` | 显式模式中存在拼写错误 | 参见 `registerCsv` 下的类型列表，查看可接受的名称 |
| `init()` 超过 5 秒仍无响应 | 初始 WASM 下载（原始约 72 MB，gzip 后约 15 MB） | 添加加载指示器；考虑自托管并缓存二进制文件，而不是使用 CDN |
| jsDelivr 返回 404 | jsDelivr 的 50 MB 单文件 CDN 上限阻止了二进制文件 | 改用 [unpkg](https://unpkg.com/)，或自行托管 |

---

## 兼容性

| `@janusai/janus-core-wasm` | janus-core | 浏览器 |
|---|---|---|
| 0.3.x | 0.5.x | 任何支持 WASM 和 ES 模块的浏览器（Chrome 91+、Firefox 89+、Safari 15+） |

该包提供一个 `dist/` 打包产物（ES 模块）以及 `.wasm` 二进制文件。没有 UMD 或 CommonJS 构建。

---

## 限制

- **WASM 二进制约 72 MB。** 冷加载在网速较快时需要 1–4 秒；请展示加载状态。后续加载会使用 HTTP 缓存。
- **仅支持内存中的表。** `registerJson` / `registerCsv` 会将整个数据集物化为 Arrow 批次，实际上限取决于浏览器标签页能容纳多少数据（通常在内存压力出现前可容纳数百 MB）。
- **不支持流式处理。** 每次 `register*` 调用都会在可查询之前完整缓冲数据。对于非常大的远程文件，请改用 URL 模式（DataFusion 通过范围请求以流式方式读取 Parquet）。
- **单线程。** DataFusion 构建时配置了 `target_partitions = 1`，没有 Web Worker 线程池。长查询会阻塞主线程；如果对响应速度有要求，请考虑在 Worker 中运行引擎。
- **使用上游 DataFusion（而非 Canner 分支）。** WASM 不需要 unparser 修复；代价是 janus-core 中一些依赖分支专有行为的高级分析器路径在此无法被覆盖。
- **没有记忆模块。** 语义搜索记忆（LanceDB）是由 `janus-langchain` / `janus-pydantic` 提供的服务端功能，WASM SDK 中不可用。
