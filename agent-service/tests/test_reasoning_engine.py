from app.agent.reasoning_engine import ReasoningEngine
from app.schemas import (
    AnalystReasoning,
    DataSufficiencyResult,
    EvidenceAssessment,
    EvidenceReasoningResult,
    QueryUnderstanding,
    ReportInstructions,
    ResearchTaskType,
)


class StubLLMClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_reasoning_engine_uses_llm_over_evidence():
    expected = _evidence_reasoning_result()
    llm_client = StubLLMClient(expected)
    engine = ReasoningEngine(llm_client=llm_client)

    result = engine.reason(query="英伟达还能不能买？", understanding=_understanding(), evidence=[])

    assert result.reasoning.thesis == "证据支持谨慎乐观。"
    assert result.data_sufficiency.status == "PARTIAL"
    assert llm_client.calls[0]["response_model"] is EvidenceReasoningResult
    assert "evidenceDiagnostics" in llm_client.calls[0]["user_prompt"]
    assert "toolCalls" in llm_client.calls[0]["user_prompt"]


def test_reasoning_engine_returns_default_when_llm_fails():
    engine = ReasoningEngine(llm_client=StubLLMClient(RuntimeError("LLM unavailable")))

    result = engine.reason(query="英伟达还能不能买？", understanding=_understanding(), evidence=[])

    assert result.reasoning.missing_data
    assert result.data_sufficiency.status == "INSUFFICIENT"
    assert "证据不足" in result.reasoning.thesis


def _evidence_reasoning_result():
    reasoning = AnalystReasoning(
        thesis="证据支持谨慎乐观。",
        supportingPoints=["市场表现活跃。"],
        risks=["估值敏感。"],
        valuationNotes=[],
        missingData=[],
        uncertainty="缺少完整估值数据。",
    )
    return EvidenceReasoningResult(
        answerability="PARTIAL",
        evidenceAssessment=EvidenceAssessment(
            summary="证据只能部分支撑。",
            usableEvidence=["市场表现活跃。"],
            missingEvidence=["完整估值数据"],
            failedTools=[],
            unsupportedQuestions=["不能回答是否买入。"],
        ),
        dataSufficiency=DataSufficiencyResult(
            status="PARTIAL",
            summary="当前 evidence 只能支持部分回答。",
            expectedEvidence=[],
            availableEvidence=[],
            missingEvidence=["完整估值数据"],
            coverageNotes=[],
        ),
        reasoning=reasoning,
        reportInstructions=ReportInstructions(
            tone="cautious",
            mustSay=["证据只能部分支撑。"],
            mustNotSay=["建议买入。"],
            revisedSections=[],
        ),
    )


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
