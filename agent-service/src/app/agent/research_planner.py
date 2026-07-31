from app.agent.prompts import RESEARCH_PLANNING_SYSTEM_PROMPT, research_planning_user_prompt
from app.llm import LLMClient
from app.schemas import AnswerPlan, AnswerSectionPlan, PlanningDecision, QueryUnderstanding, ResearchPlanStep, ResearchTaskType
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
    ) -> PlanningDecision:
        try:
            decision = self.llm_client.generate_structured(
                system_prompt=RESEARCH_PLANNING_SYSTEM_PROMPT,
                user_prompt=research_planning_user_prompt(
                    query=query,
                    understanding=understanding.model_dump(by_alias=True),
                    tool_capabilities=[
                        capability.model_dump(by_alias=True)
                        for capability in tool_capabilities
                    ],
                ),
                response_model=PlanningDecision,
            )
            return normalize_decision(decision)
        except Exception:
            return default_planning_decision(understanding=understanding, tool_capabilities=tool_capabilities)


def normalize_decision(decision: PlanningDecision) -> PlanningDecision:
    max_steps = max(0, min(decision.max_steps, 6))
    allowed_tools = list(dict.fromkeys(decision.allowed_tools))
    steps = decision.steps[:max_steps]
    if decision.needs_tools and not steps:
        steps = [
            ResearchPlanStep(
                stepId=f"step-{index}",
                toolName=tool_name,
                purpose=_purpose_for(tool_name),
                toolInput=_default_tool_input(tool_name),
                expectedEvidence=", ".join(decision.evidence_needs),
                required=True,
            )
            for index, tool_name in enumerate(allowed_tools[:max_steps], start=1)
        ]
    return PlanningDecision(
        answerability=decision.answerability,
        needsTools=decision.needs_tools,
        needsClarification=decision.needs_clarification,
        allowedTools=allowed_tools,
        evidenceNeeds=decision.evidence_needs,
        clarificationQuestions=decision.clarification_questions,
        maxSteps=max_steps,
        rationale=decision.rationale,
        objective=decision.objective or decision.rationale,
        steps=steps,
        answerPlan=_normalize_answer_plan(decision.answer_plan, fallback_goal=decision.objective or decision.rationale),
    )


def default_planning_decision(
    *,
    understanding: QueryUnderstanding,
    tool_capabilities: list[ToolCapability],
) -> PlanningDecision:
    available_tools = {capability.name for capability in tool_capabilities}
    if _has_company_candidate(understanding):
        allowed_tools = _available(
            [
                "company_search",
                "market_data",
                "news_search",
                "fundamentals",
                "filings_search",
                "sec_company_facts",
                "sec_filing_retriever",
            ],
            available_tools,
        )
        return _decision(
            answerability="TOOL_REQUIRED",
            needs_tools=True,
            needs_clarification=bool(understanding.clarification_questions),
            allowed_tools=allowed_tools or ["company_search", "market_data", "news_search", "fundamentals"],
            evidence_needs=["company_resolution", "market_data", "recent_news", "fundamentals"],
            clarification_questions=understanding.clarification_questions,
            rationale="识别到具体公司，需要用公司相关工具获取 evidence。",
            task_type=understanding.task_type,
        )

    if understanding.task_type in {
        ResearchTaskType.MARKET_EXPLORATION,
        ResearchTaskType.BEGINNER_GUIDANCE,
        ResearchTaskType.PORTFOLIO_STRATEGY,
    }:
        allowed_tools = _available(["market_overview", "etf_discovery", "stock_screener"], available_tools)
        return _decision(
            answerability="PARTIAL_WITH_TOOLS",
            needs_tools=bool(allowed_tools),
            needs_clarification=bool(understanding.clarification_questions),
            allowed_tools=allowed_tools,
            evidence_needs=["sector_etf_performance", "etf_category_performance", "large_cap_recent_performance"],
            clarification_questions=understanding.clarification_questions,
            rationale="没有具体标的，但可用广泛市场工具获取板块 ETF、常见 ETF 和大盘股近期表现。",
            task_type=understanding.task_type,
        )

    return _decision(
        answerability="CLARIFICATION_REQUIRED",
        needs_tools=False,
        needs_clarification=True,
        allowed_tools=[],
        evidence_needs=[],
        clarification_questions=understanding.clarification_questions
        or [
            "你想研究的具体公司、股票代码或市场方向是什么？",
            "你的投资期限和最大可承受亏损大概是多少？",
        ],
        rationale="缺少可执行的研究对象或关键约束，应该先向用户澄清。",
        task_type=understanding.task_type,
    )


def _decision(
    *,
    answerability: str,
    needs_tools: bool,
    needs_clarification: bool,
    allowed_tools: list[str],
    evidence_needs: list[str],
    clarification_questions: list[str],
    rationale: str,
    task_type: ResearchTaskType,
) -> PlanningDecision:
    max_steps = min(len(allowed_tools), 6)
    steps = [
        ResearchPlanStep(
            stepId=f"step-{index}",
            toolName=tool_name,
            purpose=_purpose_for(tool_name),
            toolInput=_default_tool_input(tool_name),
            expectedEvidence=", ".join(evidence_needs),
            required=True,
        )
        for index, tool_name in enumerate(allowed_tools[:max_steps], start=1)
    ]
    if not needs_tools:
        steps = []
        max_steps = 0
    return PlanningDecision(
        answerability=answerability,
        needsTools=needs_tools,
        needsClarification=needs_clarification,
        allowedTools=allowed_tools,
        evidenceNeeds=evidence_needs,
        clarificationQuestions=clarification_questions,
        maxSteps=max_steps,
        rationale=rationale,
        objective=rationale,
        steps=steps,
        answerPlan=_default_answer_plan(task_type, answer_goal=rationale),
    )


def _normalize_answer_plan(answer_plan: AnswerPlan, *, fallback_goal: str) -> AnswerPlan:
    if answer_plan.answer_goal and answer_plan.sections:
        return answer_plan
    if answer_plan.sections:
        return AnswerPlan(answerGoal=fallback_goal, sections=answer_plan.sections)
    return AnswerPlan(
        answerGoal=answer_plan.answer_goal or fallback_goal,
        sections=[
            AnswerSectionPlan(title="核心回答", purpose="直接回应用户问题。"),
            AnswerSectionPlan(title="依据与限制", purpose="说明证据来源、覆盖范围和不确定性。"),
        ],
    )


def _default_answer_plan(task_type: ResearchTaskType, *, answer_goal: str) -> AnswerPlan:
    if task_type == ResearchTaskType.MARKET_EXPLORATION:
        return AnswerPlan(
            answerGoal=answer_goal,
            sections=[
                AnswerSectionPlan(title="整体表现", purpose="概括市场或板块的可验证表现。"),
                AnswerSectionPlan(title="主要变化", purpose="整理领涨、领跌或显著变化方向。"),
                AnswerSectionPlan(title="数据限制", purpose="说明覆盖不足、时间范围或工具失败影响。"),
            ],
        )
    if task_type == ResearchTaskType.BEGINNER_GUIDANCE:
        return AnswerPlan(
            answerGoal=answer_goal,
            sections=[
                AnswerSectionPlan(title="可以先了解的方向", purpose="给出适合学习和继续研究的方向。"),
                AnswerSectionPlan(title="风险边界", purpose="提示新手容易忽略的风险。"),
                AnswerSectionPlan(title="下一步问题", purpose="引导用户补充期限、预算和风险承受能力。"),
            ],
        )
    if task_type == ResearchTaskType.PORTFOLIO_STRATEGY:
        return AnswerPlan(
            answerGoal=answer_goal,
            sections=[
                AnswerSectionPlan(title="配置思路", purpose="组织通用配置框架。"),
                AnswerSectionPlan(title="约束条件", purpose="说明需要用户补充的关键约束。"),
                AnswerSectionPlan(title="风险控制", purpose="说明分散化、仓位和波动风险。"),
            ],
        )
    if task_type == ResearchTaskType.COMPANY_COMPARISON:
        return AnswerPlan(
            answerGoal=answer_goal,
            sections=[
                AnswerSectionPlan(title="比较对象", purpose="明确比较范围。"),
                AnswerSectionPlan(title="关键差异", purpose="总结证据支持的主要差异。"),
                AnswerSectionPlan(title="数据限制", purpose="说明各对象证据覆盖差异。"),
            ],
        )
    return AnswerPlan(
        answerGoal=answer_goal,
        sections=[
            AnswerSectionPlan(title="核心结论", purpose="直接回应用户的研究问题。"),
            AnswerSectionPlan(title="支持证据", purpose="列出证据支撑的判断。"),
            AnswerSectionPlan(title="风险与不确定性", purpose="说明反方因素和缺失数据。"),
        ],
    )


def _available(preferred_tools: list[str], available_tools: set[str]) -> list[str]:
    if not available_tools:
        return preferred_tools
    return [tool_name for tool_name in preferred_tools if tool_name in available_tools]


def _has_company_candidate(understanding: QueryUnderstanding) -> bool:
    return any(company.candidates for company in understanding.companies)


def _purpose_for(tool_name: str) -> str:
    return {
        "company_search": "识别或确认研究对象",
        "market_data": "获取市场价格和成交量背景",
        "news_search": "获取近期新闻和市场叙事",
        "fundamentals": "获取基本面和估值指标",
        "filings_search": "获取官方公告和披露",
        "sec_company_facts": "获取 SEC XBRL 财务事实",
        "sec_filing_retriever": "检索 SEC filing 原文相关片段",
        "market_overview": "获取板块 ETF 近期表现",
        "etf_discovery": "获取常见 ETF 类别近期表现",
        "stock_screener": "获取大盘股观察池近期表现",
        "web_article_reader": "读取用户提供的网页内容",
    }.get(tool_name, "补充回答所需 evidence")


def _default_tool_input(tool_name: str) -> dict:
    if tool_name == "etf_discovery":
        return {"riskProfile": "beginner"}
    if tool_name == "stock_screener":
        return {"profile": "beginner", "limit": 8}
    return {}
