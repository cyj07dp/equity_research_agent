import logging

from app.agent.prompts import REPLANNING_SYSTEM_PROMPT, replanning_user_prompt
from app.llm import LLMClient
from app.schemas import EvidenceItem, PlanningDecision, QueryUnderstanding, ReplanningDecision, ToolCallResult
from app.tools.base import ToolCapability

logger = logging.getLogger("uvicorn.error")


class ConditionalReplanner:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def replan(
        self,
        *,
        query: str,
        understanding: QueryUnderstanding,
        planning_decision: PlanningDecision,
        tool_calls: list[ToolCallResult],
        evidence: list[EvidenceItem],
        tool_capabilities: list[ToolCapability],
    ) -> ReplanningDecision:
        try:
            decision = self.llm_client.generate_structured(
                system_prompt=REPLANNING_SYSTEM_PROMPT,
                user_prompt=replanning_user_prompt(
                    query=query,
                    understanding=understanding.model_dump(by_alias=True),
                    planning_decision=planning_decision.model_dump(by_alias=True),
                    tool_calls=[call.model_dump(by_alias=True) for call in tool_calls],
                    evidence=[item.model_dump(by_alias=True) for item in evidence],
                    available_tools=[capability.model_dump(by_alias=True) for capability in tool_capabilities],
                ),
                response_model=ReplanningDecision,
            )
            return _normalize_replanning_decision(decision)
        except Exception as exc:
            logger.warning("LLM fallback stage=conditional_replanning reason=%s", exc)
            return ReplanningDecision(
                action="CONTINUE_WITH_AVAILABLE_EVIDENCE",
                rationale=f"Replanner unavailable: {exc}",
                additionalSteps=[],
                clarificationQuestions=[],
                capabilityGap="",
            )


def _normalize_replanning_decision(decision: ReplanningDecision) -> ReplanningDecision:
    action = decision.action.upper()
    if action not in {
        "CONTINUE_WITH_AVAILABLE_EVIDENCE",
        "CALL_ADDITIONAL_TOOLS",
        "ASK_CLARIFICATION",
        "CAPABILITY_GAP",
    }:
        action = "CONTINUE_WITH_AVAILABLE_EVIDENCE"
    return ReplanningDecision(
        action=action,
        rationale=decision.rationale,
        additionalSteps=decision.additional_steps[:3] if action == "CALL_ADDITIONAL_TOOLS" else [],
        clarificationQuestions=decision.clarification_questions if action == "ASK_CLARIFICATION" else [],
        capabilityGap=decision.capability_gap if action == "CAPABILITY_GAP" else "",
    )
