# Equity Research Agent 初版设计文档

日期：2026-06-02

## 1. 项目定位

这个项目不应该被定位为简单的 `Stock Price Prediction`，而应该定位为一个 AI 辅助投研系统。

核心想法是：

> 构建一个 Java 金融分析后端，使用 AI Agent 收集市场数据、分析新闻和公告、调用预测或回测工具，并生成带风险意识的股票研究报告。

推荐项目名：

> Equity Research Agent

可选名称：

- AI Stock Analysis Agent
- Financial Research Copilot
- Multi-Agent Stock Intelligence Platform
- Risk-Aware Stock Forecasting Agent

不建议把 `Stock Price Prediction` 作为主名称，因为它显得范围太窄，也容易被面试官认为只是一个机器学习作业。

## 2. 简历目标

这个项目最初希望同时服务两个求职方向：

- Java 后端开发
- AI Agent 应用开发

Java 后端方向应该展示：

- Spring Boot service design
- REST API design
- database modeling
- caching
- async jobs
- external API integration
- structured logging and error handling
- deployment readiness

AI Agent 方向应该展示：

- task planning
- tool calling
- RAG over financial documents
- multi-source reasoning
- forecasting and backtesting tool integration
- uncertainty handling
- structured report generation
- hallucination control and citation awareness

最强定位是：

> 一个以 AI Agent 为核心业务能力的 Java 后端平台。

## 3. 为什么不只做股价预测

如果项目只是：

- 输入股票 ticker
- 获取历史价格
- 训练模型
- 预测明天价格或涨跌

它会显得太浅，像课程作业。它还会引出很多难回答的问题：预测准确率、市场噪声、数据泄漏、真实交易价值等。

更好的方向是把 forecasting 放在更大的 research workflow 中，只作为一个工具。Agent 不应该声称确定性，而应该输出证据、风险、不确定性和不同视角。

## 4. Java 后端导向架构

如果项目偏 Java 后端岗位，架构重点应该是服务边界、持久化、可靠性和 API 设计。

```text
Frontend / API Client
        |
Spring Boot Backend
        |
REST Controllers
        |
Service Layer
  - StockService
  - WatchlistService
  - PortfolioService
  - MarketDataService
  - ReportService
  - BacktestService
        |
Data Layer
  - PostgreSQL / MySQL
  - Redis
  - Object Storage
        |
External Integrations
  - Market Data API
  - News API
  - Financial Statement API
```

重要模块：

- `UserModule`：用户身份、偏好、保存报告、watchlists
- `MarketDataModule`：价格、指标、缓存刷新、API fallback
- `ReportModule`：生成报告历史和元数据
- `BacktestModule`：策略输入、回测执行、指标持久化
- `JobModule`：异步任务状态、重试、后台分析任务
- `AuditModule`：请求日志、工具调用记录、模型输出记录

后端面试讲法：

- long-running AI analysis jobs 的 API 设计
- report、watchlist、tool call、market snapshot 的数据库建模
- Redis 缓存减少重复外部 API 调用
- async execution 避免阻塞 HTTP 请求
- 外部数据 API 失败时的 retry 和 fallback
- domain service 与 AI orchestration 分离
- agent runs 的 observability

## 5. AI Agent 导向架构

如果项目偏 AI Agent 应用岗位，重点应该是任务拆解、工具调用、信息检索和结构化推理。

```text
User Query
   |
Agent Orchestrator
   |
Planner
   |
Tool Router
   |
Specialized Tools
  - Market Data Tool
  - Technical Indicator Tool
  - News Search Tool
  - Filing Retrieval Tool
  - Forecast Tool
  - Backtest Tool
  - Chart Tool
   |
Evidence Aggregator
   |
Risk Analyzer
   |
Report Generator
   |
Structured Research Report
```

重要 agent 模块：

- `Planner`：将用户问题拆成分析步骤
- `ToolRouter`：根据 plan 选择工具
- `MarketDataTool`：获取价格、成交量、波动率、指标
- `NewsAnalysisTool`：总结新闻并提取 sentiment
- `FilingRagTool`：检索财报、公告或公司文档
- `ForecastTool`：运行时间序列或机器学习预测
- `BacktestTool`：测试简单策略或假设
- `RiskAnalyzer`：识别风险、不确定性和冲突证据
- `ReportGenerator`：生成结构化最终报告

AI 面试讲法：

- agent 如何决定调用哪些工具
- retrieved evidence 如何附着到最终回答
- 系统如何避免 unsupported investment claims
- 为什么输出 risk-aware analysis，而不是 deterministic prediction
- 工具输出如何标准化后交给 LLM
- agent runs 如何记录和评估

## 6. 推荐融合架构

初版推荐的整体方向是：

> Spring Boot 提供产品和后端平台，AI Agent 提供核心金融分析工作流。

```text
React / Vue Dashboard
        |
Spring Boot Backend
  - REST API
  - Auth
  - Watchlists
  - Report History
  - Async Job Management
  - Observability
        |
Agent Service
  - Query Planner
  - Tool Router
  - RAG Retriever
  - Forecast Executor
  - Backtest Executor
  - Risk Analyzer
  - Report Generator
        |
Data and Infrastructure
  - PostgreSQL
  - Redis
  - Vector Database
  - Market Data API
  - News API
  - Financial Filing Parser
```

这个方向可以同时服务：

- Java 后端面试：Spring Boot financial analysis platform
- AI Agent 面试：tool-using equity research agent
- 全栈或产品向面试：end-to-end AI financial research application

## 7. 推荐技术栈

后端：

- Java 17 或 21
- Spring Boot
- Spring Web
- Spring Data JPA
- PostgreSQL
- Redis
- Spring Scheduler 或轻量 job queue

AI 和 agent 层：

- LangChain4j、Spring AI，或自定义轻量 agent orchestration
- OpenAI-compatible LLM API
- pgvector、Qdrant、Chroma 等 vector database
- structured JSON tool-call contracts

数据和分析：

- market data API
- news API
- financial filings 或 company fundamentals API
- forecasting service，可以用 Java 或 Python microservice

前端：

- React 或 Vue
- dashboard 包含 query input、report view、charts、watchlist、job status

部署：

- Docker Compose 本地开发
- backend、database、Redis、vector database、可选 Python forecasting service 分开运行

## 8. 核心用户流程

示例问题：

> Analyze NVIDIA's opportunities and risks over the next month.

系统流程：

1. 用户提交分析请求。
2. 后端创建异步 analysis job。
3. Agent planner 将请求拆成子任务。
4. Tool router 按需调用 market data、news、filings、forecast、backtest tools。
5. Evidence aggregator 标准化工具输出。
6. Risk analyzer 识别 bullish evidence、bearish evidence、uncertainty 和 missing data。
7. Report generator 创建结构化 research report。
8. 后端保存报告并返回给 dashboard。

## 9. 报告结构

生成报告应该包含：

- executive summary
- recent price and volume behavior
- key technical indicators
- news and sentiment summary
- fundamental or filing highlights
- forecast output with confidence or uncertainty
- backtest result if a strategy is tested
- bullish factors
- bearish factors
- risk warnings
- final non-advisory conclusion

报告应避免直接投资建议，例如“买入这只股票”。更适合使用：

- “现有证据显示……”
- “主要上行因素包括……”
- “主要风险包括……”
- “这个结论仍有不确定性，因为……”

## 10. MVP 范围

第一版应该聚焦。

MVP features：

- stock ticker search
- market data fetch
- technical indicators
- AI-generated research report
- report history
- async job status
- basic dashboard

MVP agent tools：

- market data tool
- indicator tool
- news summary tool
- report generator

MVP backend features：

- REST APIs
- PostgreSQL persistence
- Redis cache
- async analysis job
- basic error handling

MVP 不应包含所有可能功能，目标是先建立可靠平台基础。

## 11. 后续扩展

较好的扩展方向：

- financial filing RAG
- multi-agent architecture
- portfolio-level risk analysis
- backtesting dashboard
- stock comparison mode
- watchlist alerts
- scheduled daily reports
- confidence scoring
- tool-call trace viewer
- evaluation dataset for agent outputs
- Docker deployment
- CI tests

multi-agent 可以后续演进：

```text
Research Manager Agent
        |
Specialist Agents
  - Market Data Agent
  - News Agent
  - Fundamentals Agent
  - Forecast Agent
  - Risk Agent
  - Report Agent
```

不建议一开始就做多 agent，因为会在产品价值尚未验证前引入过多复杂度。

## 12. 实现倾向

初版建议：

> 70% Java 后端工程，30% AI Agent 能力。后续再演进到 50% 后端、50% AI Agent。

原因：

- 项目作者已有 Java 后端学习基础。
- 强后端基础能支撑传统后端岗位。
- Agent 能力可以逐层叠加。
- 项目仍然能贴合 AI application hiring trend。

## 13. 推荐仓库结构

完整结构：

```text
equity_research_agent/
  backend/
    src/main/java/...
    src/test/java/...
    pom.xml
  frontend/
    package.json
    src/
  docs/
    superpowers/specs/
    architecture/
    api/
  docker-compose.yml
  README.md
```

如果第一版只做后端，可以更简单：

```text
equity_research_agent/
  src/main/java/...
  src/test/java/...
  docs/
  pom.xml
  README.md
```

如果前端或 Python forecasting service 很早加入，再采用多目录结构。

## 14. 实现路线

Phase 1：后端基础

- 创建 Spring Boot project
- 设计核心实体：stock、analysis job、report、tool call record
- 实现创建 analysis job 和查询 reports 的 REST APIs
- 加 PostgreSQL persistence
- 加 Redis cache for market data

Phase 2：基础 agent workflow

- 实现 simple single-agent orchestrator
- 定义 tool input / output DTOs
- 添加 market data 和 technical indicator tools
- 从工具结果生成 structured research report
- 持久化 tool-call traces

Phase 3：产品 dashboard

- 创建简单 frontend dashboard
- 支持 natural language query input
- 展示 async job status
- 渲染 report 和 charts
- 展示 report history

Phase 4：研究深度

- 添加 news retrieval and summarization
- 添加 financial filing 或 fundamentals retrieval
- 如果有文档数据，再加 RAG
- 改善 report evidence grounding

Phase 5：高级扩展

- 添加 forecasting tool
- 添加 backtesting tool
- 添加 portfolio 或 watchlist analysis
- 添加 scheduled reports 或 alerts
- 可选拆出 Python forecasting microservice

建议第一阶段目标是 Phase 1 加上 Phase 2 的最小部分：先得到可运行后端和可见 agent 能力。

## 15. 第一版架构决策

第一版使用单个 Spring Boot 应用。

内部将 agent 层放到独立 package：

```text
com.example.equityresearch
  api
  application
  domain
  infrastructure
  agent
    planner
    tools
    report
    memory
```

这样避免 premature microservices，同时保持边界清楚。只有当 forecasting 逻辑在 Java 中维护困难时，再考虑 Python microservice。

## 16. 简历描述

可用项目标题：

> Equity Research Agent: Java-based Multi-Agent Financial Analysis Platform

可用 bullet：

> 构建 Java Spring Boot 投研平台，集成市场数据、新闻分析、预测工具和 LLM-based agent workflow，生成结构化、风险敏感的股票研究报告。

后端版本：

> 构建 AI 金融研究平台的 Spring Boot 后端，实现 REST APIs、async job processing、PostgreSQL data modeling、Redis caching、external API integration 和 report history management。

AI 版本：

> 实现 tool-using AI agent，将股票研究问题拆解为多个子任务，检索市场和新闻数据，调用 forecasting / backtesting tools，并生成 evidence-grounded investment research report 和明确风险分析。

## 17. 成功标准

项目成功标准：

- 用户可以提交自然语言股票分析请求。
- 后端创建并追踪 analysis job。
- Agent 调用多个工具，而不是只生成 generic LLM text。
- 最终报告包含 evidence、uncertainty 和 risk analysis。
- 报告被持久化，并且之后可以查看。
- 系统足够 explainable，能在面试中深入讲解。
- 架构可以扩展，不需要推倒重来。

## 18. 关键设计决策

核心决策是：

> 不做纯股价预测应用，而是做 backend-driven equity research agent。预测只是大研究工作流中的一个工具。

这个方向更可信、更可扩展，也更贴合 Java 后端和 AI Agent 应用两个求职方向。
