---
sidebar_label: 构建并部署 CReport 应用
---

# 构建并部署 CReport 应用

CReport 会把你项目的上下文层转换为可分享的浏览器端仪表盘，由 [`janus-core-wasm`](/oss/sdk/wasm) 驱动，并部署到你自己的 Vercel 或 Cloudflare Pages 账号上。你不需要亲自输入 `janus creport` 命令：只需用自然语言描述你想要的仪表盘，智能体会驱动 CLI 生成一个公开链接。

本指南说明如何**与你的智能体对话**来完成这件事：如何请求仪表盘，以及如何请求部署。底层命令和每个参数，请参见 [`janus creport` CLI 参考](/oss/reference/cli#janus-creport--build--deploy-creport-apps)。

## 开始之前

你需要两样东西：

- **一个 Janus 项目**：仪表盘所读取的上下文层。如果还没有，请先[连接数据源](connect.md)。
- **一个能使用 `janus` CLI 的智能体**：任何可以运行 Shell 命令的编码智能体。智能体会通过 `janus skills get creport` 按需加载自己的 CReport 操作手册，因此你不需要教它工作流程。

就这些。接下来只需要对话。

## 创建仪表盘

用自然语言描述你想要的内容。智能体会确定查询、选择图表并组装应用。你可以像与同事协作一样与它反复迭代：

```text
用户：  我的项目在 ~/forecast 目录。展示上周按产品划分的预测。
用户：  再看看 8 周的趋势。
用户：  把它做成可以按产品和 OSAT 筛选、然后可以分享的交互式仪表盘。
智能体：已完成并运行了检查。要先在本地预览，还是直接部署？
用户：  先预览。
智能体：已在 http://127.0.0.1:8848/ 提供服务
用户：  把 OSAT 图表改成占比图，并把配色调浅一些。
智能体：已更新。请刷新预览。
```

在每一轮对话背后，智能体都在为你完成确定性的工作，你不需要自己运行这些步骤：

- **从 CLI 获取权威的构建说明**（它了解你项目的实时状态和固定的 wasm 版本）。
- **按照该说明在 `apps/<name>/` 下编写应用**，并选择能回答你问题的图表和布局。
- **记录并检查应用**，使其可以部署，包括一项会拒绝发布内嵌凭据的密钥扫描。
- **在你要求时进行本地预览**，让你在别人看到之前先确认效果。

如果你想了解这些步骤对应的具体命令，它们都列在 [CLI 参考](/oss/reference/cli#janus-creport--build--deploy-creport-apps) 中。

## 快照与实时数据

这是你在对话中会做出的唯一一个实质性选择。告诉智能体你想要哪一种（默认为 **snapshot**）：

| 模式 | 数据存放位置 | 适用场景 |
|------|--------------|----------|
| **snapshot**（默认） | 随应用打包，并通过 wasm 在客户端查询 | 演示、报告、小数据量、dlt 管道输出，完全无服务器 |
| **live** | 应用在查看时回调你的数据仓库或 API | 生产级规模或需要始终最新的数据；需要支持 CORS 的端点，并且**绝不**内嵌凭据 |

snapshot 会在构建时冻结数字，因此非常适合你要交付的报告。如果仪表盘必须保持最新，请选择 live。

## 分享前预览

直接提问即可：

```text
用户：  在本地预览一下。
智能体：已在 http://127.0.0.1:8848/ 提供服务
```

智能体会在你的机器上提供构建好的应用，让你在部署任何内容之前先点击体验。你可以在同一轮对话中提出修改（"改成柱状图"、"去掉 OSAT 筛选"），智能体会重新构建。

## 部署

CReport 会部署到你自己的 **Vercel** 或 **Cloudflare Pages** 账号，这是目前支持的两个平台（默认为 Vercel）。对结果满意后，请智能体进行部署：

```text
用户：  部署到 Vercel。
智能体：我需要一个 VERCEL_TOKEN。请把它添加到 ~/.janus/.env，然后告诉我。
用户：  好了。
智能体：已部署到 <preview-url>
用户：  发布到生产环境。
智能体：已晋升到 <production-url>
```

有几点需要注意，可以让对话更顺利：

- **部署令牌由你提供，而不是智能体。** 把 `VERCEL_TOKEN`（或 `CLOUDFLARE_API_TOKEN` 加上 `CLOUDFLARE_ACCOUNT_ID`）添加到环境变量或 `.env` 文件中。令牌从不通过命令行参数传递，因此不会泄漏到 Shell 历史中。
- **预览与生产。** 默认部署到预览 URL；当你希望智能体把它晋升为生产环境时，说"发布到生产环境"即可。
- **部署目标是公开的静态托管。** 任何拥有该 URL 的人都可以读取应用发布的每个文件，因此绝不要让智能体内嵌密钥。部署前的密钥扫描只是安全网，不是绝对保证。

### Vercel 401 陷阱

新建的 Vercel 项目默认开启了 **Vercel Authentication**，因此每次部署（包括预览和生产）都会向未登录你 Vercel 账号的访问者返回 **HTTP 401**。部署本身已经成功，只是 URL 被拦截了。要让仪表盘可以公开分享，请在 Vercel 控制台中关闭一次：**Project → Settings → Deployment Protection → Vercel Authentication → Disabled**。如果你只需要给自己使用的私有链接，可以保持开启。

## 另请参阅

- [`janus creport` CLI 参考](/oss/reference/cli#janus-creport--build--deploy-creport-apps)：每个子命令和参数
- [`creport` Skill](/oss/reference/skills#creport)：智能体的工作流操作手册（英文版）
- [`dlt-connector` Skill](/oss/reference/skills#dlt-connector)：在构建前加载 SaaS 数据（英文版）
- [janus-core-wasm](/oss/sdk/wasm)：驱动应用的浏览器端引擎（英文版）
