# Equity Research Agent Plan-and-Solve 设计文档

日期：2026-06-04

## 1. 核心结论

当前项目的 Agent 设计应从“固定 workflow + 少量 LLM extraction”调整为：

> Plan-and-Solve 主流程 + Structured Tool Calling + One-pass Reflection。

LLM 不应该只负责公司名抽取和意图分类。它应该承担投研 Agent 的核心认知职责：

- 理解用户真实研究问题。
- 根据可用工具生成研究计划。
- 决定每一步需要什么证据。
- 基于证据进行分析和综合。
- 生成结构化投研 memo。
- 对报告做一次质量反思和修正。

这个设计仍然保留 Java Spring Boot + Python Agent Service 的双服务架构。Java 负责产品化 API、任务管理、持久化和查询；Python 负责 Agent runtime、LLM 推理、工具调用和报告生成。

## 2. 为什么当前方向需要修正

当前 Python Agent Service 已经具备初步模块边界：

```text
query interpreter
  -> company resolver
  -> research planner
  -> tools
  -> report writer
  -> validator
```

但这个流程仍然太像传统后端 workflow：

- `QueryInterpreter` 只输出一个粗粒度 intent。
- `CompanyResolver` 主要解决实体识别，不解决研究对象和工具能力之间的关系。
- `ResearchPlanner` 根据 enum 写死工具调用顺序。
- LLM 的作用停留在结构化抽取，没有主导规划、推理和综合。
- 工具设计围绕已有代码，而不是围绕用户真实投研问题。
- 报告生成更多是模板拼接，不是证据约束下的分析。

因此，继续在现有 workflow 上小修小补会让项目偏离“AI Agent 应用”的目标。正确方向应该先从用户问题、Agent 能力和工具系统重新设计。

## 3. 目标用户和真实问题

第一版目标用户不是专业买方研究员，而是：

- 想快速理解上市公司的个人投资者。
- 希望学习 AI Agent 项目开发的开发者。
- 面试或项目评审中希望看到 Agent 思路和工程落地的人。

典型问题不是“给我查 ticker”，而是：

```text
单公司投资判断：
- 英伟达现在还能不能买？
- 苹果现在估值贵不贵？
- Palantir 的增长逻辑还成立吗？

公司对比：
- 特斯拉和比亚迪谁更有长期优势？
- 英伟达和 AMD 哪个风险更大？

财报和基本面：
- 这家公司现金流质量怎么样？
- 最近财报有什么隐患？
- 毛利率变化说明了什么？

新闻和催化剂：
- 最近下跌是因为什么？
- 近期有什么利好和利空？
- 市场对这次财报反应是否过度？

研究报告：
- 帮我生成一份简洁的投研 memo。
- 帮我总结机会、风险、估值和不确定性。
```

Agent 的设计应该从这些问题倒推，而不是从已有 fake tools 倒推。

## 4. Agent 设计模式选择

### 4.1 不采用纯 ReAct 作为第一版主流程

ReAct 的模式是：

```text
Thought -> Action -> Observation -> Thought -> Action -> Observation ...
```

它适合开放探索型任务，例如复杂网页检索、多轮工具试探、未知路径问题。

但投研 Agent 的第一版不适合用纯 ReAct 作为主循环：

- 投研工具类型相对明确。
- 输出报告结构相对明确。
- 后续接真实 API 后需要控制成本和调用次数。
- 工具调用 trace 需要清晰可解释。
- 无限或半开放循环会增加调试难度。
- 模型可能为了“继续思考”调用不必要工具。

所以第一版不应该做完全开放的 ReAct loop。

### 4.2 主流程采用 Plan-and-Solve

Plan-and-Solve 更适合当前项目：

```text
User Query
  -> Understand
  -> Plan
  -> Execute Tools
  -> Reason Over Evidence
  -> Draft Report
  -> Reflect
  -> Final Report
```

关键是：研究计划由 LLM 根据用户问题和可用工具生成，而不是由代码根据 intent enum 写死。

例如用户问：

```text
英伟达现在还能不能买？
```

Planner 应生成类似计划：

```json
{
  "objective": "判断 NVIDIA 当前投资吸引力、主要机会和风险",
  "steps": [
    {
      "stepId": "company-resolution",
      "toolName": "company_search",
      "purpose": "确认研究对象、ticker、交易所和可能歧义",
      "required": true
    },
    {
      "stepId": "market-context",
      "toolName": "market_data",
      "purpose": "查看近期价格表现、波动和市场预期变化",
      "required": true
    },
    {
      "stepId": "fundamental-review",
      "toolName": "financials",
      "purpose": "分析收入增长、利润率、现金流和估值压力",
      "required": true
    },
    {
      "stepId": "news-catalysts",
      "toolName": "news_search",
      "purpose": "识别近期催化剂、风险事件和市场叙事",
      "required": true
    },
    {
      "stepId": "valuation-check",
      "toolName": "valuation",
      "purpose": "判断估值是否已经充分反映增长预期",
      "required": false
    }
  ]
}
```

这让 LLM 从“字段抽取器”变成“研究规划者”。

### 4.3 Reflection 作为质量控制，不做无限循环

第一版采用 one-pass Reflection：

```text
Draft Report
  -> Reflection / Critic
  -> Revised Final Report
```

Reflection 检查：

- 是否有没有 evidence 支撑的判断。
- 是否直接给出投资建议。
- 是否过度确定。
- 是否遗漏关键数据。
- 是否忽略公司/ticker 歧义。
- 是否把工具不可用或 fake/simple data 当成真实结论。
- 引用、风险、不确定性是否完整。

第一版最多修订一次，不做无限反思循环。

## 5. 总体架构

```text
Client / Frontend / curl
        |
Spring Boot Backend
  - API 入口
  - agent run / job 管理
  - PostgreSQL 持久化
  - report 查询
  - trace 查询
        |
HTTP JSON
        |
Python Agent Service
  - QueryUnderstanding
  - ResearchPlanner
  - ToolRouter
  - EvidenceCollector
  - ReasoningEngine
  - ReportWriter
  - ReflectionValidator
        |
LLM Layer
  - OpenAI-compatible client
  - structured output
  - prompt templates
        |
Tool Layer
  - company_search
  - market_data
  - financials
  - news_search
  - filings_search
  - valuation
  - peer_comparison
```

Java 不直接参与 Agent 推理。Python 返回完整结果，包括 plan、tool calls、evidence、analysis、reflection 和 final report，由 Java 落库。

## 6. Python Agent Service 模块

建议重构为：

```text
agent-service/src/app/
  agent/
    orchestrator.py
    query_understanding.py
    research_planner.py
    tool_router.py
    reasoning_engine.py
    report_writer.py
    reflection_validator.py
  llm/
    client.py
    prompts/
      query_understanding.py
      research_planning.py
      evidence_reasoning.py
      report_generation.py
      reflection.py
  tools/
    base.py
    registry.py
    company_search.py
    market_data.py
    financials.py
    news_search.py
    filings_search.py
    valuation.py
    peer_comparison.py
  schemas.py
```

### 6.1 QueryUnderstanding

职责：

- 理解用户问题。
- 抽取公司、证券、市场、时间范围。
- 判断是单公司、对比、财报、新闻、估值还是综合投研。
- 识别用户是否要求实时信息。
- 识别输出偏好：简洁回答、完整 memo、对比表、风险清单。

输出示例：

```json
{
  "taskType": "INVESTMENT_THESIS",
  "companies": [
    {
      "mention": "英伟达",
      "canonicalName": "NVIDIA Corporation",
      "candidates": [
        {
          "ticker": "NVDA",
          "exchange": "NASDAQ",
          "market": "US",
          "confidence": 0.97
        }
      ],
      "needsClarification": false
    }
  ],
  "timeHorizon": "medium_term",
  "requiresLiveData": true,
  "outputStyle": "research_memo",
  "confidence": 0.93
}
```

### 6.2 ResearchPlanner

职责：

- 接收 query understanding 和可用工具列表。
- 生成结构化 ResearchPlan。
- 每一步说明目的、工具、输入参数、期望 evidence。
- 避免调用无关工具。
- 标记 required / optional。

Planner 必须知道工具能力，而不是凭空计划。输入中应包含 tool registry 的摘要：

```json
{
  "availableTools": [
    {
      "name": "market_data",
      "description": "Fetch price, volume, volatility and relative performance.",
      "inputSchema": {}
    }
  ]
}
```

### 6.3 ToolRouter

职责：

- 根据 ResearchPlan 调用工具。
- 校验 tool input。
- 记录 tool call trace。
- 将工具输出标准化为 EvidenceItem。
- 工具失败时返回失败 evidence 或 missing data，而不是直接中断整个 run。

ToolRouter 不做复杂推理。它是执行层。

### 6.4 ReasoningEngine

职责：

- 让 LLM 基于 evidence 做分析。
- 不允许凭空补充工具未提供的事实。
- 输出 thesis、supporting points、risks、missing data、uncertainty。
- 对单公司分析和公司对比使用不同 reasoning schema。

Reasoning prompt 的核心约束：

> Use only the supplied evidence. If evidence is insufficient, say what is missing.

### 6.5 ReportWriter

职责：

- 将 reasoning 和 evidence 组织成投研 memo。
- 报告应该包含：
  - question understanding
  - company summary
  - key findings
  - opportunities
  - risks
  - valuation / financial notes when available
  - evidence summary
  - uncertainty
  - citations
  - non-advisory statement

### 6.6 ReflectionValidator

职责：

- 对 draft report 做一次 critique。
- 输出是否需要修订、问题列表和修订建议。
- ReportWriter 根据 reflection 生成 final report。

Reflection 不负责重新调用工具。缺数据时应标注 missing data，而不是编造。

## 7. 工具设计

工具应该围绕用户投研问题设计，而不是围绕当前已有类设计。

### 7.1 company_search

输入：

```json
{
  "query": "英伟达",
  "markets": ["US", "HK", "CN"]
}
```

输出：

```json
{
  "candidates": [
    {
      "name": "NVIDIA Corporation",
      "ticker": "NVDA",
      "exchange": "NASDAQ",
      "market": "US",
      "confidence": 0.97
    }
  ],
  "ambiguities": []
}
```

### 7.2 market_data

用途：

- 价格表现。
- 成交量。
- 波动率。
- 相对指数表现。
- 近期市场反应。

### 7.3 financials

用途：

- 收入。
- 毛利率。
- 营业利润。
- 净利润。
- 现金流。
- 资产负债。
- 估值倍数。

### 7.4 news_search

用途：

- 近期新闻。
- 产品、监管、管理层、竞争、宏观事件。
- 新闻影响摘要。
- 来源和发布时间。

### 7.5 filings_search

用途：

- 10-K / 10-Q / annual report / interim report。
- 风险因素。
- 管理层讨论。
- 关键财务表述。

### 7.6 valuation

用途：

- 简单倍数估值。
- 同业估值比较。
- 敏感性分析。
- 明确估值假设和局限。

### 7.7 peer_comparison

用途：

- 多公司业务对比。
- 财务质量对比。
- 增长和风险对比。
- 估值对比。

## 8. Prompt 分层

Prompt 应按 Agent 职责分层，而不是把所有要求写进一个大 prompt。

### 8.1 Query Understanding Prompt

目标：

- 理解用户想问什么。
- 输出结构化 query understanding。
- 识别公司、任务类型、时间范围、输出需求、歧义。

不做：

- 不生成最终报告。
- 不调用工具。
- 不做投资结论。

### 8.2 Research Planning Prompt

目标：

- 基于用户问题和可用工具生成研究计划。
- 每一步必须对应已注册工具。
- 每一步说明为什么需要该 evidence。

不做：

- 不虚构工具。
- 不直接回答用户。

### 8.3 Evidence Reasoning Prompt

目标：

- 基于工具 evidence 做分析。
- 形成 thesis、supporting points、risks、missing data。

核心约束：

- 只使用 evidence。
- 证据不足时明确说不足。
- 不输出投资建议。

### 8.4 Report Generation Prompt

目标：

- 将 reasoning 转成结构化投研 memo。
- 保持引用、风险和不确定性。

### 8.5 Reflection Prompt

目标：

- 检查 draft report。
- 找出 unsupported claims、missing data、overconfidence、compliance risk。
- 给出修订建议。

## 9. 核心 Schema 草案

```python
class AgentRunResult(BaseModel):
    run_id: UUID
    query: str
    understanding: QueryUnderstanding
    plan: ResearchPlan
    tool_calls: list[ToolCallResult]
    evidence: list[EvidenceItem]
    reasoning: AnalystReasoning
    draft_report: ResearchReport
    reflection: ReflectionResult
    final_report: ResearchReport


class QueryUnderstanding(BaseModel):
    task_type: ResearchTaskType
    companies: list[CompanyMention]
    time_horizon: str
    requires_live_data: bool
    output_style: str
    clarification_questions: list[str]
    confidence: float


class ResearchPlan(BaseModel):
    objective: str
    steps: list[ResearchPlanStep]


class ResearchPlanStep(BaseModel):
    step_id: str
    tool_name: str
    purpose: str
    tool_input: dict
    expected_evidence: str
    required: bool


class AnalystReasoning(BaseModel):
    thesis: str
    supporting_points: list[str]
    risks: list[str]
    valuation_notes: list[str]
    missing_data: list[str]
    uncertainty: str


class ReflectionResult(BaseModel):
    passed: bool
    unsupported_claims: list[str]
    missing_data: list[str]
    overconfident_statements: list[str]
    revision_instructions: list[str]
```

## 10. 第一阶段 MVP 边界

第一阶段目标：把 Plan-and-Solve 主链路跑通，而不是接满真实金融数据。

必须支持：

- 自然语言 query。
- LLM query understanding。
- LLM research planning。
- Tool registry 和 tool router。
- 至少支持单公司分析。
- 工具接口按真实工具设计。
- 工具可以先是 simple implementation，但输出必须走标准 EvidenceItem。
- LLM evidence reasoning。
- LLM report drafting。
- one-pass reflection。
- 默认值兜底。

暂不支持：

- 无限 ReAct loop。
- 完整多 Agent 协作。
- 自动交易建议。
- 完整 DCF 模型。
- 完整多市场数据质量保证。
- 长期记忆。
- 用户账户和权限。

## 11. 单 Agent 到多 Agent 的演进

第一阶段使用单 Agent：

```text
ResearchAgent
  -> understand
  -> plan
  -> execute tools
  -> reason
  -> write report
  -> reflect
```

第二阶段再拆多 Agent：

```text
PlannerAgent
DataCollectorAgent
FinancialAnalystAgent
NewsAnalystAgent
ValuationAgent
ReportAgent
CriticAgent
```

拆分条件：

- 单 Agent prompt 变得过长。
- 财务分析、新闻分析、估值分析需要独立 prompt 和 schema。
- 工具调用出现复杂重试和探索。
- 多公司对比需要并行收集和独立分析。

## 12. 什么时候局部引入 ReAct

ReAct 不作为第一版主流程，但可以后续局部使用。

适合局部 bounded ReAct 的场景：

- 新闻搜索结果不足，需要换关键词。
- filing 里没找到关键内容，需要继续检索。
- 用户问题开放，需要先探索行业背景。
- 工具失败，需要选择替代工具。

局部 ReAct 必须有边界：

- 最大工具调用次数。
- 最大迭代轮数。
- 只在某个 ResearchPlanStep 内使用。
- 输出仍回到标准 EvidenceItem。

## 13. 对现有代码的影响

应替换或重构：

- `query_interpreter.py`
  - 从 intent classifier 升级为 `query_understanding.py`。

- `company_resolver.py`
  - 不再是独立主流程第一步，而是 query understanding 和 company_search 工具的一部分。

- `planner.py`
  - 从 enum-based hardcoded planner 升级为 LLM `research_planner.py`。

- `tools/fake_tools.py`
  - 拆成独立工具模块和 registry。

- `report_writer.py`
  - 从模板拼接升级为 LLM report drafting。

- `validator.py`
  - 升级为 deterministic checks + LLM reflection 的组合。

应保留：

- FastAPI service 边界。
- OpenAI-compatible LLM client。
- Pydantic structured schema。
- Tool call trace 思路。
- EvidenceItem 思路。
- Java/Python 双服务边界。

## 14. 推荐实施顺序

1. 定义新 schema：
   - QueryUnderstanding
   - ResearchPlan
   - ResearchPlanStep
   - AnalystReasoning
   - ReflectionResult

2. 新增 prompt 分层：
   - query understanding
   - research planning
   - evidence reasoning
   - report generation
   - reflection

3. 实现 ToolRegistry 和 ToolRouter。

4. 把现有 fake/simple tools 包装成标准工具。

5. 实现 planner-led orchestrator。

6. 实现 evidence reasoning 和 report drafting。

7. 实现 one-pass reflection。

8. 更新 API 返回结构和测试。

## 15. 最终定位

这个项目应该被描述为：

> 一个基于 Plan-and-Solve 的投研 Agent。系统先理解用户自然语言研究问题，再由 LLM 基于可用工具生成研究计划，按计划调用市场、财务、新闻和公告工具，聚合 evidence 后进行证据约束推理，生成结构化 research memo，并通过一次 reflection 检查 unsupported claims、missing data 和过度确定性。Java 后端负责产品化和持久化，Python Agent Service 负责 LLM runtime 和工具编排。

这比“固定 workflow + LLM 抽取公司名”更接近真正的 AI Agent 应用。
