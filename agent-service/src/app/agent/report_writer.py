import json
import logging

from app.agent.prompts import REPORT_GENERATION_SYSTEM_PROMPT, REPORT_REVISION_SYSTEM_PROMPT
from app.llm import LLMClient
from app.schemas import (
    AnalystReasoning,
    DataSufficiencyResult,
    EvidenceItem,
    PlanningDecision,
    ReflectionResult,
    ReportInstructions,
    ReportCitation,
    ResearchReport,
    ReportSection,
)

logger = logging.getLogger("uvicorn.error")


class ReportWriter:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def write_from_reasoning(
        self,
        *,
        query: str,
        planning_decision: PlanningDecision | None = None,
        data_sufficiency: DataSufficiencyResult | None = None,
        report_instructions: ReportInstructions | None = None,
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
                            "answerPlan": None
                            if planning_decision is None
                            else planning_decision.answer_plan.model_dump(by_alias=True),
                            "dataSufficiency": None
                            if data_sufficiency is None
                            else data_sufficiency.model_dump(by_alias=True),
                            "reportInstructions": None
                            if report_instructions is None
                            else report_instructions.model_dump(by_alias=True),
                            "reasoning": reasoning.model_dump(by_alias=True),
                            "evidence": [item.model_dump(by_alias=True) for item in evidence],
                        },
                        ensure_ascii=False,
                    ),
                    response_model=ResearchReport,
                )
            except Exception as exc:
                logger.warning("LLM fallback stage=report_drafting reason=%s", exc)
        return self._default_report_from_reasoning(query=query, reasoning=reasoning, evidence=evidence)

    def revise_with_reflection(
        self,
        *,
        query: str,
        draft_report: ResearchReport,
        reflection: ReflectionResult,
        evidence: list[EvidenceItem],
    ) -> ResearchReport:
        if self.llm_client is None:
            return draft_report
        try:
            return self.llm_client.generate_structured(
                system_prompt=REPORT_REVISION_SYSTEM_PROMPT,
                user_prompt=json.dumps(
                    {
                        "query": query,
                        "draftReport": draft_report.model_dump(by_alias=True),
                        "reflection": reflection.model_dump(by_alias=True),
                        "revisionInstructions": reflection.revision_instructions,
                        "evidence": [item.model_dump(by_alias=True) for item in evidence],
                    },
                    ensure_ascii=False,
                ),
                response_model=ResearchReport,
            )
        except Exception as exc:
            logger.warning("LLM fallback stage=report_revision reason=%s", exc)
            return draft_report

    def _default_report_from_reasoning(
        self,
        *,
        query: str,
        reasoning: AnalystReasoning,
        evidence: list[EvidenceItem],
    ) -> ResearchReport:
        citations = [
            ReportCitation(
                id=index + 1,
                title=item.title or item.source_name,
                sourceName=item.source_name,
                url=item.source_url or "",
                supports=item.summary,
            )
            for index, item in enumerate(evidence[:6])
        ]
        citation_ids = [item.id for item in citations]

        return ResearchReport(
            title="投研 Agent Memo",
            answerSummary="当前证据不足以形成完整投研判断，只能基于已获得 evidence 给出有限分析。请补充研究对象、期限或风险承受能力后继续追问。",
            companySummary="本报告基于当前 query understanding 和工具 evidence 生成。",
            questionUnderstanding=f"用户问题：{query}",
            keyFindings=[],
            opportunities=[],
            risks=[],
            evidenceSummary=" ".join(item.summary for item in evidence),
            uncertainty=reasoning.uncertainty,
            citations=citations,
            nonAdvisoryStatement="本报告为 AI Agent 生成的研究摘要，不构成投资建议。",
            sections=[
                ReportSection(title="核心回答", content=reasoning.thesis, citations=citation_ids),
                ReportSection(title="依据", content=" ".join(reasoning.supporting_points), citations=citation_ids),
                ReportSection(title="限制", content=" ".join(reasoning.missing_data) or reasoning.uncertainty),
            ],
        )
