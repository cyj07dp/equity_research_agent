import json
import logging

from app.agent.prompts import EVIDENCE_REASONING_SYSTEM_PROMPT
from app.llm import LLMClient
from app.schemas import (
    AnalystReasoning,
    DataSufficiencyResult,
    EvidenceAssessment,
    EvidenceDiagnostics,
    EvidenceItem,
    EvidenceReasoningResult,
    PlanningDecision,
    QueryUnderstanding,
    ReportInstructions,
    ToolCallResult,
)

logger = logging.getLogger("uvicorn.error")


class ReasoningEngine:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def reason(
        self,
        *,
        query: str,
        understanding: QueryUnderstanding,
        planning_decision: PlanningDecision | None = None,
        tool_calls: list[ToolCallResult] | None = None,
        evidence: list[EvidenceItem],
    ) -> EvidenceReasoningResult:
        diagnostics = collect_evidence_diagnostics(
            planning_decision=planning_decision,
            tool_calls=tool_calls or [],
            evidence=evidence,
        )
        try:
            return self.llm_client.generate_structured(
                system_prompt=EVIDENCE_REASONING_SYSTEM_PROMPT,
                user_prompt=json.dumps(
                    {
                        "query": query,
                        "understanding": understanding.model_dump(by_alias=True),
                        "planningDecision": None
                        if planning_decision is None
                        else planning_decision.model_dump(by_alias=True),
                        "evidenceDiagnostics": diagnostics.model_dump(by_alias=True),
                        "toolCalls": [
                            item.model_dump(by_alias=True)
                            for item in (tool_calls or [])
                        ],
                        "evidence": [
                            item.model_dump(by_alias=True)
                            for item in evidence
                        ],
                    },
                    ensure_ascii=False,
                ),
                response_model=EvidenceReasoningResult,
            )
        except Exception as exc:
            logger.warning("LLM fallback stage=evidence_reasoning reason=%s", exc)
            data_sufficiency = _default_data_sufficiency(
                planning_decision=planning_decision,
                diagnostics=diagnostics,
                evidence=evidence,
            )
            reasoning = AnalystReasoning(
                thesis="当前证据不足以形成可靠投研判断。",
                supportingPoints=[],
                risks=["缺少可验证的市场、新闻或财务 evidence。"] if not evidence else [],
                valuationNotes=[],
                missingData=data_sufficiency.missing_evidence,
                uncertainty="LLM reasoning 不可用或 evidence 不完整。",
            )
            return EvidenceReasoningResult(
                answerability=data_sufficiency.status,
                evidenceAssessment=EvidenceAssessment(
                    summary=data_sufficiency.summary,
                    usableEvidence=data_sufficiency.available_evidence,
                    missingEvidence=data_sufficiency.missing_evidence,
                    failedTools=diagnostics.failed_tools,
                    unsupportedQuestions=[] if evidence else ["当前问题缺少可用 evidence 支撑。"],
                ),
                dataSufficiency=data_sufficiency,
                reasoning=reasoning,
                reportInstructions=ReportInstructions(
                    tone="cautious",
                    mustSay=[data_sufficiency.summary],
                    mustNotSay=["直接给出买入、卖出或持有建议。"],
                    revisedSections=[],
                ),
            )


def collect_evidence_diagnostics(
    *,
    planning_decision: PlanningDecision | None,
    tool_calls: list[ToolCallResult],
    evidence: list[EvidenceItem],
) -> EvidenceDiagnostics:
    failed_tools = [
        call.tool_name
        for call in tool_calls
        if call.status.upper() == "FAILED"
    ]
    source_types = list(dict.fromkeys(item.source_type for item in evidence))
    planned_tool_names = []
    if planning_decision is not None:
        planned_tool_names = [
            step.tool_name or step.tool or ""
            for step in planning_decision.steps
        ]
        planned_tool_names = [name for name in planned_tool_names if name]
    executed_tool_names = list(dict.fromkeys(call.tool_name for call in tool_calls))
    notes: list[str] = []
    if planning_decision is not None and planning_decision.needs_tools and not tool_calls:
        notes.append("计划需要工具证据，但没有执行任何工具。")
    if failed_tools:
        notes.append("存在工具失败：" + ", ".join(dict.fromkeys(failed_tools)) + "。")
    if not evidence:
        notes.append("未获得可用于支撑回答的 evidence。")
    return EvidenceDiagnostics(
        toolCallCount=len(tool_calls),
        evidenceCount=len(evidence),
        failedTools=list(dict.fromkeys(failed_tools)),
        evidenceSourceTypes=source_types,
        plannedToolNames=planned_tool_names,
        executedToolNames=executed_tool_names,
        notes=notes,
    )


def _default_data_sufficiency(
    *,
    planning_decision: PlanningDecision | None,
    diagnostics: EvidenceDiagnostics,
    evidence: list[EvidenceItem],
) -> DataSufficiencyResult:
    expected = planning_decision.evidence_needs if planning_decision is not None else []
    available = [f"{item.source_type}: {item.title}" for item in evidence]
    missing = diagnostics.notes
    if not missing and not evidence:
        missing = ["未获得可用于支撑回答的 evidence。"]
    if not evidence:
        status = "INSUFFICIENT"
    elif diagnostics.failed_tools or missing:
        status = "PARTIAL"
    else:
        status = "SUFFICIENT"
    if status == "SUFFICIENT":
        summary = "当前 evidence 足以支撑基于已执行工具的回答。"
    elif status == "INSUFFICIENT":
        summary = "当前 evidence 不足，不能可靠回答用户问题。"
    else:
        summary = "当前 evidence 只能支持部分回答：" + "；".join(missing[:3])
    return DataSufficiencyResult(
        status=status,
        summary=summary,
        expectedEvidence=expected,
        availableEvidence=available,
        missingEvidence=missing,
        coverageNotes=diagnostics.notes,
    )
