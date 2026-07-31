from app.agent.agent_planner import AgentPlanner
from app.schemas import AgentPlanDecision
from app.tools.base import ToolCapability


class StubLLMClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_agent_planner_combines_intent_and_tool_plan():
    response = AgentPlanDecision.model_validate({
        "intent": {
            "summary": "分析苹果年报风险",
            "companies": [{
                "mention": "苹果",
                "canonicalName": "Apple Inc.",
                "candidates": [{"ticker": "AAPL", "exchange": "NASDAQ", "market": "US", "confidence": 0.95}],
                "needsClarification": False,
            }],
            "entities": [],
            "constraints": [],
            "needsLiveData": True,
            "riskLevel": "HIGH",
        },
        "answerability": "TOOL_REQUIRED",
        "needsTools": True,
        "needsClarification": False,
        "allowedTools": ["filings_search", "sec_filing_retriever", "market_data"],
        "evidenceNeeds": ["sec_risk_factors", "market_data"],
        "clarificationQuestions": [],
        "maxSteps": 3,
        "rationale": "需要 SEC 原文和市场数据。",
        "objective": "分析苹果年报风险并结合市场表现。",
        "steps": [
            {"stepId": "sec", "toolName": "sec_filing_retriever", "toolInput": {"ticker": "AAPL", "query": "risk factors"}},
            {"stepId": "market", "toolName": "market_data", "toolInput": {"ticker": "AAPL"}},
        ],
        "answerPlan": {"answerGoal": "回答风险问题", "sections": [{"title": "主要风险", "purpose": "总结 SEC 风险因素"}]},
        "answerPolicy": {"noDirectInvestmentAdvice": True},
    })
    planner = AgentPlanner(llm_client=StubLLMClient(response))

    result = planner.plan(
        query="帮我分析苹果年报风险",
        conversation_context="",
        user_preferences={},
        tool_capabilities=[
            ToolCapability(name="sec_filing_retriever", description="", inputSchema={}, outputEvidenceType="SEC_RAG"),
            ToolCapability(name="market_data", description="", inputSchema={}, outputEvidenceType="MARKET_DATA"),
        ],
    )

    assert result.intent.companies[0].candidates[0].ticker == "AAPL"
    assert [step.tool_name for step in result.steps] == ["sec_filing_retriever", "market_data"]
    assert result.steps[0].output_evidence_type == "SEC_RAG"
    assert result.steps[0].expected_evidence_types == ["SEC_RAG"]
    assert result.answer_policy["noDirectInvestmentAdvice"] is True


def test_agent_planner_fallback_uses_broad_market_tools():
    planner = AgentPlanner(llm_client=StubLLMClient(RuntimeError("LLM unavailable")))

    result = planner.plan(
        query="最近美股哪些方向值得学习？",
        conversation_context="",
        user_preferences={},
        tool_capabilities=[
            ToolCapability(name="market_overview", description="", inputSchema={}, outputEvidenceType="MARKET_DATA"),
            ToolCapability(name="etf_discovery", description="", inputSchema={}, outputEvidenceType="MARKET_DATA"),
            ToolCapability(name="stock_screener", description="", inputSchema={}, outputEvidenceType="MARKET_DATA"),
        ],
    )

    assert result.intent.summary == "最近美股哪些方向值得学习？"
    assert [step.tool_name for step in result.steps] == ["market_overview", "etf_discovery", "stock_screener"]
    assert [step.output_evidence_type for step in result.steps] == ["MARKET_DATA", "MARKET_DATA", "MARKET_DATA"]
    assert result.answer_policy["mustCiteEvidence"] is True


def test_agent_planner_injects_user_preferences_as_planning_signal():
    response = AgentPlanDecision.model_validate({
        "intent": {
            "summary": "低风险长期关注苹果",
            "companies": [{
                "mention": "苹果",
                "canonicalName": "Apple Inc.",
                "candidates": [{"ticker": "AAPL", "exchange": "NASDAQ", "market": "US", "confidence": 0.95}],
                "needsClarification": False,
            }],
            "entities": [],
            "constraints": ["低风险", "长期"],
            "needsLiveData": True,
            "riskLevel": "HIGH",
        },
        "answerability": "TOOL_REQUIRED",
        "needsTools": True,
        "needsClarification": False,
        "allowedTools": ["fundamentals", "sec_filing_retriever"],
        "evidenceNeeds": ["fundamentals", "sec_long_term_risks"],
        "clarificationQuestions": [],
        "maxSteps": 2,
        "rationale": "用户偏好低风险和长期，应优先验证基本面与 SEC 长期风险。",
        "objective": "判断苹果是否适合低风险长期关注。",
        "steps": [
            {"stepId": "fundamentals", "toolName": "fundamentals", "toolInput": {"ticker": "AAPL"}},
            {
                "stepId": "sec-risk",
                "toolName": "sec_filing_retriever",
                "toolInput": {"ticker": "AAPL", "query": "long term risk factors"},
            },
        ],
        "answerPlan": {"answerGoal": "结合用户偏好回答是否值得继续关注", "sections": [{"title": "适配度", "purpose": "说明低风险长期偏好的匹配程度"}]},
        "answerPolicy": {
            "riskTolerance": "LOW",
            "timeHorizon": "LONG_TERM",
            "avoidPhrases": ["稳赚", "闭眼买", "重仓"],
        },
    })
    llm = StubLLMClient(response)
    planner = AgentPlanner(llm_client=llm)

    result = planner.plan(
        query="苹果适合我继续关注吗？",
        conversation_context="",
        user_preferences={
            "enabled": True,
            "riskTolerance": "LOW",
            "timeHorizon": "LONG_TERM",
            "preferredAssets": ["ETF"],
        },
        tool_capabilities=[
            ToolCapability(name="fundamentals", description="", inputSchema={}),
            ToolCapability(name="sec_filing_retriever", description="", inputSchema={}),
        ],
    )

    user_prompt = llm.calls[0]["user_prompt"]
    assert '"riskTolerance": "LOW"' in user_prompt
    assert '"timeHorizon": "LONG_TERM"' in user_prompt
    assert '"preferredAssets": ["ETF"]' in user_prompt
    assert [step.tool_name for step in result.steps] == ["fundamentals", "sec_filing_retriever"]
    assert result.answer_policy["riskTolerance"] == "LOW"
