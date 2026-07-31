# Agent Service Plan-and-Solve Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Python `agent-service` 从固定 workflow 改造成 Plan-and-Solve 主流程：LLM 理解问题、生成研究计划、按计划调用工具、基于 evidence 推理、生成报告，并做 one-pass reflection。

**Architecture:** 保留 FastAPI 服务边界和 OpenAI-compatible LLM client。新增 QueryUnderstanding、ResearchPlanner、ToolRegistry/ToolRouter、ReasoningEngine、ReflectionValidator 等模块；现有 fake/simple tools 先包装成标准工具，后续再替换为真实金融数据工具。

**Tech Stack:** Python 3.11、FastAPI、Pydantic v2、OpenAI-compatible Chat Completions、pytest。

---

## File Structure

Create:

- `agent-service/src/app/agent/query_understanding.py`
  - LLM 语义理解层，输出 `QueryUnderstanding`。

- `agent-service/src/app/agent/research_planner.py`
  - LLM 研究规划层，基于 understanding 和 tool registry 生成 `ResearchPlan`。

- `agent-service/src/app/agent/tool_router.py`
  - 按 plan 调用工具，记录 `ToolCallResult`，收集 `EvidenceItem`。

- `agent-service/src/app/agent/reasoning_engine.py`
  - LLM 基于 evidence 输出 `AnalystReasoning`。

- `agent-service/src/app/agent/reflection_validator.py`
  - LLM/规则组合检查 draft report，输出 `ReflectionResult`。

- `agent-service/src/app/tools/registry.py`
  - 注册工具、导出 planner 可读的 tool capabilities。

- `agent-service/tests/test_query_understanding.py`
  - 覆盖 LLM understanding 和默认兜底。

- `agent-service/tests/test_research_planner.py`
  - 覆盖 planner 使用工具能力生成计划和默认兜底。

- `agent-service/tests/test_tool_router.py`
  - 覆盖 router 按 plan 调工具、跳过未知工具。

- `agent-service/tests/test_plan_and_solve_agent_run.py`
  - 覆盖端到端 Plan-and-Solve 主链路。

Modify:

- `agent-service/src/app/schemas.py`
  - 新增 Plan-and-Solve schema。

- `agent-service/src/app/agent/prompts.py`
  - 拆分/新增 understanding、planning、reasoning、report、reflection prompts。

- `agent-service/src/app/agent/orchestrator.py`
  - 从固定 workflow 改为 Plan-and-Solve 编排。

- `agent-service/src/app/agent/report_writer.py`
  - 从模板拼接改为支持 LLM draft + reflection revision；第一步可保留 deterministic fallback。

- `agent-service/src/app/tools/base.py`
  - 扩展工具接口，使工具声明 name、description、input schema。

- `agent-service/src/app/tools/fake_tools.py`
  - 适配新 tool interface。

- `agent-service/tests/test_agent_run.py`
  - 更新断言，验证 `understanding`、`reasoning`、`reflection`、`finalReport`。

- `agent-service/tests/test_api.py`
  - 更新 API 返回结构断言。

---

## Task 1: Add Plan-and-Solve Schemas

**Files:**

- Modify: `agent-service/src/app/schemas.py`
- Test: `agent-service/tests/test_plan_and_solve_schemas.py`

- [ ] **Step 1: Write schema tests**

Create `agent-service/tests/test_plan_and_solve_schemas.py`:

```python
from uuid import UUID

from app.schemas import (
    AgentRunResult,
    AnalystReasoning,
    CompanyCandidate,
    CompanyMention,
    EvidenceItem,
    QueryUnderstanding,
    ReflectionResult,
    ResearchPlan,
    ResearchPlanStep,
    ResearchReport,
    ToolCallResult,
)


def test_plan_and_solve_result_schema_accepts_full_agent_trace():
    understanding = QueryUnderstanding.model_validate(
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
                            "confidence": 0.97,
                        }
                    ],
                    "needsClarification": False,
                    "ambiguityReason": None,
                }
            ],
            "timeHorizon": "medium_term",
            "requiresLiveData": True,
            "outputStyle": "research_memo",
            "clarificationQuestions": [],
            "confidence": 0.93,
        }
    )
    plan = ResearchPlan(
        objective="判断 NVIDIA 当前投资吸引力",
        steps=[
            ResearchPlanStep(
                stepId="market-context",
                toolName="market_data",
                purpose="查看近期市场表现",
                toolInput={"ticker": "NVDA"},
                expectedEvidence="近期价格、成交量和波动",
                required=True,
            )
        ],
    )
    reasoning = AnalystReasoning(
        thesis="证据支持谨慎乐观，但估值风险需要单独标注。",
        supportingPoints=["市场表现显示关注度较高。"],
        risks=["估值对增长预期敏感。"],
        valuationNotes=[],
        missingData=[],
        uncertainty="当前 evidence 仍不完整。",
    )
    reflection = ReflectionResult(
        passed=True,
        unsupportedClaims=[],
        missingData=[],
        overconfidentStatements=[],
        revisionInstructions=[],
    )
    report = ResearchReport(
        title="NVIDIA 投研 Agent Memo",
        companySummary="NVIDIA Corporation 是本次研究对象。",
        questionUnderstanding="用户关注 NVIDIA 当前投资吸引力。",
        keyFindings=["证据支持谨慎分析。"],
        opportunities=["增长预期仍是主要机会。"],
        risks=["估值风险较高。"],
        evidenceSummary="市场数据、新闻和基本面 evidence 已聚合。",
        uncertainty="当前工具数据仍有限。",
        citations=["https://example.com/market/NVDA"],
        nonAdvisoryStatement="本报告为 AI Agent 生成的研究摘要，不构成投资建议。",
    )
    result = AgentRunResult(
        runId=UUID("00000000-0000-0000-0000-000000000000"),
        query="英伟达还能不能买？",
        locale="zh-CN",
        understanding=understanding,
        plan=plan,
        toolCalls=[],
        evidence=[],
        reasoning=reasoning,
        draftReport=report,
        reflection=reflection,
        finalReport=report,
    )

    assert result.understanding.task_type == "INVESTMENT_THESIS"
    assert result.plan.steps[0].tool_name == "market_data"
    assert result.final_report.title == "NVIDIA 投研 Agent Memo"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_plan_and_solve_schemas.py -q
```

Expected: FAIL because `QueryUnderstanding`, `ResearchPlan`, `AnalystReasoning`, `ReflectionResult`, and new `AgentRunResult` fields do not exist yet.

- [ ] **Step 3: Add schema models**

Modify `agent-service/src/app/schemas.py`:

```python
class ResearchTaskType(StrEnum):
    INVESTMENT_THESIS = "INVESTMENT_THESIS"
    COMPANY_OVERVIEW = "COMPANY_OVERVIEW"
    FINANCIAL_HEALTH = "FINANCIAL_HEALTH"
    RECENT_NEWS = "RECENT_NEWS"
    COMPANY_COMPARISON = "COMPANY_COMPARISON"


class CompanyMention(BaseModel):
    mention: str
    canonical_name: str = Field(alias="canonicalName")
    candidates: list[CompanyCandidate]
    needs_clarification: bool = Field(alias="needsClarification")
    ambiguity_reason: str | None = Field(default=None, alias="ambiguityReason")

    model_config = {"populate_by_name": True}


class QueryUnderstanding(BaseModel):
    task_type: ResearchTaskType = Field(alias="taskType")
    companies: list[CompanyMention]
    time_horizon: str = Field(alias="timeHorizon")
    requires_live_data: bool = Field(alias="requiresLiveData")
    output_style: str = Field(alias="outputStyle")
    clarification_questions: list[str] = Field(alias="clarificationQuestions")
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = {"populate_by_name": True}


class ResearchPlanStep(BaseModel):
    step_id: str = Field(alias="stepId")
    tool_name: str = Field(alias="toolName")
    purpose: str
    tool_input: dict[str, Any] = Field(alias="toolInput")
    expected_evidence: str = Field(alias="expectedEvidence")
    required: bool

    model_config = {"populate_by_name": True}


class ResearchPlan(BaseModel):
    objective: str
    steps: list[ResearchPlanStep]


class AnalystReasoning(BaseModel):
    thesis: str
    supporting_points: list[str] = Field(alias="supportingPoints")
    risks: list[str]
    valuation_notes: list[str] = Field(alias="valuationNotes")
    missing_data: list[str] = Field(alias="missingData")
    uncertainty: str

    model_config = {"populate_by_name": True}


class ReflectionResult(BaseModel):
    passed: bool
    unsupported_claims: list[str] = Field(alias="unsupportedClaims")
    missing_data: list[str] = Field(alias="missingData")
    overconfident_statements: list[str] = Field(alias="overconfidentStatements")
    revision_instructions: list[str] = Field(alias="revisionInstructions")

    model_config = {"populate_by_name": True}
```

Update `AgentRunResult` to include:

```python
understanding: QueryUnderstanding
reasoning: AnalystReasoning
draft_report: ResearchReport = Field(alias="draftReport")
reflection: ReflectionResult
final_report: ResearchReport = Field(alias="finalReport")
```

Keep `company` and `intent` only if backward compatibility is still needed by Java. If kept, mark them as derived fields.

- [ ] **Step 4: Run schema test**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_plan_and_solve_schemas.py -q
```

Expected: PASS.

---

## Task 2: Implement QueryUnderstanding

**Files:**

- Create: `agent-service/src/app/agent/query_understanding.py`
- Modify: `agent-service/src/app/agent/prompts.py`
- Test: `agent-service/tests/test_query_understanding.py`

- [ ] **Step 1: Write failing tests**

Create `agent-service/tests/test_query_understanding.py`:

```python
from app.agent.query_understanding import QueryUnderstandingService
from app.schemas import QueryUnderstanding, ResearchTaskType


class StubLLMClient:
    def __init__(self, response):
        self.response = response

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_query_understanding_uses_llm_semantics():
    llm_response = QueryUnderstanding.model_validate(
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
                            "confidence": 0.97,
                        }
                    ],
                    "needsClarification": False,
                    "ambiguityReason": None,
                }
            ],
            "timeHorizon": "medium_term",
            "requiresLiveData": True,
            "outputStyle": "research_memo",
            "clarificationQuestions": [],
            "confidence": 0.94,
        }
    )
    service = QueryUnderstandingService(llm_client=StubLLMClient(llm_response))

    result = service.understand("英伟达现在还能不能买？")

    assert result.task_type == ResearchTaskType.INVESTMENT_THESIS
    assert result.companies[0].candidates[0].ticker == "NVDA"


def test_query_understanding_returns_default_when_llm_fails():
    service = QueryUnderstandingService(llm_client=StubLLMClient(RuntimeError("LLM unavailable")))

    result = service.understand("随便看看")

    assert result.task_type == ResearchTaskType.INVESTMENT_THESIS
    assert result.companies == []
    assert result.confidence == 0.1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_query_understanding.py -q
```

Expected: FAIL because `QueryUnderstandingService` does not exist.

- [ ] **Step 3: Add prompt constants**

Modify `agent-service/src/app/agent/prompts.py`:

```python
QUERY_UNDERSTANDING_SYSTEM_PROMPT = """
You are the query understanding layer for an equity research agent.
Understand the user's real research need before any tool planning.

Return structured JSON with:
- taskType
- companies
- timeHorizon
- requiresLiveData
- outputStyle
- clarificationQuestions
- confidence

Do not generate a research plan.
Do not write the final report.
Do not invent facts that require tools.
""".strip()


def query_understanding_user_prompt(query: str) -> str:
    return f"User query:\\n{query}"
```

- [ ] **Step 4: Implement service**

Create `agent-service/src/app/agent/query_understanding.py`:

```python
from app.agent.prompts import QUERY_UNDERSTANDING_SYSTEM_PROMPT, query_understanding_user_prompt
from app.llm import LLMClient
from app.schemas import QueryUnderstanding, ResearchTaskType


class QueryUnderstandingService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def understand(self, query: str) -> QueryUnderstanding:
        try:
            return self.llm_client.generate_structured(
                system_prompt=QUERY_UNDERSTANDING_SYSTEM_PROMPT,
                user_prompt=query_understanding_user_prompt(query),
                response_model=QueryUnderstanding,
            )
        except Exception:
            return QueryUnderstanding(
                taskType=ResearchTaskType.INVESTMENT_THESIS,
                companies=[],
                timeHorizon="unspecified",
                requiresLiveData=True,
                outputStyle="research_memo",
                clarificationQuestions=[],
                confidence=0.1,
            )
```

- [ ] **Step 5: Run test**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_query_understanding.py -q
```

Expected: PASS.

---

## Task 3: Implement Tool Registry and Router

**Files:**

- Modify: `agent-service/src/app/tools/base.py`
- Create: `agent-service/src/app/tools/registry.py`
- Modify: `agent-service/src/app/tools/fake_tools.py`
- Create: `agent-service/src/app/agent/tool_router.py`
- Test: `agent-service/tests/test_tool_router.py`

- [ ] **Step 1: Write router tests**

Create `agent-service/tests/test_tool_router.py`:

```python
from app.agent.tool_router import ToolRouter
from app.schemas import CompanyResolution, EvidenceItem, ResearchPlan, ResearchPlanStep, ToolCallResult
from app.tools.base import ResearchTool, ToolCapability


class StubTool(ResearchTool):
    name = "market_data"
    capability = ToolCapability(
        name="market_data",
        description="Fetch market data.",
        inputSchema={"type": "object"},
    )

    def run(self, tool_input, context):
        return (
            ToolCallResult(
                toolName="market_data",
                input=tool_input,
                output={"summary": "NVDA moved actively."},
                status="SUCCEEDED",
                latencyMs=1,
            ),
            [
                EvidenceItem(
                    sourceType="MARKET_DATA",
                    sourceName="Stub Market Tool",
                    sourceUrl="https://example.com/market/NVDA",
                    title="NVDA market data",
                    summary="NVDA moved actively.",
                    observedAt="2026-06-04T00:00:00+00:00",
                    relevance=0.8,
                    confidence=0.7,
                    rawContent='{"summary":"NVDA moved actively."}',
                )
            ],
        )


def test_tool_router_executes_registered_plan_steps():
    router = ToolRouter(tools={"market_data": StubTool()})
    plan = ResearchPlan(
        objective="Analyze NVDA",
        steps=[
            ResearchPlanStep(
                stepId="market",
                toolName="market_data",
                purpose="Fetch market context",
                toolInput={"ticker": "NVDA"},
                expectedEvidence="market evidence",
                required=True,
            )
        ],
    )

    tool_calls, evidence = router.execute(plan=plan, context={"query": "英伟达还能不能买？"})

    assert tool_calls[0].tool_name == "market_data"
    assert evidence[0].source_type == "MARKET_DATA"


def test_tool_router_records_unknown_tool_without_crashing():
    router = ToolRouter(tools={})
    plan = ResearchPlan(
        objective="Analyze NVDA",
        steps=[
            ResearchPlanStep(
                stepId="unknown",
                toolName="unknown_tool",
                purpose="Try unavailable tool",
                toolInput={},
                expectedEvidence="unknown evidence",
                required=False,
            )
        ],
    )

    tool_calls, evidence = router.execute(plan=plan, context={})

    assert tool_calls[0].tool_name == "unknown_tool"
    assert tool_calls[0].status == "FAILED"
    assert evidence == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_tool_router.py -q
```

Expected: FAIL because `ToolRouter` and `ToolCapability` do not exist.

- [ ] **Step 3: Extend tool base interface**

Modify `agent-service/src/app/tools/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.schemas import EvidenceItem, ToolCallResult


class ToolCapability(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(alias="inputSchema")

    model_config = {"populate_by_name": True}


class ResearchTool(ABC):
    name: str
    capability: ToolCapability

    @abstractmethod
    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        raise NotImplementedError
```

- [ ] **Step 4: Implement tool router**

Create `agent-service/src/app/agent/tool_router.py`:

```python
from time import perf_counter

from app.schemas import ResearchPlan, ToolCallResult, EvidenceItem
from app.tools.base import ResearchTool


class ToolRouter:
    def __init__(self, tools: dict[str, ResearchTool]) -> None:
        self.tools = tools

    def execute(
        self,
        *,
        plan: ResearchPlan,
        context: dict,
    ) -> tuple[list[ToolCallResult], list[EvidenceItem]]:
        tool_calls: list[ToolCallResult] = []
        evidence: list[EvidenceItem] = []

        for step in plan.steps:
            tool = self.tools.get(step.tool_name)
            if tool is None:
                tool_calls.append(_failed_tool_call(step.tool_name, step.tool_input))
                continue

            try:
                call, items = tool.run(tool_input=step.tool_input, context=context)
            except Exception as exc:
                call = _failed_tool_call(step.tool_name, step.tool_input, str(exc))
                items = []
            tool_calls.append(call)
            evidence.extend(items)

        return tool_calls, evidence


def _failed_tool_call(
    tool_name: str,
    tool_input: dict,
    message: str = "Tool is not registered.",
) -> ToolCallResult:
    started = perf_counter()
    return ToolCallResult(
        toolName=tool_name,
        input=tool_input,
        output={"error": message},
        status="FAILED",
        latencyMs=int((perf_counter() - started) * 1000),
    )
```

- [ ] **Step 5: Implement registry**

Create `agent-service/src/app/tools/registry.py`:

```python
from app.tools.base import ResearchTool, ToolCapability
from app.tools.fake_tools import default_tools


class ToolRegistry:
    def __init__(self, tools: dict[str, ResearchTool] | None = None) -> None:
        self.tools = tools or default_tools()

    def get_tools(self) -> dict[str, ResearchTool]:
        return self.tools

    def capabilities(self) -> list[ToolCapability]:
        return [tool.capability for tool in self.tools.values()]
```

- [ ] **Step 6: Adapt fake tools**

Modify `agent-service/src/app/tools/fake_tools.py`:

- Add `capability` to each tool.
- Change `run(query, company)` to `run(tool_input, context)`.
- Read `company` from `context.get("company")` if present.
- Read ticker from `tool_input["ticker"]` when present.
- Preserve existing EvidenceItem content.

- [ ] **Step 7: Run router test**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_tool_router.py -q
```

Expected: PASS.

---

## Task 4: Implement LLM Research Planner

**Files:**

- Create: `agent-service/src/app/agent/research_planner.py`
- Modify: `agent-service/src/app/agent/prompts.py`
- Test: `agent-service/tests/test_research_planner.py`

- [ ] **Step 1: Write planner tests**

Create `agent-service/tests/test_research_planner.py`:

```python
from app.agent.research_planner import ResearchPlanner
from app.schemas import QueryUnderstanding, ResearchPlan, ResearchPlanStep, ResearchTaskType
from app.tools.base import ToolCapability


class StubLLMClient:
    def __init__(self, response):
        self.response = response

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _understanding():
    return QueryUnderstanding(
        taskType=ResearchTaskType.INVESTMENT_THESIS,
        companies=[],
        timeHorizon="medium_term",
        requiresLiveData=True,
        outputStyle="research_memo",
        clarificationQuestions=[],
        confidence=0.9,
    )


def test_research_planner_uses_llm_and_tool_capabilities():
    llm_response = ResearchPlan(
        objective="判断 NVIDIA 当前投资吸引力",
        steps=[
            ResearchPlanStep(
                stepId="market",
                toolName="market_data",
                purpose="查看市场表现",
                toolInput={"ticker": "NVDA"},
                expectedEvidence="价格、成交量和波动",
                required=True,
            )
        ],
    )
    planner = ResearchPlanner(llm_client=StubLLMClient(llm_response))

    plan = planner.plan(
        query="英伟达还能不能买？",
        understanding=_understanding(),
        tool_capabilities=[
            ToolCapability(
                name="market_data",
                description="Fetch market data.",
                inputSchema={"type": "object"},
            )
        ],
    )

    assert plan.objective == "判断 NVIDIA 当前投资吸引力"
    assert plan.steps[0].tool_name == "market_data"


def test_research_planner_returns_default_plan_when_llm_fails():
    planner = ResearchPlanner(llm_client=StubLLMClient(RuntimeError("LLM unavailable")))

    plan = planner.plan(query="英伟达还能不能买？", understanding=_understanding(), tool_capabilities=[])

    assert plan.objective
    assert [step.tool_name for step in plan.steps] == ["company_search", "market_data", "news_search", "fundamentals"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_research_planner.py -q
```

Expected: FAIL because `ResearchPlanner` does not exist.

- [ ] **Step 3: Add planning prompt**

Modify `agent-service/src/app/agent/prompts.py`:

```python
RESEARCH_PLANNING_SYSTEM_PROMPT = """
You are the planning layer for an equity research agent.
Create a research plan using only the available tools provided by the system.

Rules:
- Every step must use a tool from availableTools.
- Do not answer the user directly.
- Do not invent tools.
- Prefer enough evidence to answer the user's research task.
- Keep the plan concise and traceable.
""".strip()


def research_planning_user_prompt(query: str, understanding: dict, tool_capabilities: list[dict]) -> str:
    return json.dumps(
        {
            "query": query,
            "understanding": understanding,
            "availableTools": tool_capabilities,
        },
        ensure_ascii=False,
    )
```

- [ ] **Step 4: Implement planner**

Create `agent-service/src/app/agent/research_planner.py`:

```python
from app.agent.prompts import RESEARCH_PLANNING_SYSTEM_PROMPT, research_planning_user_prompt
from app.llm import LLMClient
from app.schemas import QueryUnderstanding, ResearchPlan, ResearchPlanStep
from app.tools.base import ToolCapability


class ResearchPlanner:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def plan(
        self,
        *,
        query: str,
        understanding: QueryUnderstanding,
        tool_capabilities: list[ToolCapability],
    ) -> ResearchPlan:
        try:
            return self.llm_client.generate_structured(
                system_prompt=RESEARCH_PLANNING_SYSTEM_PROMPT,
                user_prompt=research_planning_user_prompt(
                    query=query,
                    understanding=understanding.model_dump(by_alias=True),
                    tool_capabilities=[
                        capability.model_dump(by_alias=True)
                        for capability in tool_capabilities
                    ],
                ),
                response_model=ResearchPlan,
            )
        except Exception:
            return _default_plan()


def _default_plan() -> ResearchPlan:
    return ResearchPlan(
        objective="生成一份基础投研分析，覆盖公司识别、市场表现、新闻和基本面。",
        steps=[
            ResearchPlanStep(
                stepId="company-resolution",
                toolName="company_search",
                purpose="确认研究对象",
                toolInput={},
                expectedEvidence="公司名称、ticker、交易所",
                required=True,
            ),
            ResearchPlanStep(
                stepId="market-context",
                toolName="market_data",
                purpose="查看近期市场表现",
                toolInput={},
                expectedEvidence="价格、成交量和波动",
                required=True,
            ),
            ResearchPlanStep(
                stepId="news-context",
                toolName="news_search",
                purpose="识别近期催化剂和风险事件",
                toolInput={},
                expectedEvidence="近期新闻摘要",
                required=True,
            ),
            ResearchPlanStep(
                stepId="fundamental-context",
                toolName="fundamentals",
                purpose="分析基本面背景",
                toolInput={},
                expectedEvidence="收入、盈利、现金流和估值摘要",
                required=True,
            ),
        ],
    )
```

- [ ] **Step 5: Run planner test**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_research_planner.py -q
```

Expected: PASS.

---

## Task 5: Implement Evidence Reasoning

**Files:**

- Create: `agent-service/src/app/agent/reasoning_engine.py`
- Modify: `agent-service/src/app/agent/prompts.py`
- Test: `agent-service/tests/test_reasoning_engine.py`

- [ ] **Step 1: Write tests**

Create `agent-service/tests/test_reasoning_engine.py`:

```python
from app.agent.reasoning_engine import ReasoningEngine
from app.schemas import AnalystReasoning, EvidenceItem, QueryUnderstanding, ResearchTaskType


class StubLLMClient:
    def __init__(self, response):
        self.response = response

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_reasoning_engine_uses_llm_over_evidence():
    expected = AnalystReasoning(
        thesis="证据支持谨慎乐观。",
        supportingPoints=["市场表现活跃。"],
        risks=["估值敏感。"],
        valuationNotes=[],
        missingData=[],
        uncertainty="缺少完整估值数据。",
    )
    engine = ReasoningEngine(llm_client=StubLLMClient(expected))

    result = engine.reason(query="英伟达还能不能买？", understanding=_understanding(), evidence=[])

    assert result.thesis == "证据支持谨慎乐观。"


def test_reasoning_engine_returns_default_when_llm_fails():
    engine = ReasoningEngine(llm_client=StubLLMClient(RuntimeError("LLM unavailable")))

    result = engine.reason(query="英伟达还能不能买？", understanding=_understanding(), evidence=[])

    assert result.missing_data
    assert "证据不足" in result.thesis


def _understanding():
    return QueryUnderstanding(
        taskType=ResearchTaskType.INVESTMENT_THESIS,
        companies=[],
        timeHorizon="medium_term",
        requiresLiveData=True,
        outputStyle="research_memo",
        clarificationQuestions=[],
        confidence=0.9,
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_reasoning_engine.py -q
```

Expected: FAIL because `ReasoningEngine` does not exist.

- [ ] **Step 3: Add prompt and implementation**

Add prompt:

```python
EVIDENCE_REASONING_SYSTEM_PROMPT = """
You are an equity research analyst reasoning over tool evidence.
Use only the supplied evidence.
If evidence is insufficient, explicitly list missingData.
Do not give direct investment advice.
Do not invent financial facts.
""".strip()
```

Create `agent-service/src/app/agent/reasoning_engine.py`:

```python
import json

from app.agent.prompts import EVIDENCE_REASONING_SYSTEM_PROMPT
from app.llm import LLMClient
from app.schemas import AnalystReasoning, EvidenceItem, QueryUnderstanding


class ReasoningEngine:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def reason(
        self,
        *,
        query: str,
        understanding: QueryUnderstanding,
        evidence: list[EvidenceItem],
    ) -> AnalystReasoning:
        try:
            return self.llm_client.generate_structured(
                system_prompt=EVIDENCE_REASONING_SYSTEM_PROMPT,
                user_prompt=json.dumps(
                    {
                        "query": query,
                        "understanding": understanding.model_dump(by_alias=True),
                        "evidence": [
                            item.model_dump(by_alias=True)
                            for item in evidence
                        ],
                    },
                    ensure_ascii=False,
                ),
                response_model=AnalystReasoning,
            )
        except Exception:
            return AnalystReasoning(
                thesis="当前证据不足以形成可靠投研判断。",
                supportingPoints=[],
                risks=["缺少可验证的市场、新闻或财务 evidence。"],
                valuationNotes=[],
                missingData=["market data", "financials", "news"],
                uncertainty="LLM reasoning 不可用或 evidence 不完整。",
            )
```

- [ ] **Step 4: Run test**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_reasoning_engine.py -q
```

Expected: PASS.

---

## Task 6: Implement Report Drafting and Reflection

**Files:**

- Modify: `agent-service/src/app/agent/report_writer.py`
- Create: `agent-service/src/app/agent/reflection_validator.py`
- Modify: `agent-service/src/app/agent/prompts.py`
- Test: `agent-service/tests/test_report_reflection.py`

- [ ] **Step 1: Write tests**

Create `agent-service/tests/test_report_reflection.py`:

```python
from app.agent.reflection_validator import ReflectionValidator
from app.agent.report_writer import ReportWriter
from app.schemas import AnalystReasoning, ReflectionResult, ResearchReport


class StubLLMClient:
    def __init__(self, response):
        self.response = response

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_report_writer_can_use_llm_draft():
    report = _report()
    writer = ReportWriter(llm_client=StubLLMClient(report))

    result = writer.write_from_reasoning(query="英伟达还能不能买？", reasoning=_reasoning(), evidence=[])

    assert result.title == "NVIDIA 投研 Agent Memo"


def test_reflection_validator_uses_llm_result():
    reflection = ReflectionResult(
        passed=False,
        unsupportedClaims=["增长确定性过强"],
        missingData=["valuation data"],
        overconfidentStatements=["一定会继续上涨"],
        revisionInstructions=["降低结论确定性。"],
    )
    validator = ReflectionValidator(llm_client=StubLLMClient(reflection))

    result = validator.reflect(query="英伟达还能不能买？", draft_report=_report(), evidence=[])

    assert result.passed is False
    assert result.revision_instructions == ["降低结论确定性。"]


def _reasoning():
    return AnalystReasoning(
        thesis="证据支持谨慎乐观。",
        supportingPoints=["市场表现活跃。"],
        risks=["估值敏感。"],
        valuationNotes=[],
        missingData=[],
        uncertainty="缺少完整估值数据。",
    )


def _report():
    return ResearchReport(
        title="NVIDIA 投研 Agent Memo",
        companySummary="NVIDIA 是本次研究对象。",
        questionUnderstanding="用户关注 NVIDIA 当前投资吸引力。",
        keyFindings=["证据支持谨慎乐观。"],
        opportunities=["增长预期是主要机会。"],
        risks=["估值敏感。"],
        evidenceSummary="已聚合 evidence。",
        uncertainty="缺少完整估值数据。",
        citations=["https://example.com/market/NVDA"],
        nonAdvisoryStatement="本报告为 AI Agent 生成的研究摘要，不构成投资建议。",
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_report_reflection.py -q
```

Expected: FAIL because `write_from_reasoning` and `ReflectionValidator` do not exist.

- [ ] **Step 3: Add report and reflection prompts**

Add to `prompts.py`:

```python
REPORT_GENERATION_SYSTEM_PROMPT = """
You write structured equity research memos from analyst reasoning and evidence.
Keep claims tied to evidence.
Do not provide direct investment advice.
Always include uncertainty and non-advisory statement.
""".strip()

REFLECTION_SYSTEM_PROMPT = """
You are a critic for an equity research agent.
Check the draft report for unsupported claims, missing data, overconfidence,
and investment-advice risk.
Return structured critique only.
""".strip()
```

- [ ] **Step 4: Modify report writer**

Add `llm_client` as optional constructor dependency in `ReportWriter`.

Add method:

```python
def write_from_reasoning(
    self,
    *,
    query: str,
    reasoning: AnalystReasoning,
    evidence: list[EvidenceItem],
) -> ResearchReport:
    if self.llm_client is not None:
        try:
            return self.llm_client.generate_structured(
                system_prompt=REPORT_GENERATION_SYSTEM_PROMPT,
                user_prompt=json.dumps(
                    {
                        "query": query,
                        "reasoning": reasoning.model_dump(by_alias=True),
                        "evidence": [item.model_dump(by_alias=True) for item in evidence],
                    },
                    ensure_ascii=False,
                ),
                response_model=ResearchReport,
            )
        except Exception:
            pass
    return self._default_report_from_reasoning(query=query, reasoning=reasoning, evidence=evidence)
```

Keep existing `write(...)` temporarily for backward compatibility until orchestrator is fully migrated.

- [ ] **Step 5: Implement reflection validator**

Create `agent-service/src/app/agent/reflection_validator.py`:

```python
import json

from app.agent.prompts import REFLECTION_SYSTEM_PROMPT
from app.llm import LLMClient
from app.schemas import EvidenceItem, ReflectionResult, ResearchReport


class ReflectionValidator:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def reflect(
        self,
        *,
        query: str,
        draft_report: ResearchReport,
        evidence: list[EvidenceItem],
    ) -> ReflectionResult:
        try:
            return self.llm_client.generate_structured(
                system_prompt=REFLECTION_SYSTEM_PROMPT,
                user_prompt=json.dumps(
                    {
                        "query": query,
                        "draftReport": draft_report.model_dump(by_alias=True),
                        "evidence": [item.model_dump(by_alias=True) for item in evidence],
                    },
                    ensure_ascii=False,
                ),
                response_model=ReflectionResult,
            )
        except Exception:
            return ReflectionResult(
                passed=True,
                unsupportedClaims=[],
                missingData=[],
                overconfidentStatements=[],
                revisionInstructions=[],
            )
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_report_reflection.py -q
```

Expected: PASS.

---

## Task 7: Migrate Orchestrator to Plan-and-Solve

**Files:**

- Modify: `agent-service/src/app/agent/orchestrator.py`
- Modify: `agent-service/tests/test_plan_and_solve_agent_run.py`
- Modify: `agent-service/tests/test_agent_run.py`
- Modify: `agent-service/tests/test_api.py`

- [ ] **Step 1: Write end-to-end test**

Create `agent-service/tests/test_plan_and_solve_agent_run.py`:

```python
from uuid import UUID

from app.agent.orchestrator import ResearchAgentOrchestrator


def test_plan_and_solve_orchestrator_returns_full_trace_without_real_llm_key():
    orchestrator = ResearchAgentOrchestrator()

    result = orchestrator.run(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        query="帮我分析一下英伟达现在还能不能买",
        locale="zh-CN",
    )

    assert result.understanding
    assert result.plan.steps
    assert result.tool_calls
    assert result.evidence
    assert result.reasoning
    assert result.draft_report
    assert result.reflection
    assert result.final_report
```

This test should pass without a real API key because each LLM stage has a default fallback.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_plan_and_solve_agent_run.py -q
```

Expected: FAIL because orchestrator still returns old fields.

- [ ] **Step 3: Modify orchestrator**

Update `ResearchAgentOrchestrator.__init__`:

```python
llm_client = create_llm_client_from_env()
tool_registry = ToolRegistry()

self.query_understanding = QueryUnderstandingService(llm_client=llm_client)
self.research_planner = ResearchPlanner(llm_client=llm_client)
self.tool_registry = tool_registry
self.tool_router = ToolRouter(tools=tool_registry.get_tools())
self.reasoning_engine = ReasoningEngine(llm_client=llm_client)
self.report_writer = ReportWriter(llm_client=llm_client)
self.reflection_validator = ReflectionValidator(llm_client=llm_client)
```

Update `run(...)` flow:

```python
understanding = self.query_understanding.understand(query)
plan = self.research_planner.plan(
    query=query,
    understanding=understanding,
    tool_capabilities=self.tool_registry.capabilities(),
)
tool_calls, evidence = self.tool_router.execute(
    plan=plan,
    context={"query": query, "understanding": understanding},
)
reasoning = self.reasoning_engine.reason(
    query=query,
    understanding=understanding,
    evidence=evidence,
)
draft_report = self.report_writer.write_from_reasoning(
    query=query,
    reasoning=reasoning,
    evidence=evidence,
)
reflection = self.reflection_validator.reflect(
    query=query,
    draft_report=draft_report,
    evidence=evidence,
)
final_report = draft_report
```

First version can set `final_report = draft_report`. A later revision step can ask LLM to revise according to reflection. This keeps one-pass reflection visible without adding another LLM call immediately.

- [ ] **Step 4: Update API and old agent tests**

Update tests to assert new fields:

```python
assert payload["understanding"]
assert payload["plan"]
assert payload["toolCalls"]
assert payload["evidence"]
assert payload["reasoning"]
assert payload["draftReport"]
assert payload["reflection"]
assert payload["finalReport"]
```

Remove assertions that rely on old top-level `company` and `intent`, unless compatibility fields are intentionally retained.

- [ ] **Step 5: Run focused tests**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest tests/test_plan_and_solve_agent_run.py tests/test_agent_run.py tests/test_api.py -q
```

Expected: PASS.

---

## Task 8: Documentation and Final Verification

**Files:**

- Modify: `agent-service/README.md`

- [ ] **Step 1: Update README flow**

Replace old flow:

```text
query interpreter
  -> company resolver
  -> research planner
  -> fake tools
  -> evidence
  -> report writer
  -> validator
```

With:

```text
query understanding
  -> LLM research planner
  -> tool router
  -> evidence
  -> evidence reasoning
  -> report drafting
  -> reflection
  -> final report
```

- [ ] **Step 2: Run all Python tests**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run import smoke test**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/python - <<'PY'
from app.main import app
print(app.title)
PY
```

Expected output:

```text
Equity Research Agent Service
```

- [ ] **Step 4: Manual API smoke test**

Run:

```bash
cd agent-service
./.venv-equity-research-agent/bin/uvicorn app.main:app --app-dir src --port 8001
```

In another terminal:

```bash
curl -X POST http://localhost:8001/agent-runs \
  -H 'Content-Type: application/json' \
  -d '{
    "runId": "00000000-0000-0000-0000-000000000000",
    "query": "帮我分析一下英伟达现在还能不能买",
    "locale": "zh-CN"
  }'
```

Expected: JSON response contains `understanding`, `plan`, `toolCalls`, `evidence`, `reasoning`, `draftReport`, `reflection`, and `finalReport`.

---

## Implementation Notes

- Keep LLM provider access behind `LLMClient`.
- Do not call OpenAI SDK directly from agent modules.
- Keep Pydantic schemas as the contract between LLM and code.
- Keep defaults conservative: when LLM fails, return structured fallback rather than crashing.
- Avoid adding multi-agent classes in this phase.
- Avoid implementing full ReAct loop in this phase.
- Keep Java unchanged in this phase.

## Self-Review Checklist

- The plan implements the approved design: Plan-and-Solve + Structured Tool Calling + One-pass Reflection.
- Query understanding and planning are logically separate.
- Tools are registry-driven, not hardcoded in orchestrator.
- LLM reasoning is evidence-bound.
- Reflection is one pass only.
- Existing FastAPI boundary remains.
- Python tests cover schema, understanding, planning, routing, reasoning, reflection, and API response.
