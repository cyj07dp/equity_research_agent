from datetime import UTC, datetime
import json

from app.agent.reflection_validator import ReflectionValidator
from app.agent.report_writer import ReportWriter
from app.agent.orchestrator import ResearchAgentOrchestrator
from app.agent.tool_router import ToolRouter
from app.schemas import AgentPlanDecision, AnalystReasoning, EvidenceItem, ReflectionResult, ResearchReport, ResearchPlanStep, ToolCallResult
from app.tools.base import ResearchTool, ToolCapability


class StubLLMClient:
    def __init__(self, response):
        self.response = response

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class RecordingLLMClient:
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
        return self.response


def test_report_writer_can_use_llm_draft():
    report = _report()
    writer = ReportWriter(llm_client=StubLLMClient(report))

    result = writer.write_from_reasoning(query="英伟达还能不能买？", reasoning=_reasoning(), evidence=[])

    assert result.title == "NVIDIA 投研 Agent Memo"


def test_reflection_validator_uses_llm_result():
    reflection = ReflectionResult(
        passed=False,
        unsupportedClaims=["增长确定性过强"],
        missingData=["valuation data"],
        overconfidentStatements=["一定会继续上涨"],
        revisionInstructions=["降低结论确定性。"],
    )
    validator = ReflectionValidator(llm_client=StubLLMClient(reflection))

    result = validator.reflect(query="英伟达还能不能买？", draft_report=_report(), evidence=[])

    assert result.passed is False
    assert result.revision_instructions == ["降低结论确定性。"]


def test_report_writer_revises_draft_with_reflection_feedback():
    revised_report = _report(title="修订后的报告", opportunities=["证据不足，暂不形成机会判断。"])
    llm_client = RecordingLLMClient(revised_report)
    writer = ReportWriter(llm_client=llm_client)
    reflection = ReflectionResult(
        passed=False,
        unsupportedClaims=["增长确定性过强"],
        missingData=["valuation data"],
        overconfidentStatements=["一定会继续上涨"],
        revisionInstructions=["删除缺少证据的增长判断。"],
    )

    result = writer.revise_with_reflection(
        query="英伟达还能不能买？",
        draft_report=_report(),
        reflection=reflection,
        evidence=[],
    )

    assert result.title == "修订后的报告"
    assert result.opportunities == ["证据不足，暂不形成机会判断。"]
    assert llm_client.calls
    assert "revisionInstructions" in llm_client.calls[0]["user_prompt"]


def test_orchestrator_uses_revised_report_when_reflection_fails():
    orchestrator = ResearchAgentOrchestrator()
    draft_report = _report(title="初稿")
    revised_report = _report(title="修订稿", opportunities=["证据不足，暂不形成机会判断。"])
    reflection = ReflectionResult(
        passed=False,
        unsupportedClaims=["增长确定性过强"],
        missingData=["valuation data"],
        overconfidentStatements=["一定会继续上涨"],
        revisionInstructions=["删除缺少证据的增长判断。"],
    )
    orchestrator.report_writer.write_from_reasoning = lambda **kwargs: draft_report
    orchestrator.report_writer.revise_with_reflection = lambda **kwargs: revised_report
    orchestrator.reflection_validator.reflect = lambda **kwargs: reflection
    orchestrator.agent_planner.plan = lambda **kwargs: _agent_plan_decision()
    orchestrator.tool_router = ToolRouter(tools={"market_overview": _EvidenceTool()})

    result = orchestrator.run(
        run_id="00000000-0000-0000-0000-000000000000",
        query="英伟达还能不能买？",
    )

    assert result.draft_report.title == "初稿"
    assert result.final_report.title == "修订稿"


def test_orchestrator_uses_revised_report_when_reflection_has_instructions_even_if_passed():
    orchestrator = ResearchAgentOrchestrator()
    draft_report = _report(title="初稿")
    revised_report = _report(title="补充新手策略后的报告", opportunities=["补充定投和分散研究框架。"])
    reflection = ReflectionResult(
        passed=True,
        unsupportedClaims=[],
        missingData=["缺少新手购买策略说明"],
        overconfidentStatements=[],
        revisionInstructions=["补充定投、分散和风险承受能力说明。"],
    )
    orchestrator.report_writer.write_from_reasoning = lambda **kwargs: draft_report
    orchestrator.report_writer.revise_with_reflection = lambda **kwargs: revised_report
    orchestrator.reflection_validator.reflect = lambda **kwargs: reflection
    orchestrator.agent_planner.plan = lambda **kwargs: _agent_plan_decision()
    orchestrator.tool_router = ToolRouter(tools={"market_overview": _EvidenceTool()})

    result = orchestrator.run(
        run_id="00000000-0000-0000-0000-000000000003",
        query="我是美股小白，应该怎么买？",
    )

    assert result.reflection.passed is True
    assert result.draft_report.title == "初稿"
    assert result.final_report.title == "补充新手策略后的报告"


def _reasoning():
    return AnalystReasoning(
        thesis="证据支持谨慎乐观。",
        supportingPoints=["市场表现活跃。"],
        risks=["估值敏感。"],
        valuationNotes=[],
        missingData=[],
        uncertainty="缺少完整估值数据。",
    )


class _EvidenceTool(ResearchTool):
    name = "market_overview"
    capability = ToolCapability(name="market_overview", description="Static evidence", inputSchema={})

    def run(self, tool_input: dict, context: dict):
        return (
            ToolCallResult(
                toolName=self.name,
                input=tool_input,
                output={"summary": "market evidence"},
                status="SUCCEEDED",
                latencyMs=1,
            ),
            [
                EvidenceItem(
                    sourceType="MARKET_DATA",
                    sourceName="TestProvider",
                    sourceUrl="https://example.com",
                    title="market evidence",
                    summary="market evidence",
                    observedAt=datetime.now(UTC).isoformat(),
                    relevance=0.8,
                    confidence=0.8,
                    rawContent=json.dumps({"summary": "market evidence"}, ensure_ascii=False),
                )
            ],
        )


def _agent_plan_decision():
    return AgentPlanDecision(
        intent={
            "summary": "测试用最小工具计划。",
            "entities": [],
            "companies": [],
            "constraints": [],
            "needsLiveData": True,
            "riskLevel": "NORMAL",
        },
        answerability="PARTIAL_WITH_TOOLS",
        needsTools=True,
        needsClarification=False,
        allowedTools=["market_overview"],
        evidenceNeeds=["market_context"],
        clarificationQuestions=[],
        maxSteps=1,
        rationale="测试用最小工具计划。",
        objective="测试用最小工具计划。",
        steps=[
            ResearchPlanStep(
                stepId="overview",
                toolName="market_overview",
                purpose="获取市场探索框架",
                toolInput={},
                expectedEvidence="market_context",
                required=True,
            )
        ],
    )


def _report(title="NVIDIA 投研 Agent Memo", opportunities=None):
    return ResearchReport(
        title=title,
        companySummary="NVIDIA 是本次研究对象。",
        questionUnderstanding="用户关注 NVIDIA 当前投资吸引力。",
        keyFindings=["证据支持谨慎乐观。"],
        opportunities=opportunities or ["增长预期是主要机会。"],
        risks=["估值敏感。"],
        evidenceSummary="已聚合 evidence。",
        uncertainty="缺少完整估值数据。",
        citations=["https://example.com/market/NVDA"],
        nonAdvisoryStatement="本报告为 AI Agent 生成的研究摘要，不构成投资建议。",
    )
