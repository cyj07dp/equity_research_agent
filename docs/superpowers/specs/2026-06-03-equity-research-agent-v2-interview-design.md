# Equity Research Agent V2 面试版设计文档

日期：2026-06-03

> 状态：已被 V3 Agent-First 设计取代。本文保留作为历史版本，后续实现应以 `2026-06-03-equity-research-agent-v3-agent-first-design.md` 为准。

## 1. 核心决策

V2 是面向面试简历的实现版本。项目定位为：

> 一个基于 Spring Boot 的投研工作流系统，通过轻量 AI Agent 调用金融分析工具、聚合证据，并生成带来源意识的 first-pass company research memo。

目标比例：

- Java 后端工程：60%
- AI Agent 应用工程：40%

第一版优先展示可靠后端能力：服务边界、异步任务、持久化、错误处理、可观测性和测试。AI 层要有实质内容，但范围保持克制：工具编排、证据聚合、结构化报告生成和输出校验。

## 2. 相比 V1 的变化

V1 的方向更像一个完整 AI 投研平台，长期可以作为灵感，但第一版范围过大。V2 收敛成一个可完成、可演示、可解释的面试项目。

第一版暂不做：

- 完整前端产品
- 用户体系、watchlist、portfolio、alerts、scheduled reports
- multi-agent 架构
- forecasting 和 backtesting
- vector database
- Python microservice

第一版目标不是功能多，而是有一个扎实闭环，可以在面试中讲清楚架构、取舍和演进空间。

## 3. 简历定位

推荐项目标题：

> Equity Research Agent：Spring Boot + LLM Financial Research Workflow

推荐简历描述：

> 构建基于 Spring Boot 的 Equity Research Agent，编排金融数据工具、证据聚合和结构化研报生成，支持异步任务执行、tool-call trace、report persistence 和 schema validation。

后端方向可以强调：

> 设计 REST APIs、async job execution、JPA persistence model、external API client abstraction、error handling 和 tool-call audit logs，支撑一个可追溯的金融研究工作流。

AI 方向可以强调：

> 实现轻量 tool-using agent，收集 market、fundamentals 和 news evidence，标准化工具输出，并生成包含风险、不确定性和来源意识的结构化 research memo。

## 4. 核心 Demo

核心 demo 应该简单、稳定、可重复：

```text
POST /api/research-jobs
input: ticker = NVDA
        |
create async research job
        |
agent calls tools:
  - market data tool
  - fundamentals tool
  - news tool
        |
evidence aggregator normalizes results
        |
report generator creates structured memo
        |
report validator checks schema and citations
        |
report and tool trace are persisted
        |
GET /api/research-jobs/{id}
GET /api/reports/{id}
```

第一批稳定 demo ticker：

- `AAPL`
- `NVDA`
- `TSLA`

第一版不追求覆盖所有股票。面试项目里，三个稳定样例比大量不稳定 ticker 更有价值。

## 5. MVP 范围

必须实现：

- Spring Boot 应用
- 创建 research job 的 REST API
- 查询 job status 的 REST API
- 查询 generated report 的 REST API
- async job execution
- market data tool
- fundamentals tool
- news tool
- evidence aggregation
- structured report generation
- report validation
- tool-call trace persistence
- report persistence
- README，包括架构、启动方式、API 示例和样例输出

建议实现：

- PostgreSQL 持久化
- Redis 或 cache abstraction，用于后续缓存外部 API 响应
- external API failure 的 retry / fallback 思路
- 主流程集成测试
- `docs/examples/` 下保存样例报告

后续再做：

- 简单 frontend report viewer
- SEC filing retrieval
- filing RAG
- confidence scoring
- tool trace viewer
- Docker Compose 完整开发环境
- CI pipeline
- forecast tool
- backtest tool

明确不做：

- user login
- watchlist management
- portfolio management
- stock alerts
- scheduled daily reports
- multi-agent specialist system
- buy / sell / hold 投资建议
- production-grade trading 或 investment advice

## 6. 推荐架构

第一版使用单体 Spring Boot 应用，不拆 microservices。

```text
Client / curl / Postman
        |
REST Controllers
        |
Application Services
  - ResearchJobService
  - ReportService
        |
Agent Orchestration
  - ResearchAgentOrchestrator
  - EvidenceAggregator
  - ReportGenerator
  - ReportValidator
        |
Tools
  - MarketDataTool
  - FundamentalsTool
  - NewsTool
        |
Infrastructure
  - External API clients
  - LLM client
  - Persistence
  - Cache
  - Logging
```

推荐 package 结构：

```text
com.example.equityresearch
  api
  application
  domain
  agent
    orchestration
    tools
    report
    validation
  infrastructure
    external
    llm
    persistence
    cache
  config
```

## 7. 核心领域模型

`ResearchJob` 表示一次分析请求，核心字段包括：

- `id`
- `ticker`
- `status`: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`
- `createdAt`
- `startedAt`
- `completedAt`
- `errorMessage`
- `reportId`

`ResearchReport` 表示最终 memo，核心字段包括：

- `id`
- `jobId`
- `ticker`
- `companyName`
- `executiveSummary`
- `businessOverview`
- `marketSnapshot`
- `fundamentalHighlights`
- `recentNews`
- `bullishFactors`
- `bearishFactors`
- `riskFactors`
- `uncertainties`
- `nonAdvisoryConclusion`
- `createdAt`
- `rawJson`

`ToolCallRecord` 表示工具调用轨迹，核心字段包括：

- `id`
- `jobId`
- `toolName`
- `inputJson`
- `outputJson`
- `status`
- `errorMessage`
- `startedAt`
- `completedAt`
- `latencyMs`

`EvidenceItem` 表示标准化证据，核心字段包括：

- `id`
- `jobId`
- `sourceType`: `MARKET_DATA`, `FUNDAMENTALS`, `NEWS`
- `sourceName`
- `sourceUrl`
- `title`
- `summary`
- `observedAt`
- `confidence`

## 8. Agent 工作流

第一版 agent 应该是轻量 orchestrator，而不是复杂 autonomous agent。

流程：

1. `ResearchJobService` 接收 ticker。
2. MVP 使用固定 research plan。
3. 调用 market data、fundamentals、news tools。
4. 持久化每次工具调用和错误。
5. 将工具输出转换为标准化 `EvidenceItem`。
6. 生成结构化 report。
7. 校验 report schema。
8. 检查主要结论是否能对应 evidence。
9. 持久化 report。
10. 将 job 标记为 `SUCCEEDED` 或 `FAILED`。

固定 workflow 比完全自主 planner 更容易实现、测试和面试讲解。dynamic planner 可以在核心闭环稳定后再加。

## 9. 报告结构

最终报告必须是结构化、非投资建议的 research memo。

必需部分：

- executive summary
- company overview
- market snapshot
- fundamental highlights
- recent news summary
- bullish factors
- bearish factors
- risk factors
- uncertainty and missing data
- non-advisory conclusion
- citations

规则：

- V2 不输出直接 `buy` / `sell` / `hold` 建议。
- 主要结论需要能连接到 evidence item。
- 数据缺失时必须明确说明。
- 结论使用 research language，不使用 investment advice language。

示例结论风格：

> 现有证据显示该公司短期情况较为混合。收入增长和产品动能是支撑因素，估值敏感性和宏观不确定性是主要风险。本 memo 仅为研究摘要，不构成投资建议。

## 10. API

创建研究任务：

```http
POST /api/research-jobs
Content-Type: application/json

{
  "ticker": "NVDA"
}
```

响应：

```json
{
  "jobId": "uuid",
  "status": "PENDING"
}
```

查询任务状态：

```http
GET /api/research-jobs/{jobId}
```

响应：

```json
{
  "jobId": "uuid",
  "ticker": "NVDA",
  "status": "SUCCEEDED",
  "reportId": "uuid",
  "errorMessage": null
}
```

查询报告：

```http
GET /api/reports/{reportId}
```

查询工具调用记录：

```http
GET /api/research-jobs/{jobId}/tool-calls
```

这个接口很适合面试 demo，因为它能证明最终报告来自工具结果，而不是单纯 LLM 泛化文本。

## 11. 数据源策略

使用 adapter interface，让真实数据源后续可以替换。

建议第一步：

- 定义 `MarketDataClient`、`FundamentalsClient`、`NewsClient` 等接口。
- 先实现 fake provider，保证测试和 demo 稳定。
- 后续再接入一个真实 provider。

第一版优先保证稳定样例输出，不追求广泛 ticker 覆盖。

## 12. 错误处理

预期失败场景：

- ticker 非法
- 外部 API rate limit
- 外部 API timeout
- fundamentals 缺失
- news 不足
- LLM generation failure
- report schema invalid

处理原则：

- 持久化失败的 tool call。
- 安全时允许 partial evidence 继续生成报告。
- 只有无法负责任地产生报告时才将 job 标为 `FAILED`。
- 报告中明确说明 missing data。
- failed job 对外暴露 `errorMessage`。

## 13. 测试策略

最低测试范围：

- ticker validation unit test
- evidence aggregation unit test
- report validation unit test
- tool error handling unit test
- fake tools + fake LLM 的端到端 workflow test
- job status 和 report retrieval API test

最重要的是 fake end-to-end workflow。它证明后端设计不依赖真实 API 或 LLM 也能运行。

## 14. 实现路线

Phase 1：后端骨架

- 创建 Spring Boot 项目。
- 添加 `ResearchJob`、`ResearchReport`、`ToolCallRecord`。
- 添加 REST endpoints。
- 添加 async job execution。
- 先接 PostgreSQL 和 JPA。

退出标准：

- 能创建 job。
- 能查询 job status。
- 能生成并查询 fake report。

Phase 2：fake tools agent workflow

- 实现 `ResearchAgentOrchestrator`。
- 实现 fake market data、fundamentals、news tools。
- 实现 evidence aggregation。
- 持久化 tool-call traces。
- 从 evidence 生成 deterministic placeholder report。

退出标准：

- 一次请求能生成 report 和 tool-call trace。
- workflow 可以在没有真实 API / LLM 的情况下测试。

Phase 3：LLM report generation

- 增加 LLM client abstraction。
- 增加 structured prompt。
- 生成 JSON report。
- 校验 report schema。
- 本地 demo 模式保留 deterministic fallback。

Phase 4：真实数据 adapter

- 接入一个 market/fundamentals provider。
- 接入一个 news provider。
- 保留 fake providers 用于测试。
- 缓存外部 API 响应。
- 改善 missing-data 行为。

Phase 5：面试展示打磨

- README 架构图。
- API 示例。
- `docs/examples/` 样例报告。
- 设计取舍说明。
- 测试和验证说明。
- 可选 Docker Compose 完整化。

## 15. 后续突破点

V2 稳定后，每次只往一个方向增强。

可选方向：

- SEC filing retrieval and RAG
- report evaluation dataset
- citation quality scoring
- two-ticker comparison mode
- thin frontend report viewer
- forecasting as optional tool
- backtesting as optional tool
- scheduled watchlist reports

推荐第一个突破点：

> 增加 SEC filing retrieval 和 RAG。它能加强 AI Agent 叙事，又不会把项目带偏成股价预测应用。

## 16. 面试讲法

后端亮点：

- long-running AI task 建模为 async job。
- tool-call trace 作为 audit log。
- external API abstraction 和 fake provider 提高可测试性。
- report persistence 前做 schema validation。
- partial failure handling。
- persistence model 围绕 explainability 设计。

AI 亮点：

- fixed workflow first，dynamic planning later。
- tool outputs 先标准化，再进入 report generation。
- citations 和 evidence grounding 降低 unsupported claims。
- non-advisory language 避免虚假的投资确定性。
- fake LLM / fake tools 让评估可复现。

重要取舍：

> 第一版不直接做完全自主 multi-agent 系统。对面试项目来说，deterministic orchestrator + tool use + trace + validation 更可靠，也更容易测试。核心闭环稳定后，再加入 dynamic planning。

## 17. 成功标准

V2 成功标准：

- `POST /api/research-jobs` 能启动异步分析。
- 可以轮询 job status。
- 可以查询最终 report。
- tool-call traces 能展示数据来源。
- report 是结构化并经过校验的。
- fake providers 支持稳定测试。
- 至少一个真实数据 demo 能跑通。
- README 解释架构、取舍和样例输出。
- 简历 bullet 与实际实现一致。

## 18. 当前建议

先实现 Phase 1 和 Phase 2，不接真实 API，不接真实 LLM。

原因：

- 先证明后端 workflow。
- 快速得到 runnable project。
- 避免一开始卡在 API key、rate limit 或 prompt instability。
- 为后续 LLM 和真实数据 adapter 留出清晰边界。
