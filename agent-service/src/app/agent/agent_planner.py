import logging

from app.agent.prompts import AGENT_PLANNER_SYSTEM_PROMPT, agent_planner_user_prompt
from app.llm import LLMClient
from app.schemas import AgentPlanDecision, AnswerPlan, AnswerSectionPlan, ResearchPlanStep
from app.tools.base import ToolCapability

logger = logging.getLogger("uvicorn.error")


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
                    tool_capabilities=[capability.model_dump(by_alias=True) for capability in tool_capabilities],
                ),
                response_model=AgentPlanDecision,
            )
            return normalize_agent_plan(decision, tool_capabilities=tool_capabilities)
        except Exception as exc:
            logger.warning("LLM fallback stage=agent_planning reason=%s", exc)
            return fallback_agent_plan(query=query, tool_capabilities=tool_capabilities)


def normalize_agent_plan(decision: AgentPlanDecision, tool_capabilities: list[ToolCapability] | None = None) -> AgentPlanDecision:
    max_steps = max(0, min(decision.max_steps, 6))
    allowed_tools = list(dict.fromkeys(decision.allowed_tools))
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
            for index, tool_name in enumerate(allowed_tools[:max_steps], start=1)
        ]
    decision.max_steps = max_steps
    decision.allowed_tools = allowed_tools
    decision.steps = _steps_with_evidence_metadata(steps, tool_capabilities or [])
    if not decision.answer_plan.sections:
        decision.answer_plan = AnswerPlan(
            answerGoal=decision.objective or decision.rationale,
            sections=[
                AnswerSectionPlan(title="核心回答", purpose="直接回答用户问题。"),
                AnswerSectionPlan(title="证据依据", purpose="说明证据来源和覆盖范围。"),
                AnswerSectionPlan(title="限制与下一步", purpose="说明不确定性和后续研究方向。"),
            ],
        )
    return decision


def _steps_with_evidence_metadata(
    steps: list[ResearchPlanStep],
    tool_capabilities: list[ToolCapability],
) -> list[ResearchPlanStep]:
    evidence_by_tool = {
        capability.name: capability.output_evidence_type
        for capability in tool_capabilities
        if capability.output_evidence_type
    }
    for step in steps:
        tool_name = step.tool_name or step.tool
        evidence_type = evidence_by_tool.get(str(tool_name or ""))
        if evidence_type:
            step.output_evidence_type = evidence_type
            if evidence_type not in step.expected_evidence_types:
                step.expected_evidence_types.append(evidence_type)
    return steps


def fallback_agent_plan(*, query: str, tool_capabilities: list[ToolCapability]) -> AgentPlanDecision:
    available_tools = {capability.name for capability in tool_capabilities}
    broad_tools = [name for name in ["market_overview", "etf_discovery", "stock_screener"] if name in available_tools]
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
            ResearchPlanStep(
                stepId=f"step-{index}",
                toolName=name,
                toolInput={},
                outputEvidenceType=_output_evidence_type(name, tool_capabilities),
                expectedEvidenceTypes=[_output_evidence_type(name, tool_capabilities)] if _output_evidence_type(name, tool_capabilities) else [],
                required=True,
            )
            for index, name in enumerate(broad_tools, start=1)
        ],
        answerPlan={
            "answerGoal": "给出谨慎研究回答。",
            "sections": [
                {"title": "核心回答", "purpose": "直接回答用户问题。"},
                {"title": "证据限制", "purpose": "说明可用证据不足之处。"},
            ],
        },
        answerPolicy={"noDirectInvestmentAdvice": True, "mustCiteEvidence": True, "language": "zh-CN"},
    )


def _output_evidence_type(tool_name: str, tool_capabilities: list[ToolCapability]) -> str:
    for capability in tool_capabilities:
        if capability.name == tool_name:
            return capability.output_evidence_type
    return ""
