from app.agent.plan_validator import PlanValidator
from app.schemas import AgentPlanDecision, PlanningDecision, QueryUnderstanding, ResearchPlan, ResearchPlanStep, ResearchTaskType


def test_plan_validator_filters_disallowed_tools_and_invalid_article_reader():
    plan = ResearchPlan(
        objective="为用户探索可研究方向",
        steps=[
            ResearchPlanStep(stepId="bad-market", toolName="market_data", toolInput={"ticker": ""}),
            ResearchPlanStep(stepId="bad-reader", toolName="web_article_reader", toolInput={}),
            ResearchPlanStep(stepId="overview", toolName="market_overview", toolInput={}),
            ResearchPlanStep(stepId="etf", toolName="etf_discovery", toolInput={}),
        ],
    )

    result = PlanValidator().validate(
        plan=plan,
        understanding=_understanding_without_company(),
        planning_decision=_planning_decision(["market_overview", "etf_discovery"], max_steps=4),
    )

    assert [step.tool_name for step in result.steps] == ["market_overview", "etf_discovery"]


def test_plan_validator_respects_max_steps():
    plan = ResearchPlan(
        objective="最多两步",
        steps=[
            ResearchPlanStep(stepId="overview", toolName="market_overview", toolInput={}),
            ResearchPlanStep(stepId="etf", toolName="etf_discovery", toolInput={}),
            ResearchPlanStep(stepId="screen", toolName="stock_screener", toolInput={}),
        ],
    )

    result = PlanValidator().validate(
        plan=plan,
        understanding=_understanding_without_company(),
        planning_decision=_planning_decision(["market_overview", "etf_discovery", "stock_screener"], max_steps=2),
    )

    assert [step.tool_name for step in result.steps] == ["market_overview", "etf_discovery"]


def test_plan_validator_accepts_agent_plan_decision():
    plan = ResearchPlan(
        objective="使用新 AgentPlanner 决策校验",
        steps=[
            ResearchPlanStep(stepId="overview", toolName="market_overview", toolInput={}),
            ResearchPlanStep(stepId="blocked", toolName="market_data", toolInput={"ticker": ""}),
        ],
    )

    result = PlanValidator().validate(
        plan=plan,
        planning_decision=AgentPlanDecision(
            intent={"summary": "市场探索", "entities": [], "companies": [], "constraints": [], "needsLiveData": True, "riskLevel": "NORMAL"},
            answerability="PARTIAL_WITH_TOOLS",
            needsTools=True,
            needsClarification=False,
            allowedTools=["market_overview", "market_data"],
            evidenceNeeds=["market_context"],
            clarificationQuestions=[],
            maxSteps=3,
            rationale="需要市场证据。",
            objective="探索市场方向。",
            steps=[],
            answerPlan={"answerGoal": "回答市场方向", "sections": []},
            answerPolicy={"noDirectInvestmentAdvice": True},
        ),
    )

    assert [step.tool_name for step in result.steps] == ["market_overview"]


def test_plan_validator_blocks_steps_when_clarification_required_without_tools():
    plan = ResearchPlan(
        objective="错误地尝试执行工具",
        steps=[
            ResearchPlanStep(stepId="market", toolName="market_data", toolInput={"ticker": "TSLA"}),
        ],
    )

    result = PlanValidator().validate(
        plan=plan,
        understanding=_understanding_without_company(),
        planning_decision=PlanningDecision(
            answerability="CLARIFICATION_REQUIRED",
            needsTools=False,
            needsClarification=True,
            allowedTools=[],
            evidenceNeeds=[],
            clarificationQuestions=["你这里的“纳斯达克”是指公司还是指数？"],
            maxSteps=0,
            rationale="存在阻塞性歧义。",
            objective="先澄清对象。",
            steps=[],
        ),
    )

    assert result.steps == []


def _understanding_without_company():
    return QueryUnderstanding(
        taskType=ResearchTaskType.MARKET_EXPLORATION,
        companies=[],
        timeHorizon="unspecified",
        analysisAspects=["market_context"],
        comparisonMode=False,
        userDecisionContext="market_exploration",
        requiresLiveData=False,
        outputStyle="beginner_friendly",
        constraints=[],
        clarificationQuestions=[],
        confidence=0.8,
    )


def _planning_decision(allowed_tools, max_steps):
    return PlanningDecision(
        answerability="PARTIAL_WITH_TOOLS",
        needsTools=True,
        needsClarification=False,
        allowedTools=allowed_tools,
        evidenceNeeds=["market_context"],
        clarificationQuestions=[],
        maxSteps=max_steps,
        rationale="需要广泛市场 evidence。",
        objective="为用户探索可研究方向",
        steps=[],
    )
