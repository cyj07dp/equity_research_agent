from uuid import UUID
from datetime import UTC, datetime
import json

from app.agent.orchestrator import ResearchAgentOrchestrator
from app.agent.tool_router import ToolRouter
from app.schemas import AgentPlanDecision, CompanyCandidate, CompanyMention, EvidenceItem, ToolCallResult
from app.tools.base import ResearchTool, ToolCapability


def test_agent_run_understands_plans_tools_reasons_and_generates_report():
    orchestrator = ResearchAgentOrchestrator()
    orchestrator.agent_planner.plan = lambda **kwargs: _agent_plan(
        companies=[
            CompanyMention(
                mention="Palantir",
                canonicalName="Palantir Technologies",
                candidates=[CompanyCandidate(ticker="PLTR", exchange="NASDAQ", market="US", confidence=0.9)],
                needsClarification=False,
            )
        ],
        allowed_tools=["company_search", "market_data", "news_search", "fundamentals"],
        evidence_needs=["company_resolution", "market_data", "news", "fundamentals"],
        steps=[
            {"stepId": "company", "toolName": "company_search", "toolInput": {"ticker": "PLTR"}},
            {"stepId": "market", "toolName": "market_data", "toolInput": {"ticker": "PLTR"}},
            {"stepId": "news", "toolName": "news_search", "toolInput": {"ticker": "PLTR"}},
            {"stepId": "fund", "toolName": "fundamentals", "toolInput": {"ticker": "PLTR"}},
        ],
    )
    result = orchestrator.run(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        query="帮我分析一下 Palantir 最近的增长机会和主要风险",
        locale="zh-CN",
    )

    assert result.understanding is not None
    assert len(result.plan.steps) >= 3
    assert {call.tool_name for call in result.tool_calls} >= {
        "company_search",
        "market_data",
        "news_search",
    }
    assert len(result.evidence) >= 1
    assert any(
        call.status == "FAILED" and "ALPHA_VANTAGE_API_KEY" in call.output.get("error", "")
        for call in result.tool_calls
        if call.tool_name in {"market_data", "news_search", "fundamentals"}
    )
    assert result.reasoning is not None
    assert result.draft_report is not None
    assert result.draft_report.sections
    assert any(section.title == "核心回答" for section in result.draft_report.sections)
    assert any(section.title == "限制" for section in result.draft_report.sections)
    assert result.reflection is not None
    assert result.final_report is not None
    assert result.run_status == "COMPLETED"


def test_agent_run_uses_market_exploration_tools_for_beginner_no_ticker_query():
    orchestrator = ResearchAgentOrchestrator()
    orchestrator.tool_router = ToolRouter(
        tools={
            "market_overview": _StaticEvidenceTool("market_overview", "市场概览 evidence"),
            "etf_discovery": _StaticEvidenceTool("etf_discovery", "ETF evidence"),
            "stock_screener": _StaticEvidenceTool("stock_screener", "股票池 evidence"),
        }
    )
    orchestrator.agent_planner.plan = lambda **kwargs: _agent_plan(
        companies=[],
        allowed_tools=["market_overview", "etf_discovery", "stock_screener"],
        evidence_needs=["market_context", "etf_categories", "screening_framework"],
        clarification_questions=["你的投资期限是多久？"],
        steps=[
            {"stepId": "overview", "toolName": "market_overview", "toolInput": {}},
            {"stepId": "etf", "toolName": "etf_discovery", "toolInput": {}},
            {"stepId": "screen", "toolName": "stock_screener", "toolInput": {}},
        ],
    )

    result = orchestrator.run(
        run_id=UUID("00000000-0000-0000-0000-000000000001"),
        query="我是一个刚接触美股的小白，你觉得我适合入手哪些股？应该选择哪种购买策略？",
        locale="zh-CN",
    )

    assert [step.tool_name for step in result.plan.steps] == [
        "market_overview",
        "etf_discovery",
        "stock_screener",
    ]
    assert {call.tool_name for call in result.tool_calls} == {
        "market_overview",
        "etf_discovery",
        "stock_screener",
    }
    assert len(result.evidence) == 3
    assert {item.source_type for item in result.evidence} == {"MARKET_DATA"}
    assert result.planning_decision.allowed_tools == ["market_overview", "etf_discovery", "stock_screener"]
    assert result.run_status == "COMPLETED"
    assert result.clarification_questions == ["你的投资期限是多久？"]


def test_agent_run_degrades_without_extra_llm_when_tools_return_no_evidence():
    orchestrator = ResearchAgentOrchestrator()
    orchestrator.tool_router = ToolRouter(tools={"market_overview": _NoEvidenceTool("market_overview")})
    orchestrator.agent_planner.plan = lambda **kwargs: _agent_plan(
        companies=[],
        allowed_tools=["market_overview"],
        evidence_needs=["market_context"],
        steps=[{"stepId": "overview", "toolName": "market_overview", "toolInput": {}}],
    )
    orchestrator.reasoning_engine.reason = lambda **kwargs: (_raise("reasoning should be skipped"))
    orchestrator.report_writer.write_from_reasoning = lambda **kwargs: (_raise("report drafting should be skipped"))
    orchestrator.reflection_validator.reflect = lambda **kwargs: (_raise("reflection should be skipped"))

    result = orchestrator.run(
        run_id=UUID("00000000-0000-0000-0000-000000000004"),
        query="最近美股哪些方向表现比较强？",
        locale="zh-CN",
    )

    assert result.run_status == "DEGRADED"
    assert result.runtime_warnings
    assert result.evidence == []
    assert result.final_report is not None
    assert "工具已执行" in result.runtime_warnings[0]


class _StaticEvidenceTool(ResearchTool):
    def __init__(self, name: str, summary: str) -> None:
        self.name = name
        self.summary = summary
        self.capability = ToolCapability(name=name, description=summary, inputSchema={})

    def run(self, tool_input: dict, context: dict):
        return (
            ToolCallResult(
                toolName=self.name,
                input=tool_input,
                output={"summary": self.summary},
                status="SUCCEEDED",
                latencyMs=1,
            ),
            [
                EvidenceItem(
                    sourceType="MARKET_DATA",
                    sourceName="TestProvider",
                    sourceUrl="https://example.com",
                    title=self.summary,
                    summary=self.summary,
                    observedAt=datetime.now(UTC).isoformat(),
                    relevance=0.8,
                    confidence=0.8,
                    rawContent=json.dumps({"summary": self.summary}, ensure_ascii=False),
                )
            ],
        )


class _NoEvidenceTool(ResearchTool):
    def __init__(self, name: str) -> None:
        self.name = name
        self.capability = ToolCapability(name=name, description="No evidence tool", inputSchema={})

    def run(self, tool_input: dict, context: dict):
        return (
            ToolCallResult(
                toolName=self.name,
                input=tool_input,
                output={"message": "no data"},
                status="SUCCEEDED",
                latencyMs=1,
            ),
            [],
        )


def _raise(message: str):
    raise AssertionError(message)


def test_agent_run_continues_with_limited_report_when_no_ticker_requires_clarification():
    orchestrator = ResearchAgentOrchestrator()
    orchestrator.agent_planner.plan = lambda **kwargs: _agent_plan(
        companies=[],
        answerability="CLARIFICATION_REQUIRED",
        needs_tools=False,
        needs_clarification=True,
        allowed_tools=[],
        evidence_needs=[],
        clarification_questions=["你想研究哪家公司或股票代码？"],
        rationale="缺少研究对象，无法形成工具计划。",
        steps=[],
    )

    result = orchestrator.run(
        run_id=UUID("00000000-0000-0000-0000-000000000002"),
        query="现在要不要买？",
        locale="zh-CN",
    )

    assert result.plan.steps == []
    assert result.tool_calls == []
    assert result.evidence == []
    assert result.final_report is not None
    assert result.reasoning is not None
    assert result.draft_report is not None
    assert result.reflection is not None
    assert result.run_status == "COMPLETED"
    assert result.clarification_questions == ["你想研究哪家公司或股票代码？"]
    assert "证据不足" in result.reasoning.thesis


def test_agent_run_continues_with_open_questions_when_planner_needs_clarification_even_if_tools_may_be_needed():
    orchestrator = ResearchAgentOrchestrator()
    orchestrator.agent_planner.plan = lambda **kwargs: _agent_plan(
        companies=[],
        answerability="CLARIFICATION_REQUIRED",
        needs_tools=True,
        needs_clarification=True,
        allowed_tools=["market_overview", "market_data", "news_search"],
        evidence_needs=["板块价格变动", "近期市场新闻"],
        clarification_questions=["请问您关注的是哪个市场（例如A股、港股、美股）的板块表现？"],
        rationale="用户未指定市场，必须先澄清市场才能设计有效的研究步骤。",
        objective="明确市场后再获取最近五个交易日板块表现。",
        steps=[],
    )

    result = orchestrator.run(
        run_id=UUID("00000000-0000-0000-0000-000000000003"),
        query="最近五个交易日各个板块股价表现如何",
        locale="zh-CN",
    )

    assert result.run_status == "COMPLETED"
    assert result.plan.steps == []
    assert result.tool_calls == []
    assert result.evidence == []
    assert result.reasoning is not None
    assert result.draft_report is not None
    assert result.reflection is not None
    assert result.final_report is not None
    assert result.clarification_questions == ["请问您关注的是哪个市场（例如A股、港股、美股）的板块表现？"]


def _agent_plan(
    *,
    companies: list[CompanyMention],
    allowed_tools: list[str],
    evidence_needs: list[str],
    steps: list[dict],
    answerability: str = "TOOL_REQUIRED",
    needs_tools: bool = True,
    needs_clarification: bool = False,
    clarification_questions: list[str] | None = None,
    rationale: str = "需要工具证据支持回答。",
    objective: str = "生成基于证据的研究回答。",
) -> AgentPlanDecision:
    return AgentPlanDecision.model_validate({
        "intent": {
            "summary": objective,
            "companies": [company.model_dump(by_alias=True) for company in companies],
            "entities": [],
            "constraints": [],
            "needsLiveData": needs_tools,
            "riskLevel": "HIGH" if "要不要买" in objective else "NORMAL",
        },
        "answerability": answerability,
        "needsTools": needs_tools,
        "needsClarification": needs_clarification,
        "allowedTools": allowed_tools,
        "evidenceNeeds": evidence_needs,
        "clarificationQuestions": clarification_questions or [],
        "maxSteps": len(steps),
        "rationale": rationale,
        "objective": objective,
        "steps": steps,
        "answerPlan": {
            "answerGoal": objective,
            "sections": [
                {"title": "核心回答", "purpose": "直接回答用户问题。"},
                {"title": "限制", "purpose": "说明证据限制和不确定性。"},
            ],
        },
        "answerPolicy": {"noDirectInvestmentAdvice": True, "mustCiteEvidence": True},
    })
