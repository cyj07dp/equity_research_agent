# Equity Research Agent Design Spec

Date: 2026-06-02

## 1. Project Positioning

This project should be positioned as an AI-assisted equity research platform, not a simple stock price prediction demo.

The core idea is:

> Build a Java-based financial analysis backend that uses an AI agent to collect market data, analyze news and filings, run forecasting or backtesting tools, and generate risk-aware stock research reports.

The project name should preferably be:

> Equity Research Agent

Alternative names:

- AI Stock Analysis Agent
- Financial Research Copilot
- Multi-Agent Stock Intelligence Platform
- Risk-Aware Stock Forecasting Agent

Avoid using `Stock Price Prediction` as the primary project name, because it sounds narrower and easier than the system we want to build.

## 2. Resume Goal

The project should support two job-search directions at the same time:

- Java backend development
- AI agent application development

For Java backend roles, the project should demonstrate engineering depth:

- Spring Boot service design
- REST API design
- database modeling
- caching
- async jobs
- external API integration
- structured logging and error handling
- deployment readiness

For AI agent roles, the project should demonstrate agent application ability:

- task planning
- tool calling
- RAG over financial documents
- multi-source reasoning
- forecasting and backtesting tool integration
- uncertainty handling
- structured report generation
- hallucination control and citation awareness

The strongest positioning is:

> A Java backend platform with an AI agent as the core business capability.

## 3. Why Not Build Only Stock Price Prediction

A simple stock prediction project is likely to be considered too shallow if it only does the following:

- input a stock ticker
- fetch historical prices
- train a model
- predict tomorrow's price or trend

This version looks like a machine learning homework project. It also invites difficult questions about prediction accuracy, market noise, data leakage, and whether the model has real-world value.

The better project direction is to treat forecasting as one tool inside a larger research workflow. The agent should not claim certainty. It should produce analysis with evidence, risk factors, confidence levels, and alternative views.

## 4. Java Backend-Oriented Architecture

If the project is optimized for Java backend roles, the architecture should emphasize service boundaries, persistence, reliability, and API design.

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

Important backend modules:

- `UserModule`: user identity, preferences, saved reports, watchlists
- `MarketDataModule`: stock prices, indicators, cache refresh, API fallback
- `ReportModule`: generated report history and report metadata
- `BacktestModule`: strategy input, backtest execution, metrics persistence
- `JobModule`: async task status, retries, background analysis jobs
- `AuditModule`: request logs, tool invocation records, model output records

Backend-focused interview talking points:

- API design for long-running AI analysis jobs
- database schema for reports, watchlists, tool calls, and market snapshots
- Redis caching to reduce repeated external API calls
- async execution to avoid blocking HTTP requests
- retry and fallback when external data APIs fail
- separation between domain services and AI orchestration
- observability for agent runs

## 5. AI Agent-Oriented Architecture

If the project is optimized for AI agent application roles, the architecture should emphasize task decomposition, tool use, information retrieval, and structured reasoning.

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

Important agent modules:

- `Planner`: converts user questions into analysis steps
- `ToolRouter`: chooses which tool to call based on the plan
- `MarketDataTool`: fetches prices, volume, volatility, and indicators
- `NewsAnalysisTool`: summarizes market news and extracts sentiment
- `FilingRagTool`: retrieves relevant financial filings or company documents
- `ForecastTool`: runs time-series or machine learning forecasts
- `BacktestTool`: tests simple strategies or hypotheses
- `RiskAnalyzer`: identifies risks, uncertainty, and conflicting evidence
- `ReportGenerator`: produces a structured final report

Agent-focused interview talking points:

- how the agent decides which tools to call
- how retrieved evidence is attached to the final answer
- how the system avoids unsupported investment claims
- why the system presents risk-aware analysis instead of deterministic predictions
- how tool outputs are normalized for the LLM
- how agent runs are logged and evaluated

## 6. Recommended Fusion Architecture

The recommended final architecture is a fusion:

> Spring Boot provides the product and backend platform. The AI agent provides the core financial analysis workflow.

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

This lets the project speak to both job types:

- For Java backend interviews, present it as a Spring Boot financial analysis platform.
- For AI agent interviews, present it as a tool-using equity research agent.
- For full-stack or product-oriented interviews, present it as an end-to-end AI financial research application.

## 7. Recommended Technical Stack

Backend:

- Java 17 or 21
- Spring Boot
- Spring Web
- Spring Data JPA
- PostgreSQL
- Redis
- Spring Scheduler or a lightweight job queue

AI and agent layer:

- LangChain4j, Spring AI, or a custom lightweight agent orchestration layer
- OpenAI-compatible LLM API or another LLM provider
- vector database such as pgvector, Qdrant, or Chroma
- structured JSON tool-call contracts

Data and analysis:

- market data API
- news API
- financial filings or company fundamentals API
- forecasting service, either in Java or a Python microservice

Frontend:

- React or Vue
- dashboard with query input, report view, charts, watchlist, and job status

Deployment:

- Docker Compose for local development
- separate services for backend, database, Redis, vector database, and optional Python forecasting service

## 8. Core User Workflow

Example user query:

> Analyze NVIDIA's opportunities and risks over the next month.

System flow:

1. User submits an analysis request.
2. Backend creates an async analysis job.
3. Agent planner decomposes the request into subtasks.
4. Tool router calls market data, news, filings, forecast, and backtest tools as needed.
5. Evidence aggregator normalizes tool outputs.
6. Risk analyzer identifies bullish evidence, bearish evidence, uncertainty, and missing data.
7. Report generator creates a structured research report.
8. Backend stores the report and returns it to the dashboard.

## 9. Report Structure

Each generated report should include:

- executive summary
- recent price and volume behavior
- key technical indicators
- news and sentiment summary
- fundamental or filing highlights if available
- forecast output with confidence or uncertainty
- backtest result if a strategy is tested
- bullish factors
- bearish factors
- risk warnings
- final non-advisory conclusion

The report should avoid direct investment advice such as "buy this stock." It should use research-oriented language such as:

- "The evidence suggests..."
- "Main upside factors include..."
- "Main risks include..."
- "This conclusion is uncertain because..."

## 10. MVP Scope

The first version should be intentionally focused.

MVP features:

- stock ticker search
- market data fetch
- technical indicators
- AI-generated research report
- report history
- async job status
- basic dashboard

MVP agent tools:

- market data tool
- indicator tool
- news summary tool
- report generator

MVP backend features:

- REST APIs
- PostgreSQL persistence
- Redis cache
- async analysis job
- basic error handling

MVP should not include every possible feature. The goal is to build a solid platform foundation first.

## 11. Later Extensions

Good extension directions:

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

Suggested multi-agent extension:

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

This should be added after the single-agent MVP works. Starting with too many agents would add complexity before the product value is proven.

## 12. Implementation Bias

The recommended balance is:

> Start with 70% Java backend engineering and 30% AI agent capability. Later evolve toward 50% backend and 50% AI agent.

Reason:

- The developer already has Java backend learning experience.
- A strong backend foundation makes the project credible for traditional roles.
- Agent features can be layered on gradually.
- The project can still follow the hiring trend toward AI application development.

## 13. Suggested Repository Structure

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

If the first implementation is backend-only, the repository can start simpler:

```text
equity_research_agent/
  src/main/java/...
  src/test/java/...
  docs/
  pom.xml
  README.md
```

The multi-folder structure is better if a frontend or Python forecasting service will be added early.

## 14. Implementation Roadmap

Phase 1: Backend foundation

- create Spring Boot project
- design core entities: stock, analysis job, report, tool call record
- implement REST APIs for creating analysis jobs and reading reports
- add PostgreSQL persistence
- add Redis cache for market data

Phase 2: Basic agent workflow

- implement a simple single-agent orchestrator
- define tool input and output DTOs
- add market data and technical indicator tools
- generate a structured research report from tool results
- persist tool-call traces for debugging and interview explanation

Phase 3: Product dashboard

- create a simple frontend dashboard
- support natural language query input
- show async job status
- render generated report and charts
- show report history

Phase 4: Research depth

- add news retrieval and summarization
- add financial filing or fundamentals retrieval
- add RAG if document data is available
- improve report evidence grounding

Phase 5: Advanced extensions

- add forecasting tool
- add backtesting tool
- add portfolio or watchlist analysis
- add scheduled reports or alerts
- optionally split forecasting into a Python microservice

The recommended first implementation target is Phase 1 plus a minimal part of Phase 2. That gives the project a working backend and a visible agent capability without becoming too large too early.

## 15. Architecture Decision for the First Build

For the first build, use a single Spring Boot application.

Inside that application, keep the agent layer as a separate package or module:

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

This avoids premature microservices while still keeping boundaries clear. A Python forecasting microservice can be added later only if the forecasting logic becomes too awkward to maintain in Java.

## 16. Resume Description

Possible resume title:

> Equity Research Agent: Java-based Multi-Agent Financial Analysis Platform

Possible resume bullet:

> Built a Java Spring Boot equity research platform that integrates market data, news analysis, forecasting tools, and LLM-based agent workflows to generate structured, risk-aware stock analysis reports.

Expanded version:

> Designed and implemented an AI-powered financial research system with async analysis jobs, external market data integrations, Redis caching, PostgreSQL persistence, and an agent orchestration layer for tool calling, evidence aggregation, and report generation.

AI-focused version:

> Developed a tool-using AI agent that decomposes stock research queries, retrieves market and news data, invokes forecasting and backtesting tools, and generates evidence-grounded investment research reports with explicit risk analysis.

Backend-focused version:

> Built a Spring Boot backend for an AI financial research platform, including REST APIs, async job processing, PostgreSQL data modeling, Redis caching, external API integration, and report history management.

## 17. Success Criteria

The project is successful if it can demonstrate:

- a user can submit a natural language stock analysis request
- the backend creates and tracks an analysis job
- the agent calls multiple tools instead of only producing generic LLM text
- the final report includes evidence, uncertainty, and risk analysis
- reports are persisted and viewable later
- the system is explainable enough to discuss in interviews
- the architecture can be extended without rewriting the whole project

## 18. Key Design Decision

The core design decision is:

> Do not build a pure stock prediction app. Build a backend-driven equity research agent where prediction is only one tool in a broader analysis workflow.

This makes the project more credible, more extensible, and more aligned with both Java backend and AI agent application roles.
