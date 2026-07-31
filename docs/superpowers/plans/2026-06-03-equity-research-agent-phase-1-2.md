# Equity Research Agent Phase 1-2 实现计划

> **给 agentic workers 的要求：** 实现本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`。任务使用 checkbox（`- [ ]`）跟踪。

> 状态：已被 V3 Agent-First 架构取代。本文保留作为历史实现计划，后续不应继续按本计划扩展后端 workflow，而应重新制定 Java Backend + Python Agent Service 的实现计划。

**目标：** 构建第一条可运行的后端闭环：Maven + Java 21 + Spring Boot、Docker Compose PostgreSQL、异步 research job、fake agent tools、report persistence 和 tool-call trace APIs。

**架构：** 使用单个 Spring Boot 应用。第一版 agent 采用 deterministic workflow：`ResearchJobService` 创建异步任务，`ResearchAgentOrchestrator` 调用 fake tools，`EvidenceAggregator` 标准化工具结果，`ReportGenerator` 生成结构化报告，repository 负责持久化 job、report、evidence 和 tool-call traces。

**技术栈：** Java 21、Maven、Spring Boot 3.x、Spring Web、Spring Data JPA、PostgreSQL、Flyway、JUnit 5。

---

## 范围

本计划实现 V2 spec 中的 Phase 1 和 Phase 2：

- Maven Spring Boot 项目骨架
- Docker Compose 本地 PostgreSQL
- job、report、tool-call、evidence 领域模型
- async research job API
- fake market data、fundamentals、news tools
- deterministic report generation
- report 和 tool-call retrieval APIs
- 核心行为测试

本计划不实现真实外部 API、真实 LLM、前端 UI、Redis、RAG、forecasting 或 backtesting。

## 文件结构

创建或维护以下文件：

- `pom.xml`：Maven build、Java 21、Spring Boot dependencies。
- `docker-compose.yml`：本地 PostgreSQL service。
- `.env.example`：数据库配置示例。
- `src/main/resources/application.yml`：Spring datasource 和应用配置。
- `src/main/resources/db/migration/V1__init_schema.sql`：初始 PostgreSQL schema。
- `src/main/java/com/yjc/equityresearch/EquityResearchApplication.java`：应用入口。
- `src/main/java/com/yjc/equityresearch/domain/*.java`：job、report、tool-call、evidence 实体和枚举。
- `src/main/java/com/yjc/equityresearch/repository/*.java`：JPA repository。
- `src/main/java/com/yjc/equityresearch/api/*.java`：REST controllers。
- `src/main/java/com/yjc/equityresearch/api/dto/*.java`：request / response DTOs。
- `src/main/java/com/yjc/equityresearch/application/*.java`：应用服务边界。
- `src/main/java/com/yjc/equityresearch/config/AsyncConfig.java`：异步执行器配置。
- `src/main/java/com/yjc/equityresearch/agent/**/*.java`：agent workflow、fake tools、report generator。
- `src/test/java/com/yjc/equityresearch/**/*.java`：行为测试。

## 任务 1：项目骨架和 PostgreSQL Compose

**文件：**

- 创建：`pom.xml`
- 创建：`docker-compose.yml`
- 创建：`.env.example`
- 创建：`src/main/resources/application.yml`
- 创建：`src/main/java/com/yjc/equityresearch/EquityResearchApplication.java`

- [x] **Step 1：创建 Maven Spring Boot 项目文件**

使用 Java 21、Spring Boot 3，并加入 Web、JPA、Validation、Flyway、PostgreSQL 和 Test dependencies。

- [x] **Step 2：添加 PostgreSQL Docker Compose**

使用官方镜像：

```yaml
image: postgres:16
```

本地数据库配置：

```text
database: equity_research
username: equity_user
password: equity_password
port: 5432
```

- [x] **Step 3：添加本地配置示例**

`.env.example` 包含：

```dotenv
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/equity_research
SPRING_DATASOURCE_USERNAME=equity_user
SPRING_DATASOURCE_PASSWORD=equity_password
```

- [x] **Step 4：添加 Spring 配置**

`application.yml` 使用 PostgreSQL、JPA validate 和 Flyway migration。

- [x] **Step 5：添加应用入口**

`EquityResearchApplication` 使用 `@SpringBootApplication` 和 `@EnableAsync`。

## 任务 2：领域模型和数据库 Schema

**文件：**

- 创建：`src/main/resources/db/migration/V1__init_schema.sql`
- 创建：`ResearchJob`
- 创建：`ResearchJobStatus`
- 创建：`ResearchReport`
- 创建：`ToolCallRecord`
- 创建：`ToolCallStatus`
- 创建：`EvidenceItem`
- 创建：四个 repository

- [x] **Step 1：编写 schema migration**

创建 `research_jobs`、`research_reports`、`tool_call_records` 和 `evidence_items`。对 raw report / tool payload 使用 PostgreSQL `jsonb`。

- [x] **Step 2：实现 JPA entities**

实体与 migration 对齐，并保留领域状态转换方法，例如 `markRunning`、`markSucceeded`、`markFailed`。

- [x] **Step 3：实现 repositories**

使用 Spring Data JPA，支持按 `jobId` 查询 report、tool calls 和 evidence。

- [ ] **Step 4：数据库启动验证**

待 Maven 可用后运行：

```bash
docker compose up -d postgres
mvn test
```

预期：

- PostgreSQL container healthy。
- Flyway migration 成功。
- Maven test phase 通过。

## 任务 3：Evidence Aggregation TDD

**文件：**

- 创建：`src/test/java/com/yjc/equityresearch/agent/EvidenceAggregatorTest.java`
- 创建：`src/main/java/com/yjc/equityresearch/agent/EvidenceAggregator.java`
- 创建：`src/main/java/com/yjc/equityresearch/agent/tools/ToolResult.java`

- [x] **Step 1：编写 aggregation 测试**

测试 market、fundamentals、news tool results 能被转换成标准化 `EvidenceItem`，包含 source type、title、summary、source name 和 confidence。

- [ ] **Step 2：运行测试确认 RED**

当前环境没有 `mvn`，待本机 Maven 可用后运行：

```bash
mvn -Dtest=EvidenceAggregatorTest test
```

- [x] **Step 3：实现最小 aggregator**

创建 `ToolResult` record 和 `EvidenceAggregator`。

- [ ] **Step 4：运行测试确认 GREEN**

```bash
mvn -Dtest=EvidenceAggregatorTest test
```

## 任务 4：Deterministic Report Generation TDD

**文件：**

- 创建：`src/test/java/com/yjc/equityresearch/agent/report/ReportGeneratorTest.java`
- 创建：`src/main/java/com/yjc/equityresearch/agent/report/ReportGenerator.java`

- [x] **Step 1：编写 report generator 测试**

测试 ticker、company name 和 evidence list 能生成包含 executive summary、market snapshot、fundamental highlights、recent news、bullish factors、bearish factors、risk factors、uncertainty、non-advisory conclusion 和 raw JSON 的报告。

- [ ] **Step 2：运行测试确认 RED**

```bash
mvn -Dtest=ReportGeneratorTest test
```

- [x] **Step 3：实现 deterministic report generator**

第一版不调用真实 LLM，而是根据 evidence 生成稳定结构化报告。

- [ ] **Step 4：运行测试确认 GREEN**

```bash
mvn -Dtest=ReportGeneratorTest test
```

## 任务 5：Fake Tools 和 Orchestrator

**文件：**

- 创建：`ResearchTool`
- 创建：`FakeMarketDataTool`
- 创建：`FakeFundamentalsTool`
- 创建：`FakeNewsTool`
- 创建：`ResearchAgentOrchestrator`
- 创建：`ResearchWorkflowResult`

- [x] **Step 1：编写 orchestrator 测试**

测试 orchestrator 会调用三个 fake tools，并返回 report、三条 evidence 和三条 tool-call records。

- [ ] **Step 2：运行测试确认 RED**

```bash
mvn -Dtest=ResearchAgentOrchestratorTest test
```

- [x] **Step 3：实现 fake tools**

对 `AAPL`、`NVDA`、`TSLA` 返回 deterministic fixture，对其他 ticker 返回 generic fallback。

- [x] **Step 4：实现 orchestrator**

固定顺序调用 tools，聚合 evidence，生成 report，并返回 workflow result。

- [ ] **Step 5：运行测试确认 GREEN**

```bash
mvn -Dtest=ResearchAgentOrchestratorTest test
```

## 任务 6：Async Job Service 和 APIs

**文件：**

- 创建：`AsyncConfig`
- 创建：`ResearchJobService`
- 创建：`ReportService`
- 创建：`ResearchJobController`
- 创建：`ReportController`
- 创建：`api/dto/*.java`

- [x] **Step 1：编写 service workflow 测试**

测试 job 从 `PENDING` 进入处理流程后，最终保存 report、evidence、tool-call records，并将 job 标记为 `SUCCEEDED`。

- [ ] **Step 2：运行测试确认 RED**

```bash
mvn -Dtest=ResearchJobServiceTest test
```

- [x] **Step 3：实现 job service**

实现 ticker validation、job creation、async processing、status transitions、report persistence、evidence persistence 和 tool-call persistence。

- [x] **Step 4：实现 controllers 和 DTOs**

暴露接口：

- `POST /api/research-jobs`
- `GET /api/research-jobs/{jobId}`
- `GET /api/research-jobs/{jobId}/tool-calls`
- `GET /api/reports/{reportId}`

- [ ] **Step 5：运行 service test 和完整测试**

```bash
mvn test
```

## 任务 7：README 和手动 Demo

**文件：**

- 创建：`README.md`

- [x] **Step 1：编写 README**

README 包含：

- 项目定位
- 架构图
- prerequisites
- PostgreSQL startup command
- Maven test command
- run command
- API examples
- current limitations
- next roadmap

- [ ] **Step 2：运行手动 demo**

待 Maven 可用后运行：

```bash
docker compose up -d postgres
mvn spring-boot:run
```

然后调用：

```bash
curl -X POST http://localhost:8080/api/research-jobs \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"NVDA"}'
```

预期：

- 响应包含 `jobId` 和 `PENDING` 或 `RUNNING`。
- 轮询 job 后最终返回 `SUCCEEDED`。
- report endpoint 返回结构化报告。
- tool-call endpoint 返回三条工具调用记录。

## 当前验证状态

已经验证：

```bash
docker compose config
```

结果：通过，说明 `docker-compose.yml` 语法有效。

尚未验证：

```bash
mvn test
```

原因：当前执行环境没有 `mvn` 命令。需要在本机安装 Maven 后运行。

## 自查

Spec 覆盖情况：

- Maven + Java 21：Task 1。
- PostgreSQL through Docker Compose：Task 1。
- async research jobs：Task 6。
- fake tools and deterministic workflow：Tasks 3-5。
- report persistence and tool-call trace persistence：Tasks 2 and 6。
- API demo path：Tasks 6-7。

有意延期：

- real external APIs
- real LLM integration
- Redis cache
- frontend
- RAG
- Spring Boot app Dockerfile

实现不应直接在 `master` 上继续推进。当前使用分支：

```text
codex/phase-1-2-backend-skeleton
```
