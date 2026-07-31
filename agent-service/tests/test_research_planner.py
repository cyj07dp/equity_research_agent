from app.agent.research_planner import ResearchPlanner
from app.schemas import CompanyCandidate, CompanyMention, PlanningDecision, QueryUnderstanding, ResearchPlanStep, ResearchTaskType
from app.tools.base import ToolCapability


class StubLLMClient:
    def __init__(self, response):
        self.response = response

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_research_planner_uses_llm_and_tool_capabilities():
    llm_response = PlanningDecision(
        answerability="TOOL_REQUIRED",
        needsTools=True,
        needsClarification=False,
        allowedTools=["market_data"],
        evidenceNeeds=["价格、成交量和波动"],
        clarificationQuestions=[],
        maxSteps=1,
        rationale="需要市场数据支持判断。",
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
    assert plan.needs_tools is True
    assert plan.allowed_tools == ["market_data"]


def test_research_planner_returns_default_plan_when_llm_fails():
    planner = ResearchPlanner(llm_client=StubLLMClient(RuntimeError("LLM unavailable")))

    plan = planner.plan(
        query="英伟达还能不能买？",
        understanding=_understanding(),
        tool_capabilities=[],
    )

    assert plan.objective
    assert [step.tool_name for step in plan.steps] == [
        "company_search",
        "market_data",
        "news_search",
        "fundamentals",
        "filings_search",
        "sec_company_facts",
    ]


def test_research_planner_uses_default_decision_when_llm_fails_for_broad_query():
    planner = ResearchPlanner(llm_client=StubLLMClient(RuntimeError("LLM unavailable")))

    plan = planner.plan(
        query="我是美股小白，适合看哪些方向？",
        understanding=_market_exploration_understanding(),
        tool_capabilities=[
            ToolCapability(name="market_overview", description="Market context.", inputSchema={}),
            ToolCapability(name="etf_discovery", description="ETF discovery.", inputSchema={}),
            ToolCapability(name="stock_screener", description="Stock screening.", inputSchema={}),
        ],
    )

    assert [step.tool_name for step in plan.steps] == ["market_overview", "etf_discovery", "stock_screener"]
    assert plan.needs_clarification is True
    assert plan.clarification_questions == ["你的投资期限是多久？"]
    assert plan.answer_plan.answer_goal
    assert "可以先了解的方向" in [section.title for section in plan.answer_plan.sections]
    assert "机会" not in [section.title for section in plan.answer_plan.sections]


def test_research_planner_preserves_llm_answer_plan():
    llm_response = PlanningDecision(
        answerability="PARTIAL_WITH_TOOLS",
        needsTools=True,
        needsClarification=False,
        allowedTools=["market_data"],
        evidenceNeeds=["5-day sector returns"],
        clarificationQuestions=[],
        maxSteps=1,
        rationale="需要板块 ETF 数据。",
        objective="对比美股板块表现",
        steps=[
            ResearchPlanStep(
                stepId="sector-data",
                toolName="market_data",
                purpose="获取板块ETF行情",
                toolInput={"ticker": "XLK"},
                expectedEvidence="5-day sector returns",
                required=True,
            )
        ],
        answerPlan={
            "answerGoal": "回答最近五个交易日美股各板块表现。",
            "sections": [
                {"title": "板块表现", "purpose": "列出各板块涨跌。"},
                {"title": "数据限制", "purpose": "说明覆盖不足。"},
            ],
        },
    )
    planner = ResearchPlanner(llm_client=StubLLMClient(llm_response))

    plan = planner.plan(
        query="最近五个交易日美股各板块表现如何？",
        understanding=_market_exploration_understanding(),
        tool_capabilities=[ToolCapability(name="market_data", description="Market data.", inputSchema={})],
    )

    assert plan.answer_plan.answer_goal == "回答最近五个交易日美股各板块表现。"
    assert [section.title for section in plan.answer_plan.sections] == ["板块表现", "数据限制"]


def _understanding():
    return QueryUnderstanding(
        taskType=ResearchTaskType.INVESTMENT_THESIS,
        companies=[
            CompanyMention(
                mention="英伟达",
                canonicalName="NVIDIA Corporation",
                candidates=[CompanyCandidate(ticker="NVDA", exchange="NASDAQ", market="US", confidence=0.95)],
                needsClarification=False,
            )
        ],
        timeHorizon="medium_term",
        requiresLiveData=True,
        outputStyle="research_memo",
        clarificationQuestions=[],
        confidence=0.9,
    )


def _market_exploration_understanding():
    return QueryUnderstanding(
        taskType=ResearchTaskType.BEGINNER_GUIDANCE,
        companies=[],
        timeHorizon="unspecified",
        analysisAspects=["market_overview", "portfolio_strategy", "risk_management"],
        comparisonMode=False,
        userDecisionContext="beginner_stock_selection_and_strategy",
        requiresLiveData=False,
        outputStyle="beginner_friendly",
        constraints=["beginner_appropriate", "diversification"],
        clarificationQuestions=["你的投资期限是多久？"],
        confidence=0.7,
    )
