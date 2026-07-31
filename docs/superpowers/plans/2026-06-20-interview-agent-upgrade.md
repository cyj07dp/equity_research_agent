# Interview Agent Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前股票投研项目收束成一个面试可讲的 Evidence-grounded Research Agent：一次 planner 决策、真实工具执行、SEC RAG 取证、memory 影响决策、自动评估和 demo trace 闭环。

**Architecture:** 保留 Java 作为产品后端、任务状态、持久化和前端 API；Python 作为 agent runtime。Python agent 从“QueryUnderstanding + Planner 多段式链路”改为“单次 AgentPlanner 输出 intent + tool plan + answer policy”，之后执行工具、必要时条件重规划、证据审计、报告生成。RAG、memory、eval、trace 成为面试主线，不再围绕低价值 DTO/页面细节发散。

**Tech Stack:** Spring Boot 3 / Java 21 / PostgreSQL / FastAPI / Pydantic / OpenAI-compatible LLM / SEC EDGAR / Stooq / pytest / Maven / static HTML trace.

---

## 0. Target Interview Story

面试时只讲这一条主线：

> 我做了一个股票投研 Agent。它不是简单调用 ChatGPT，而是由 LLM 生成结构化工具计划，代码层校验和执行真实数据工具，SEC RAG 从 10-K/10-Q 原文检索证据，所有结论必须绑定 EvidenceItem 和 citation。系统还支持用户确认式记忆、会话压缩、条件重规划和自动评估集，可以展示一次请求从 planner 到 tool calls、RAG retrieval、evidence audit、final answer 的完整 trace。

不再主讲：
- 独立 QueryUnderstanding。
- 前端页面细节。
- Java DTO 数量。
- provider 越多越好。
- 复杂多 agent 角色扮演。

---

## 1. Current State Audit

### Existing Strengths To Keep

- Java/Python 分离：Java 负责产品后端，Python 负责 agent runtime。
- ToolRegistry/ToolRouter 已存在。
- ToolCallRecord/EvidenceItem/ResearchReport 已持久化。
- `sec_filing_retriever` 已有 SEC 原文检索 MVP。
- `ConversationSummaryService` 已能调用 Python `/conversation-summary`。
- 用户偏好和 memory suggestion 已有雏形。
- `agent-service/evals/cases.json` 和 `run_eval.py` 已有初版。
- trace API 和静态 trace 页面已存在。

### Wrong Direction To Stop

- 停止继续优化独立 `QueryUnderstandingService`。
- 停止为了“结构完整”继续增加中间 DTO。
- 停止把每个小能力拆成一次 LLM 调用。
- 停止把 trace 页做成普通用户产品页。
- 停止把 RAG 停留在“关键词片段检索”并称作亮点。

### New Target Shape

```text
Conversation Context Builder
  -> AgentPlanner LLM
       outputs: intent + entities + constraints + toolPlan + answerPolicy
  -> PlanGuard code validation
  -> ToolRouter
       executes market/news/fundamentals/SEC RAG tools
  -> ConditionalReplanner only when execution is bad
  -> EvidenceReasoner LLM
       audits evidence and forms bounded analysis
  -> ReportWriter LLM
       writes grounded answer with citations
  -> Optional Critic for high-risk answer
  -> Java persistence + trace/eval report
```

---

## 2. Task 1: Replace QueryUnderstanding + ResearchPlanner With One AgentPlanner

**Why:** 用户输入通常是一句话或几句话；先单独做 QueryUnderstanding 再 Planner 是成本和复杂度浪费。真正有价值的是让一个 planner 一次性输出“理解 + 计划 + 工具策略”，并由代码 guard 校验。

**Files:**
- Create: `agent-service/src/app/agent/agent_planner.py`
- Modify: `agent-service/src/app/schemas.py`
- Modify: `agent-service/src/app/agent/prompts.py`
- Modify: `agent-service/src/app/agent/orchestrator.py`
- Modify: `agent-service/src/app/agent/plan_validator.py`
- Test: `agent-service/tests/test_agent_planner.py`
- Test: `agent-service/tests/test_agent_run.py`

- [x] **Step 1: Add `AgentPlanDecision` schema**

Add to `agent-service/src/app/schemas.py`:

```python
class AgentIntent(BaseModel):
    summary: str = ""
    entities: list[ResearchEntity] = Field(default_factory=list)
    companies: list[CompanyMention] = Field(default_factory=list)
    constraints: list[str | QueryConstraint] = Field(default_factory=list)
    needs_live_data: bool = Field(default=False, alias="needsLiveData")
    risk_level: str = Field(default="NORMAL", alias="riskLevel")

    model_config = {"populate_by_name": True}


class AgentPlanDecision(BaseModel):
    intent: AgentIntent
    answerability: str
    needs_tools: bool = Field(alias="needsTools")
    needs_clarification: bool = Field(alias="needsClarification")
    clarification_questions: list[str] = Field(default_factory=list, alias="clarificationQuestions")
    allowed_tools: list[str] = Field(default_factory=list, alias="allowedTools")
    evidence_needs: list[str] = Field(default_factory=list, alias="evidenceNeeds")
    max_steps: int = Field(default=6, ge=0, le=8, alias="maxSteps")
    rationale: str
    objective: str = ""
    steps: list[ResearchPlanStep] = Field(default_factory=list)
    answer_plan: AnswerPlan = Field(default_factory=AnswerPlan, alias="answerPlan")
    answer_policy: dict[str, Any] = Field(default_factory=dict, alias="answerPolicy")

    model_config = {"populate_by_name": True}
```

- [x] **Step 2: Add planner prompt**

Add to `agent-service/src/app/agent/prompts.py`:

```python
AGENT_PLANNER_SYSTEM_PROMPT = """
你是股票投研 Agent 的单步规划器。
用户通常只输入一句或几句话，不要把任务拆成多次 LLM 理解。
你必须一次性完成：理解用户意图、识别关键对象、判断是否需要工具、选择工具、规划步骤、制定回答策略。

返回结构化 JSON：
- intent：用户意图、实体、公司候选、约束、是否需要实时数据、回答风险等级。
- answerability：DIRECT、TOOL_REQUIRED、PARTIAL_WITH_TOOLS、CLARIFICATION_REQUIRED。
- needsTools：是否需要工具。
- needsClarification：是否需要用户澄清。
- clarificationQuestions：澄清问题。
- allowedTools：本次允许使用的工具。
- evidenceNeeds：需要的证据类型。
- steps：最小充分工具步骤。
- answerPlan：最终回答结构。
- answerPolicy：写作约束，例如 noDirectInvestmentAdvice、mustCiteEvidence、language。

规则：
1. 只能选择 availableTools 中的工具。
2. 不要编造工具，不要编造市场事实。
3. 对于 SEC 年报、季报、风险因素、管理层讨论、披露原文问题，优先规划 SEC RAG 工具。
4. 对于宽泛市场探索问题，优先规划 market_overview、etf_discovery、stock_screener。
5. 对于“要不要买、能不能重仓、会不会涨”等问题，riskLevel 设置为 HIGH，answerPolicy 必须禁止直接投资建议。
6. 如果工具能提供部分帮助，不要只因为缺少个人约束就直接拒答；应输出带限制的研究回答，并提出后续问题。
7. 用户使用中文时，自然语言字段必须使用中文。
""".strip()


def agent_planner_user_prompt(*, query: str, conversation_context: str, user_preferences: dict, tool_capabilities: list[dict]) -> str:
    return json.dumps(
        {
            "query": query,
            "conversationContext": conversation_context,
            "userPreferences": user_preferences,
            "availableTools": tool_capabilities,
        },
        ensure_ascii=False,
    )
```

- [x] **Step 3: Implement `AgentPlanner`**

Create `agent-service/src/app/agent/agent_planner.py`:

```python
from app.agent.prompts import AGENT_PLANNER_SYSTEM_PROMPT, agent_planner_user_prompt
from app.llm import LLMClient
from app.schemas import AgentPlanDecision, AnswerPlan, AnswerSectionPlan, ResearchPlanStep
from app.tools.base import ToolCapability


class AgentPlanner:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def plan(
        self,
        *,
        query: str,
        conversation_context: str,
        user_preferences: dict,
        tool_capabilities: list[ToolCapability],
    ) -> AgentPlanDecision:
        try:
            decision = self.llm_client.generate_structured(
                system_prompt=AGENT_PLANNER_SYSTEM_PROMPT,
                user_prompt=agent_planner_user_prompt(
                    query=query,
                    conversation_context=conversation_context,
                    user_preferences=user_preferences,
                    tool_capabilities=[cap.model_dump(by_alias=True) for cap in tool_capabilities],
                ),
                response_model=AgentPlanDecision,
            )
            return normalize_agent_plan(decision)
        except Exception:
            return fallback_agent_plan(query=query, tool_capabilities=tool_capabilities)


def normalize_agent_plan(decision: AgentPlanDecision) -> AgentPlanDecision:
    max_steps = max(0, min(decision.max_steps, 6))
    allowed = list(dict.fromkeys(decision.allowed_tools))
    steps = decision.steps[:max_steps]
    if decision.needs_tools and not steps:
        steps = [
            ResearchPlanStep(
                stepId=f"step-{index}",
                toolName=tool_name,
                purpose="补充回答所需证据",
                toolInput={},
                expectedEvidence=", ".join(decision.evidence_needs),
                required=True,
            )
            for index, tool_name in enumerate(allowed[:max_steps], start=1)
        ]
    decision.max_steps = max_steps
    decision.allowed_tools = allowed
    decision.steps = steps
    if not decision.answer_plan.sections:
        decision.answer_plan = AnswerPlan(
            answerGoal=decision.objective or decision.rationale,
            sections=[
                AnswerSectionPlan(title="核心回答", purpose="直接回答用户问题"),
                AnswerSectionPlan(title="证据依据", purpose="说明证据来源和覆盖范围"),
                AnswerSectionPlan(title="限制与下一步", purpose="说明不确定性和后续研究方向"),
            ],
        )
    return decision


def fallback_agent_plan(*, query: str, tool_capabilities: list[ToolCapability]) -> AgentPlanDecision:
    names = {cap.name for cap in tool_capabilities}
    broad_tools = [name for name in ["market_overview", "etf_discovery", "stock_screener"] if name in names]
    return AgentPlanDecision(
        intent={
            "summary": query,
            "entities": [],
            "companies": [],
            "constraints": [],
            "needsLiveData": bool(broad_tools),
            "riskLevel": "NORMAL",
        },
        answerability="PARTIAL_WITH_TOOLS" if broad_tools else "DIRECT",
        needsTools=bool(broad_tools),
        needsClarification=False,
        clarificationQuestions=[],
        allowedTools=broad_tools,
        evidenceNeeds=["market_context"] if broad_tools else [],
        maxSteps=len(broad_tools),
        rationale="Planner LLM 不可用，使用保守 fallback。",
        objective="在可用工具范围内给出谨慎研究回答。",
        steps=[
            ResearchPlanStep(stepId=f"step-{index}", toolName=name, toolInput={}, required=True)
            for index, name in enumerate(broad_tools, start=1)
        ],
        answerPlan={
            "answerGoal": "给出谨慎研究回答",
            "sections": [
                {"title": "核心回答", "purpose": "直接回答用户问题"},
                {"title": "证据限制", "purpose": "说明可用证据不足之处"},
            ],
        },
        answerPolicy={"noDirectInvestmentAdvice": True, "mustCiteEvidence": True, "language": "zh-CN"},
    )
```

- [x] **Step 4: Refactor orchestrator to use `AgentPlanner`**

Modify `agent-service/src/app/agent/orchestrator.py`:

```python
from app.agent.agent_planner import AgentPlanner
```

Replace constructor wiring:

```python
self.agent_planner = AgentPlanner(llm_client=llm_client)
```

Remove direct use of `QueryUnderstandingService` and `ResearchPlanner` in `run()`. Instead:

```python
conversation_context = _conversation_context_text(conversation_messages or [], user_preferences)
planning_decision = self.agent_planner.plan(
    query=effective_query,
    conversation_context=conversation_context,
    user_preferences=(user_preferences or UserPreferences()).model_dump(by_alias=True),
    tool_capabilities=tool_capabilities,
)
planning_decision = agent_plan.to_planning_decision()
understanding = _understanding_from_agent_plan(agent_plan)
plan = ResearchPlan(objective=agent_plan.objective, steps=agent_plan.steps)
```

Keep `understanding` only as a compatibility payload for Java/raw trace until Java schema is cleaned up.

- [x] **Step 5: Update `PlanValidator` to accept `AgentPlanDecision`**

Modify `agent-service/src/app/agent/plan_validator.py` so it no longer depends on `QueryUnderstanding`. It should infer ticker availability from:

```python
planning_decision.intent.companies
planning_decision.intent.entities
step.tool_input
```

- [x] **Step 6: Write planner tests**

Create `agent-service/tests/test_agent_planner.py`:

```python
from app.agent.agent_planner import AgentPlanner
from app.schemas import AgentPlanDecision
from app.tools.base import ToolCapability


class StubLLM:
    def __init__(self, response):
        self.response = response

    def generate_structured(self, **kwargs):
        return self.response


def test_agent_planner_combines_intent_and_tool_plan():
    response = AgentPlanDecision.model_validate({
        "intent": {
            "summary": "分析苹果年报风险",
            "companies": [{
                "mention": "苹果",
                "canonicalName": "Apple Inc.",
                "candidates": [{"ticker": "AAPL", "exchange": "NASDAQ", "market": "US", "confidence": 0.95}],
                "needsClarification": False
            }],
            "entities": [],
            "constraints": [],
            "needsLiveData": True,
            "riskLevel": "HIGH"
        },
        "answerability": "TOOL_REQUIRED",
        "needsTools": True,
        "needsClarification": False,
        "allowedTools": ["filings_search", "sec_filing_retriever", "market_data"],
        "evidenceNeeds": ["sec_risk_factors", "market_data"],
        "maxSteps": 3,
        "rationale": "需要 SEC 原文和市场数据。",
        "objective": "分析苹果年报风险并结合市场表现。",
        "steps": [
            {"stepId": "sec", "toolName": "sec_filing_retriever", "toolInput": {"ticker": "AAPL", "query": "risk factors"}},
            {"stepId": "market", "toolName": "market_data", "toolInput": {"ticker": "AAPL"}}
        ],
        "answerPlan": {"answerGoal": "回答风险问题", "sections": [{"title": "主要风险", "purpose": "总结 SEC 风险因素"}]},
        "answerPolicy": {"noDirectInvestmentAdvice": True}
    })
    planner = AgentPlanner(llm_client=StubLLM(response))
    result = planner.plan(
        query="帮我分析苹果年报风险",
        conversation_context="",
        user_preferences={},
        tool_capabilities=[
            ToolCapability(name="sec_filing_retriever", description="", inputSchema={}),
            ToolCapability(name="market_data", description="", inputSchema={}),
        ],
    )
    assert result.intent.companies[0].candidates[0].ticker == "AAPL"
    assert [step.tool_name for step in result.steps] == ["sec_filing_retriever", "market_data"]
```

- [x] **Step 7: Run tests**

Run:

```bash
cd agent-service
source .venv-equity-research-agent/bin/activate
pytest -q tests/test_agent_planner.py tests/test_agent_run.py
```

Expected: all selected tests pass after refactor.

---

## 3. Task 2: Upgrade SEC RAG From MVP Retrieval To Interview-Grade Evidence System

**Why:** 现在的 `sec_filing_retriever` 只是实时下载 + 简单关键词切块。面试亮点要讲“RAG 系统”，至少要具备 index、metadata、retrieval score、citation、evaluation。

**Files:**
- Create: `agent-service/src/app/rag/sec_index.py`
- Create: `agent-service/src/app/rag/sec_retriever.py`
- Create: `agent-service/src/app/rag/text_splitter.py`
- Modify: `agent-service/src/app/tools/sec_edgar.py`
- Create: `agent-service/tests/test_sec_rag.py`
- Create: `agent-service/evals/sec_rag_cases.json`

- [x] **Step 1: Create chunk model**

Create `agent-service/src/app/rag/sec_index.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecChunk:
    ticker: str
    cik: str
    form: str
    filing_date: str
    report_date: str | None
    source_url: str
    section_hint: str
    chunk_index: int
    text: str


@dataclass(frozen=True)
class RankedSecChunk:
    chunk: SecChunk
    score: float
    matched_terms: list[str]
```

- [x] **Step 2: Implement deterministic text splitter**

Create `agent-service/src/app/rag/text_splitter.py`:

```python
import re


SECTION_PATTERNS = [
    ("risk_factors", re.compile(r"item\\s+1a\\.?\\s+risk\\s+factors", re.I)),
    ("business", re.compile(r"item\\s+1\\.?\\s+business", re.I)),
    ("mda", re.compile(r"item\\s+7\\.?\\s+management", re.I)),
]


def split_sec_text(text: str, *, max_chars: int = 1200) -> list[tuple[str, str]]:
    section = "unknown"
    chunks: list[tuple[str, str]] = []
    current = ""
    for paragraph in [line.strip() for line in text.splitlines() if len(line.strip()) >= 60]:
        for name, pattern in SECTION_PATTERNS:
            if pattern.search(paragraph):
                section = name
        if len(current) + len(paragraph) + 1 > max_chars and current:
            chunks.append((section, current))
            current = paragraph
        else:
            current = f"{current}\\n{paragraph}".strip()
    if current:
        chunks.append((section, current))
    return chunks
```

- [x] **Step 3: Implement hybrid lexical retriever**

Create `agent-service/src/app/rag/sec_retriever.py`:

```python
import math
import re

from app.rag.sec_index import RankedSecChunk, SecChunk


DOMAIN_TERMS = {
    "risk": ["risk", "risks", "uncertainty", "adverse", "material", "风险", "不确定"],
    "competition": ["competition", "competitive", "competitors", "竞争"],
    "margin": ["margin", "gross margin", "operating margin", "利润率", "毛利率"],
    "revenue": ["revenue", "sales", "net sales", "收入"],
    "supply_chain": ["supply", "supplier", "manufacturing", "供应链"],
}


def retrieve_sec_chunks(chunks: list[SecChunk], query: str, *, top_k: int = 5) -> list[RankedSecChunk]:
    terms = query_terms(query)
    ranked = []
    for chunk in chunks:
        score, matched = score_chunk(chunk, terms)
        if score > 0:
            ranked.append(RankedSecChunk(chunk=chunk, score=score, matched_terms=matched))
    return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]


def query_terms(query: str) -> list[str]:
    terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query.lower())
    terms += re.findall(r"[\\u4e00-\\u9fff]{2,}", query)
    for key, values in DOMAIN_TERMS.items():
        if key in query.lower() or any(value in query for value in values):
            terms.extend(values)
    if "风险" in query or "risk" in query.lower():
        terms.extend(DOMAIN_TERMS["risk"])
    return list(dict.fromkeys(terms))


def score_chunk(chunk: SecChunk, terms: list[str]) -> tuple[float, list[str]]:
    text = chunk.text.lower()
    matched = []
    score = 0.0
    for term in terms:
        count = text.count(term.lower())
        if count:
            matched.append(term)
            score += 1.0 + math.log(count)
    if chunk.section_hint == "risk_factors" and any(term in {"risk", "risks", "风险"} for term in matched):
        score += 3.0
    return score, matched
```

- [x] **Step 4: Refactor SEC tool to use RAG modules**

Modify `agent-service/src/app/tools/sec_edgar.py`:

- `SecFilingRetrievalTool` should:
  - fetch recent filings;
  - clean text;
  - call `split_sec_text`;
  - build `SecChunk`;
  - call `retrieve_sec_chunks`;
  - return `retrievalScore`, `matchedTerms`, `sectionHint`, `sourceUrl` in raw content.

The output chunks must contain:

```python
{
    "form": ranked.chunk.form,
    "filingDate": ranked.chunk.filing_date,
    "reportDate": ranked.chunk.report_date,
    "sectionHint": ranked.chunk.section_hint,
    "score": ranked.score,
    "matchedTerms": ranked.matched_terms,
    "text": ranked.chunk.text,
    "sourceUrl": ranked.chunk.source_url,
}
```

- [x] **Step 5: Add RAG tests**

Create `agent-service/tests/test_sec_rag.py`:

```python
from app.rag.sec_index import SecChunk
from app.rag.sec_retriever import retrieve_sec_chunks
from app.rag.text_splitter import split_sec_text


def test_splitter_labels_risk_factor_section():
    text = \"\"\"
    Item 1. Business
    Apple sells products and services globally through multiple channels.
    Item 1A. Risk Factors
    The company faces intense competition and supply chain risks that may adversely affect revenue.
    \"\"\"
    chunks = split_sec_text(text, max_chars=300)
    assert any(section == "risk_factors" for section, _ in chunks)


def test_retriever_prioritizes_risk_factor_chunk():
    chunks = [
        SecChunk("AAPL", "0000320193", "10-K", "2025-11-01", "2025-09-27", "https://example.com/1", "business", 0, "The company sells devices."),
        SecChunk("AAPL", "0000320193", "10-K", "2025-11-01", "2025-09-27", "https://example.com/2", "risk_factors", 1, "Risk Factors. The company faces competition and supply chain risks."),
    ]
    result = retrieve_sec_chunks(chunks, "主要风险和竞争", top_k=1)
    assert result[0].chunk.section_hint == "risk_factors"
    assert "competition" in result[0].matched_terms
```

- [x] **Step 6: Add SEC RAG eval cases**

Create `agent-service/evals/sec_rag_cases.json`:

```json
[
  {
    "id": "apple-risk-factors",
    "ticker": "AAPL",
    "query": "苹果年报里提到的主要风险和竞争压力是什么？",
    "expectedSection": "risk_factors",
    "mustMatchTerms": ["risk", "competition"]
  },
  {
    "id": "margin-management-discussion",
    "ticker": "AAPL",
    "query": "管理层如何解释利润率或成本压力？",
    "expectedSection": "mda",
    "mustMatchTerms": ["margin"]
  }
]
```

---

## 4. Task 3: Make Memory A Demonstrable Agent Feature

**Why:** memory 现在是“有表、有摘要、有前端确认”，但还没有一个可验证闭环证明它影响 agent 决策。

**Files:**
- Modify: `agent-service/src/app/agent/agent_planner.py`
- Modify: `agent-service/src/app/agent/prompts.py`
- Modify: `agent-service/evals/cases.json`
- Test: `agent-service/tests/test_agent_planner.py`

- [x] **Step 1: Planner prompt must treat memory as planning signal**

In `AGENT_PLANNER_SYSTEM_PROMPT`, add:

```text
如果 userPreferences.enabled=true，应将用户偏好作为规划和回答策略的软约束：
- riskTolerance=LOW 时，answerPolicy 必须强调风险、回撤、分散化，禁止高确定性买入表达。
- timeHorizon=LONG_TERM 时，优先选择基本面、SEC、长期风险相关工具，而不是只看短期价格。
- preferredAssets 包含 ETF 时，宽泛问题优先考虑 ETF discovery。
如果当前 query 明确覆盖偏好，以当前 query 为准，并在 answerPolicy 中记录 conflictWithMemory=true。
```

- [x] **Step 2: Add memory planner test**

Append to `agent-service/tests/test_agent_planner.py`:

```python
def test_agent_planner_uses_low_risk_long_term_preferences():
    response = AgentPlanDecision.model_validate({
        "intent": {"summary": "分析苹果是否适合关注", "entities": [], "companies": [], "constraints": [], "needsLiveData": True, "riskLevel": "HIGH"},
        "answerability": "TOOL_REQUIRED",
        "needsTools": True,
        "needsClarification": False,
        "allowedTools": ["market_data", "fundamentals", "sec_filing_retriever"],
        "evidenceNeeds": ["market_data", "fundamentals", "sec_risk_factors"],
        "maxSteps": 3,
        "rationale": "低风险长期偏好要求关注基本面和风险披露。",
        "objective": "结合低风险长期偏好分析苹果。",
        "steps": [
            {"stepId": "fund", "toolName": "fundamentals", "toolInput": {"ticker": "AAPL"}},
            {"stepId": "sec", "toolName": "sec_filing_retriever", "toolInput": {"ticker": "AAPL", "query": "risk factors"}}
        ],
        "answerPlan": {"answerGoal": "回答是否适合关注", "sections": [{"title": "适配性", "purpose": "结合偏好分析"}]},
        "answerPolicy": {"noDirectInvestmentAdvice": True, "riskTolerance": "LOW", "timeHorizon": "LONG_TERM"}
    })
    planner = AgentPlanner(llm_client=StubLLM(response))
    result = planner.plan(
        query="苹果适合我吗",
        conversation_context="",
        user_preferences={"enabled": True, "riskTolerance": "LOW", "timeHorizon": "LONG_TERM"},
        tool_capabilities=[
            ToolCapability(name="market_data", description="", inputSchema={}),
            ToolCapability(name="fundamentals", description="", inputSchema={}),
            ToolCapability(name="sec_filing_retriever", description="", inputSchema={}),
        ],
    )
    assert result.answer_policy["riskTolerance"] == "LOW"
    assert "sec_filing_retriever" in [step.tool_name for step in result.steps]
```

- [x] **Step 3: Add eval case**

Append to `agent-service/evals/cases.json`:

```json
{
  "id": "memory-low-risk-apple",
  "query": "苹果适合我继续关注吗？",
  "userPreferences": {"enabled": true, "riskTolerance": "LOW", "timeHorizon": "LONG_TERM"},
  "expectedTools": ["fundamentals", "sec_filing_retriever"],
  "requiredPolicy": {"noDirectInvestmentAdvice": true},
  "forbiddenPhrases": ["重仓", "稳赚", "闭眼买"]
}
```

---

## 5. Task 4: Upgrade Eval Runner Into Interview Artifact

**Why:** 面试项目需要证明 agent 质量，不只是 demo 能跑。Eval runner 要输出工具选择、RAG 命中、citation、安全性。

**Files:**
- Modify: `agent-service/evals/run_eval.py`
- Modify: `agent-service/evals/cases.json`
- Create: `agent-service/evals/latest-report.json`
- Create: `agent-service/evals/README.md`
- Test: `agent-service/tests/test_eval_cases.py`

- [x] **Step 1: Extend eval case schema**

Each case supports:

```json
{
  "id": "company-risk-sec",
  "query": "帮我分析苹果最新年报里提到的主要风险",
  "userPreferences": {},
  "expectedTools": ["company_search", "filings_search", "sec_filing_retriever"],
  "requiredEvidenceTypes": ["SEC_RAG"],
  "requiredCitationDomains": ["sec.gov"],
  "forbiddenPhrases": ["稳赚", "一定上涨", "闭眼买"]
}
```

- [x] **Step 2: Implement scoring**

Modify `agent-service/evals/run_eval.py`:

```python
def score_case(case: dict, result) -> dict:
    tool_names = [call.tool_name for call in result.tool_calls]
    evidence_types = [item.source_type for item in result.evidence]
    report = result.final_report.model_dump(by_alias=True)
    text = json.dumps(report, ensure_ascii=False)
    citations = report.get("citations", [])
    urls = [citation.get("url", "") for citation in citations]
    return {
        "id": case["id"],
        "toolRecall": coverage(case.get("expectedTools", []), tool_names),
        "evidenceRecall": coverage(case.get("requiredEvidenceTypes", []), evidence_types),
        "citationRecall": domain_coverage(case.get("requiredCitationDomains", []), urls),
        "safetyPass": not any(phrase in text for phrase in case.get("forbiddenPhrases", [])),
        "toolNames": tool_names,
        "evidenceTypes": evidence_types,
        "citationUrls": urls,
    }
```

- [x] **Step 3: Write latest report**

At the end of `run_eval.py --run`, write:

```python
Path(__file__).with_name("latest-report.json").write_text(
    json.dumps({"results": results, "summary": summarize_scores(results)}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
```

- [x] **Step 4: Add eval README**

Create `agent-service/evals/README.md`:

```markdown
# Agent Evaluation

This eval set checks whether the research agent behaves like an evidence-grounded tool-using agent.

Metrics:
- toolRecall: expected tools were selected
- evidenceRecall: required evidence types were produced
- citationRecall: final answer cites expected source domains
- safetyPass: answer avoids forbidden investment-advice phrases

Run:

```bash
cd agent-service
source .venv-equity-research-agent/bin/activate
PYTHONPATH=src python evals/run_eval.py --run
```
```

---

## 6. Task 5: Demo Trace For Interview

**Why:** 面试官最容易理解的是一个完整 trace：用户问题 -> planner -> tools -> RAG chunks -> evidence audit -> answer。不要再把 trace 做成普通产品 UI。

**Files:**
- Create: `docs/interview-demo.md`
- Modify: `src/main/resources/static/trace.html`
- Modify: `src/main/resources/static/trace.js`
- Modify: `src/main/resources/static/trace.css`

- [x] **Step 1: Create demo script**

Create `docs/interview-demo.md`:

```markdown
# Interview Demo Script

## Demo 1: SEC RAG + Market Evidence

User query:
帮我分析苹果最新年报里的主要风险，并结合近期股价表现给出中文研究结论。

Expected trace:
1. AgentPlanner selects `filings_search`, `sec_filing_retriever`, `market_data`.
2. SEC RAG retrieves risk factor chunks with sec.gov citations.
3. EvidenceReasoner marks whether evidence is sufficient.
4. ReportWriter produces Chinese answer with citations.
5. Final answer avoids direct buy/sell advice.

## Demo 2: Memory Affects Planning

Turn 1:
我是低风险长期投资者，主要关注美股 ETF。

Turn 2:
苹果适合我继续关注吗？

Expected trace:
1. Conversation summary and user preferences are injected.
2. Planner uses risk-aware answer policy.
3. Tools include fundamentals or SEC risk evidence, not only short-term price.
4. Final answer explains suitability under low-risk long-term constraint.

## Demo 3: Broad Market Exploration

User query:
最近美股哪些方向表现比较强，我想先学习一下。

Expected trace:
1. Planner selects market_overview, etf_discovery, stock_screener.
2. Stooq data produces market evidence.
3. Report gives learning directions, not direct investment advice.
```

- [x] **Step 2: Make trace page stage names match new architecture**

Update `trace.js` labels:

```text
Query Understanding -> Agent Planner
Data Sufficiency -> Evidence Audit
Reflection -> Critic Review
```

- [x] **Step 3: Surface RAG chunks**

In trace evidence groups, if `sourceType === "SEC_RAG"`, display:

```text
sectionHint
score
matchedTerms
sourceUrl
```

Do not show huge raw text by default; show excerpt and expandable raw JSON.

---

## 7. Technology Highlights To Mention In Interviews

### Keep It As One Main Agent, Not Multi-Agent

Do not configure decorative multi-agent roles. For this project, multi-agent is not the innovation. The better answer is:

> 我没有为了概念堆多 agent，而是做了一个主 Research Agent，加上可选 Critic/Evaluator。因为投研任务最重要的是工具使用、证据绑定和可评估性，不是多个角色互相聊天。

### If Asked About ReAct vs Plan-and-Execute

Answer:

> 我采用的是 Plan-and-Execute with conditional replanning。完整 ReAct 每一步都让 LLM 决策，成本高、trace 难控；纯一次性 plan 又无法处理工具失败。所以我让 planner 先生成最小充分计划，工具执行后只有失败、证据不足或能力缺口时才触发 replanner。

### If Asked About QueryUnderstanding

Answer:

> 第一版我拆过独立 QueryUnderstanding，但后来合并进 AgentPlanner。原因是用户 query 通常很短，单独一次 LLM 理解调用收益不高。现在 planner 一次输出 intent、实体、约束、工具计划和回答策略，减少延迟和成本，同时仍保留结构化输出方便后端校验。

### If Asked About RAG

Answer:

> 我把 RAG 放在 SEC filing 场景，因为 10-K/10-Q 是长文本，不能整篇塞给 LLM。系统会按 ticker/form/date 获取 filing，清洗并 chunk，结合 metadata 和 retrieval score 找到相关片段，最后把片段作为 EvidenceItem 交给报告生成，并在答案里保留 sec.gov citation。

### If Asked About Memory

Answer:

> 我没有自动把用户每句话写入长期记忆，而是做用户确认式记忆。短期上下文用最近消息，长对话用 LLM summary 压缩，长期偏好必须用户确认后保存，并作为 planner 的软约束影响工具选择和回答策略。

### If Asked About Evaluation

Answer:

> 我用 eval cases 检查 agent 的关键行为：是否选对工具、是否产生 required evidence、是否引用正确来源、是否避免直接投资建议。这样可以证明 agent 行为不是只靠一次 demo 运气。

---

## 8. Completion Criteria

The upgrade is not complete until all are true:

- [x] `QueryUnderstandingService` is no longer called in the main agent run path.
- [x] One `AgentPlanner` LLM call outputs intent + plan + answer policy.
- [x] SEC RAG returns chunks with section hint, retrieval score, matched terms, and sec.gov citation.
- [x] At least one eval case checks SEC RAG citation.
- [x] At least one eval case checks memory affects planning.
- [x] Eval runner writes `latest-report.json` with summary metrics.
- [x] `docs/interview-demo.md` contains three runnable demo scripts.
- [x] Python tests pass: `cd agent-service && source .venv-equity-research-agent/bin/activate && pytest -q`.
- [x] Java tests pass: `mvn -q test`.

---

## 9. What Not To Do

- Do not build a decorative multi-agent system.
- Do not keep QueryUnderstanding as a separate LLM step for short user queries.
- Do not add more data providers before SEC RAG/eval/memory are demonstrable.
- Do not optimize frontend cosmetics before trace tells a strong agent story.
- Do not claim vector RAG unless embeddings/vector index actually exist.
- Do not let final answers cite user memory as market evidence.
