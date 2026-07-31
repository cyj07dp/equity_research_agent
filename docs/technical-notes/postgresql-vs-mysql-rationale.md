# 为什么本项目更倾向使用 PostgreSQL 而不是 MySQL

## 结论

MySQL 和 PostgreSQL 都可以完成本项目的基础后端功能。选择 PostgreSQL 不是因为 MySQL 不行，而是因为 `Equity Research Agent` 未来会存储大量半结构化数据，并且可能扩展到 RAG 和向量检索。

本项目不仅有普通业务表，还会保存：

- agent 工具调用输入
- agent 工具调用输出
- 外部 API 原始响应
- LLM 原始输出
- 结构化研究报告
- evidence items
- 后续可能加入的 filing chunks
- 后续可能加入的 embeddings

这些数据很多天然适合用 PostgreSQL 的 `jsonb` 和后续 `pgvector` 扩展承载。

## MySQL 和 PostgreSQL 的基本区别

MySQL 更常见于传统 Web 后端业务系统，适合用户、订单、商品、权限等典型关系型数据场景。它生态成熟、资料多，在 Java 后端面试中认可度很高。

PostgreSQL 也适合传统后端业务，但它在复杂 SQL、半结构化数据、全文检索、扩展能力和向量扩展方面更强。因此，在 AI 应用、数据分析、复杂业务建模、RAG 原型系统中，PostgreSQL 往往更顺手。

简单来说：

- 如果项目主要是普通 CRUD，MySQL 非常合适。
- 如果项目会保存 JSON、日志、原始响应、文档片段和 embedding，PostgreSQL 更有优势。

## 为什么本项目更适合 PostgreSQL

### 1. 本项目不是普通 CRUD 系统

`Equity Research Agent` 的核心数据不只是普通业务记录，还包括 research job、generated report、tool call trace、evidence item、external API raw response、LLM raw output 和 structured report JSON。

不同金融 API 的返回格式可能不同，不同工具的输入输出也可能不同。如果全部强行拆成固定关系表，模型会变重；如果全部作为字符串保存，又不方便查询和调试。PostgreSQL 的 `jsonb` 字段可以较好地平衡灵活性和可查询性。

### 2. PostgreSQL 更适合保存 agent 运行轨迹

本项目的面试亮点之一是：最终报告不是 LLM 随便生成的，而是来自可追溯的工具调用和 evidence。

`ToolCallRecord` 可能需要保存：

- `toolName`
- `inputJson`
- `outputJson`
- `rawProviderResponse`
- `errorMetadata`
- `latencyMs`
- `status`

这些字段中的 JSON payload 很适合用 PostgreSQL `jsonb` 保存。这样既可以保留完整上下文，又可以在需要时查询 JSON 内部字段。

面试时可以这样解释：

> 我使用 PostgreSQL 的 `jsonb` 字段保存工具输入、工具输出、外部 API 原始响应和 LLM trace，这样每份生成报告都可以被审计和调试。

### 3. PostgreSQL 方便后续扩展 RAG 和 pgvector

V2 第一版不会立刻做 RAG，但未来一个自然突破点是：

> 加入 SEC filing retrieval 和 RAG，让 agent 能基于 10-K、10-Q、earnings call transcript 等材料生成更可信的研究 memo。

如果使用 PostgreSQL，后续可以通过 `pgvector` 在同一个数据库中保存 embedding，例如：

- filing chunk
- chunk metadata
- embedding vector
- source document
- retrieval score

项目可以自然演进为：

```text
PostgreSQL
  -> job / report / tool trace
  -> evidence item
  -> filing chunks
  -> pgvector embeddings
  -> RAG retrieval
```

这说明技术选型考虑了后续 AI 应用能力，而不是随便选数据库。

### 4. PostgreSQL 更符合本项目的 AI 应用方向

现代 AI 应用经常同时处理：

- 结构化业务数据
- 半结构化 JSON 数据
- 文档文本
- 工具调用日志
- 模型输入输出
- embedding 向量

PostgreSQL 可以同时覆盖传统关系型数据和这些 AI 应用常见数据形态。对本项目来说，它比 MySQL 更贴合“AI Agent + 金融数据工作流”的方向。

## 为什么不是说 MySQL 不行

MySQL 仍然可以完成本项目的基础功能：

- research job 表
- report 表
- tool call 表
- REST API 查询
- Spring Data JPA 持久化

如果项目目标只是展示传统 Java 后端能力，MySQL 完全合理。

但本项目还希望展示 AI Agent 工程能力。相比 MySQL，PostgreSQL 更容易支撑这些亮点：

- 用 `jsonb` 保存工具输入输出和 LLM trace
- 用半结构化字段保留外部 API 原始响应
- 后续通过 `pgvector` 支持 RAG
- 更适合复杂查询和分析型数据
- 更适合作为 AI 应用的统一数据底座

## 面试回答模板

如果面试官问“为什么这个项目使用 PostgreSQL，而不是 MySQL？”，可以回答：

> MySQL 做基础 CRUD 完全没问题，但这个项目不是单纯的业务管理系统。它需要保存 agent 工具调用、外部 API 原始响应、LLM 输出和结构化研报，这些数据很多是半结构化 JSON。PostgreSQL 的 `jsonb` 更适合保存和查询这些内容，而且未来如果做 SEC filing RAG，可以通过 `pgvector` 扩展支持向量检索。所以我选择 PostgreSQL，是为了让系统更适合 AI 投研工作流的后续演进。

## 当前项目建议

本项目第一版建议使用：

- PostgreSQL 作为主数据库
- Spring Data JPA 管理核心实体
- `jsonb` 保存 tool input、tool output、raw response、LLM raw output
- fake provider 支持稳定测试
- 后续再考虑 `pgvector` 和 RAG

这样既能体现 Java 后端能力，也能为 AI Agent 方向留下清晰扩展空间。
