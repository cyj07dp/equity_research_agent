# Equity Research Agent V3 Agent-First 设计文档

日期：2026-06-03

## 1. 核心结论

项目方向正式调整为：

> Java Spring Boot Backend + Python Agent Service 的双服务架构。Java 后端负责产品化 API、任务管理、持久化和查询；Python Agent Service 负责真正的 Agent 核心业务，包括自然语言理解、公司识别、规划、MCP / tool calling、证据聚合、报告生成和自我校验。

这个方向比纯 Java workflow 更符合项目目标。核心业务不是高并发 CRUD，而是一个能通过工具自主完成公开市场公司研究的 AI Agent。

## 2. 为什么从 V2 调整到 V3

V2 的设计重点是 Spring Boot 后端闭环：

```text
ticker
  -> async research job
  -> fake tools
  -> evidence aggregation
  -> deterministic report
```

这个方向适合搭后端底座，但还不够像真正的 Agent 应用。主要问题：

- 用户仍需要理解 `ticker`。
- 工具调用流程基本固定。
- 没有真正的 query understanding。
- 没有 company resolver。
- 没有 research planner。
- 没有 MCP / external tools 的清晰接入点。
- agent trace 还不够表达“思考、计划、观察、校验”的过程。

V3 的重点改为 agent-first：

```text
natural language query
  -> query understanding
  -> company resolver
  -> research planner
  -> MCP / tools
  -> evidence store
  -> citation-aware report
  -> critic / validator
  -> backend persistence
```

## 3. 产品目标

用户不需要知道股票代码，只需要输入自然语言问题。

示例：

```json
{
  "query": "帮我分析一下 Palantir 最近的增长机会和主要风险"
}
```

系统应该自动完成：

```text
Palantir
  -> Palantir Technologies Inc.
  -> PLTR
  -> NYSE
  -> 机会与风险分析
  -> 生成研究计划
  -> 调用工具检索证据
  -> 生成带引用的结构化 research memo
```

项目目标不是做一个聊天机器人，而是做一个可追溯的 AI 投研 Agent。

## 4. 总体架构

```text
Client / Frontend / curl
        |
Spring Boot Backend
  - API 入口
  - agent run / job 管理
  - PostgreSQL 持久化
  - report 查询
  - trace 查询
  - 用户侧产品框架
        |
HTTP JSON
        |
Python Agent Service
  - query understanding
  - company resolver
  - research planner
  - MCP / tool calling
  - evidence aggregation
  - report generation
  - critic / validator
        |
External Tools
  - web search
  - company symbol search
  - market data APIs
  - financial statement APIs
  - news APIs
  - SEC filings
  - LLM APIs
  - MCP servers
```

## 5. 服务边界

### Java Spring Boot Backend

Java 后端负责系统工程和产品化外壳：

- 对外提供 REST API。
- 创建 agent run / research job。
- 调用 Python Agent Service。
- 保存 agent 返回的 plan、tool calls、evidence、validation、report。
- 提供 report 查询 API。
- 提供 agent trace 查询 API。
- 后续扩展用户系统、权限、历史记录和 dashboard。

Java 不负责复杂 agent 推理，不直接做 MCP orchestration。

### Python Agent Service

Python 服务负责真正的 Agent 核心业务：

- 理解自然语言 query。
- 识别研究对象和上市公司。
- 解析 ticker、exchange、company profile。
- 根据用户问题生成 research plan。
- 调用 MCP 或其他 external tools。
- 聚合、清洗、压缩 evidence。
- 生成 citation-aware report。
- 使用 critic / validator 检查报告质量。
- 将完整 agent result 返回给 Java 后端。

Python 第一版不直接写 PostgreSQL，由 Java 统一落库。

## 6. 为什么核心 Agent 用 Python

不是因为 Java 不能做 Agent，而是因为 Python 更适合快速构建 Agent 核心业务。

Python 的优势：

- LangGraph、LangChain、LlamaIndex、AutoGen 等生态更成熟。
- MCP client、tool adapters、retrieval、embedding、document parsing 更容易集成。
- Agent prompt、tool schema、规划策略和 validator 可以更快迭代。
- 金融数据处理、文本处理和文档处理库更丰富。

Java 的价值仍然很强：

- 稳定 API。
- 类型清晰的业务模型。
- PostgreSQL 持久化。
- 任务状态管理。
- 产品级后端框架。
- 后续权限、用户、历史记录、dashboard 支撑。

面试讲法：

> 我将 AI Agent runtime 和 Java 后端解耦。Spring Boot 服务负责 API、任务管理、持久化和 trace 查询；Python Agent Service 负责 planning、tool use、MCP integration、retrieval、report generation 和 validation。这让系统既有后端工程能力，也能充分利用 Python Agent 生态。

## 7. 通信方式

第一版使用 HTTP JSON。

Java 调用 Python：

```http
POST /agent-runs
Content-Type: application/json

{
  "runId": "uuid",
  "query": "帮我分析一下 Palantir 最近的增长机会和主要风险",
  "locale": "zh-CN"
}
```

Python 返回：

```json
{
  "runId": "uuid",
  "query": "帮我分析一下 Palantir 最近的增长机会和主要风险",
  "company": {
    "name": "Palantir Technologies Inc.",
    "ticker": "PLTR",
    "exchange": "NYSE",
    "confidence": 0.94,
    "source": "company-symbol-search"
  },
  "intent": "OPPORTUNITY_RISK_ANALYSIS",
  "plan": [
    {
      "step": 1,
      "tool": "company_search",
      "reason": "识别用户问题中的上市公司"
    }
  ],
  "toolCalls": [],
  "evidence": [],
  "report": {},
  "validation": {}
}
```

后续如果任务耗时变长，可以升级为：

- Java 创建 run。
- Python 异步执行。
- Java 轮询或接收 callback。
- 或引入 message queue。

第一版不需要过早引入消息队列。

## 8. Agent MVP 必须达到的水准

V3 的 MVP 不以“后端功能多”为目标，而以“Agent 能力真实”为目标。

至少应实现：

1. **自然语言输入**

   用户输入 `query`，不要求用户提供 `ticker`。

2. **Company Resolver**

   能从自然语言中识别公司，并解析为标准上市公司信息：

   ```text
   companyName
   ticker
   exchange
   confidence
   source
   ```

   不能只靠硬编码。可以有 local aliases，但真实运行应支持 external search / financial API / MCP tool。

3. **Research Planner**

   根据用户问题生成研究计划。不同问题应有不同 plan。

   例如：

   - 机会与风险分析：news、market data、fundamentals、filings。
   - 财务状况分析：fundamentals、financial statements、filings。
   - 近期新闻分析：news、price movement、market reaction。

4. **Tool Calling / MCP Integration**

   至少抽象以下工具：

   - `CompanySearchTool`
   - `MarketDataTool`
   - `NewsSearchTool`
   - `FilingSearchTool`
   - `FinancialStatementTool`
   - `WebSearchTool`

   第一版可以部分使用 fake 或 simple implementation，但架构必须允许 MCP / external tools 接入。

5. **Evidence Store**

   所有工具返回都先转成 evidence，不直接塞进最终报告。

   每条 evidence 至少包含：

   ```text
   sourceType
   sourceName
   sourceUrl
   title
   summary
   publishedAt / observedAt
   relevance
   confidence
   rawContent
   ```

6. **Citation-Aware Report**

   报告中的关键结论必须能追溯到 evidence。

   报告结构至少包含：

   - 公司识别结果
   - 用户问题理解
   - 执行计划摘要
   - 关键结论
   - 机会因素
   - 风险因素
   - 财务 / 市场 / 新闻证据
   - 不确定性
   - 引用来源
   - 非投资建议声明

7. **Critic / Validator**

   报告生成后必须校验：

   - 是否有 unsupported claims。
   - 是否缺少 citations。
   - 是否有直接投资建议。
   - 是否使用了过时数据。
   - 是否明确说明 missing data。
   - 是否把事实和推测混在一起。

8. **Agent Trace**

   必须能查询完整 agent run trace：

   ```text
   query
   parsed intent
   company resolution
   plan
   tool calls
   observations
   evidence
   draft report
   validation result
   final report
   ```

## 9. MVP API

Java 后端对外暴露：

```http
POST /api/agent-runs
GET /api/agent-runs/{runId}
GET /api/agent-runs/{runId}/trace
GET /api/reports/{reportId}
```

创建 agent run：

```json
{
  "query": "帮我分析一下英伟达最近的机会和风险"
}
```

响应：

```json
{
  "runId": "uuid",
  "status": "PENDING"
}
```

查询 trace：

```json
{
  "runId": "uuid",
  "query": "帮我分析一下英伟达最近的机会和风险",
  "company": {},
  "intent": "OPPORTUNITY_RISK_ANALYSIS",
  "plan": [],
  "toolCalls": [],
  "evidence": [],
  "validation": {},
  "reportId": "uuid"
}
```

## 10. 数据持久化原则

第一版由 Java 后端统一写 PostgreSQL。

原因：

- 数据一致性更清楚。
- Java 是对外系统的主控服务。
- Python Agent Service 可以保持 stateless，更容易替换和扩展。
- 后续如果 agent 服务失败，Java 可以保存失败状态和错误信息。

Python 返回完整 `AgentRunResult`，Java 保存：

- agent run
- company resolution
- research plan
- tool calls
- evidence items
- validation result
- final report
- raw agent result JSON

PostgreSQL 中应继续使用 `jsonb` 保存半结构化 trace。

## 11. 推荐仓库结构

建议调整为：

```text
equity_research_agent/
  backend/
    pom.xml
    src/main/java/...
    src/test/java/...
  agent-service/
    pyproject.toml
    src/
      app/
        main.py
        agent/
        tools/
        schemas/
        validators/
    tests/
  docs/
    superpowers/specs/
    technical-notes/
  docker-compose.yml
  README.md
```

当前已有 Java 代码可以后续迁移到 `backend/`。不要立即做大量移动，先完成 v3 计划，再执行迁移。

## 12. 当前已有代码如何处理

当前 Java 代码有价值，但定位要调整：

保留思想：

- async job / run 管理
- PostgreSQL persistence
- tool-call trace
- report retrieval API
- evidence model

需要重构：

- `ticker` 输入改为 `query` 输入。
- `ResearchJob` 概念升级为 `AgentRun`。
- Java 内部 fake agent workflow 改为调用 Python Agent Service。
- `ResearchAgentOrchestrator` 不再作为核心 agent，最多保留为 fallback / test stub。
- report / trace 数据结构扩展为 agent-first。

## 13. 实现阶段

### Phase 0：文档和架构调整

- 新建 v3 agent-first spec。
- 标记 v2 spec 和旧 plan 已被 v3 取代。
- 重新制定实现计划。

### Phase 1：Python Agent Service 最小闭环

- 创建 FastAPI 服务。
- 实现 `POST /agent-runs`。
- 接收自然语言 query。
- 实现 query interpreter。
- 实现 company resolver。
- 实现 planner。
- 使用 fake / simple tools 生成 evidence。
- 生成结构化 report。
- 返回完整 `AgentRunResult`。

### Phase 2：Java Backend 调用 Python Agent

- Java API 改为 `POST /api/agent-runs`。
- Java 调用 Python Agent Service。
- Java 保存完整 agent result。
- Java 提供 trace 和 report 查询。

### Phase 3：MCP / External Tools

- 接入 web search / company search / news search MCP 或 API。
- 增加 tool abstraction。
- 保留 fake tools 用于测试。

### Phase 4：LLM Report Writer 和 Validator

- 增加 LLM-based report generation。
- 增加 citation validation。
- 增加 unsupported claim detection。
- 增加 missing data warning。

### Phase 5：面试展示打磨

- README 中文化并展示双服务架构。
- 增加 sample agent trace。
- 增加 sample report。
- 增加架构图和设计取舍说明。

## 14. 暂不优先考虑的内容

在 Agent MVP 稳定前，不优先做：

- 高并发优化
- 用户系统
- portfolio
- watchlist
- scheduled reports
- 完整前端 dashboard
- Redis cache
- Kubernetes deployment

这些是产品后续阶段，不是当前核心业务。

## 15. 成功标准

V3 成功标准：

- 用户只输入自然语言 query。
- Agent 能识别公司和 ticker。
- Agent 能生成 research plan。
- Agent 能调用至少两个真实或可替换的工具。
- 工具输出被标准化为 evidence。
- 报告有 citation 和 risk / uncertainty。
- Validator 能指出 unsupported / missing / non-advisory 问题。
- Java 后端能保存并查询完整 trace。
- README 能清楚解释 Java + Python 双服务架构。

## 16. 关键设计原则

1. **Agent 能力优先**

   项目首先要像一个真正的 Agent 应用，而不是普通 CRUD 后端。

2. **Java 做产品化外壳**

   Java 负责 API、任务、持久化、查询和系统边界。

3. **Python 做 Agent 核心**

   Python 负责 LLM、MCP、tool calling、retrieval、planning 和 validation。

4. **工具结果先进入 evidence**

   任何工具输出都不应直接拼进报告，必须先标准化为 evidence。

5. **trace 是核心资产**

   面试展示时，trace 比最终报告更能体现 agent 工程能力。

6. **先可解释，再自动化**

   第一版 planner 和 validator 可以部分 rule-based，但结构必须支持后续 LLM / MCP 增强。
