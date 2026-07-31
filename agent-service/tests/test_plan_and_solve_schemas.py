from uuid import UUID

from app.schemas import (
    AgentRunResult,
    AnalystReasoning,
    PlanningDecision,
    QueryUnderstanding,
    ReflectionResult,
    ResearchPlan,
    ResearchPlanStep,
    ResearchReport,
    ReportSection,
)


def test_plan_and_solve_result_schema_accepts_full_agent_trace():
    understanding = QueryUnderstanding.model_validate(
        {
            "taskType": "INVESTMENT_THESIS",
            "companies": [
                {
                    "mention": "英伟达",
                    "canonicalName": "NVIDIA Corporation",
                    "candidates": [
                        {
                            "ticker": "NVDA",
                            "exchange": "NASDAQ",
                            "market": "US",
                            "confidence": 0.97,
                        }
                    ],
                    "needsClarification": False,
                    "ambiguityReason": None,
                }
            ],
            "timeHorizon": "medium_term",
            "analysisAspects": ["valuation", "fundamentals", "recent_news", "risks"],
            "comparisonMode": False,
            "userDecisionContext": "whether_to_buy",
            "requiresLiveData": True,
            "outputStyle": "research_memo",
            "constraints": [],
            "clarificationQuestions": [],
            "confidence": 0.93,
        }
    )
    plan = ResearchPlan(
        objective="判断 NVIDIA 当前投资吸引力",
        steps=[
            ResearchPlanStep(
                stepId="market-context",
                toolName="market_data",
                purpose="查看近期市场表现",
                toolInput={"ticker": "NVDA"},
                expectedEvidence="近期价格、成交量和波动",
                required=True,
            )
        ],
    )
    planning_decision = PlanningDecision(
        answerability="TOOL_REQUIRED",
        needsTools=True,
        needsClarification=False,
        allowedTools=["market_data"],
        evidenceNeeds=["近期价格、成交量和波动"],
        clarificationQuestions=[],
        maxSteps=1,
        rationale="需要市场数据支持判断。",
        objective=plan.objective,
        steps=plan.steps,
    )
    reasoning = AnalystReasoning(
        thesis="证据支持谨慎乐观，但估值风险需要单独标注。",
        supportingPoints=["市场表现显示关注度较高。"],
        risks=["估值对增长预期敏感。"],
        valuationNotes=[],
        missingData=[],
        uncertainty="当前 evidence 仍不完整。",
    )
    reflection = ReflectionResult(
        passed=True,
        unsupportedClaims=[],
        missingData=[],
        overconfidentStatements=[],
        revisionInstructions=[],
    )
    report = ResearchReport(
        title="NVIDIA 投研 Agent Memo",
        companySummary="NVIDIA Corporation 是本次研究对象。",
        questionUnderstanding="用户关注 NVIDIA 当前投资吸引力。",
        keyFindings=["证据支持谨慎分析。"],
        opportunities=["增长预期仍是主要机会。"],
        risks=["估值风险较高。"],
        evidenceSummary="市场数据、新闻和基本面 evidence 已聚合。",
        uncertainty="当前工具数据仍有限。",
        citations=["https://example.com/market/NVDA"],
        nonAdvisoryStatement="本报告为 AI Agent 生成的研究摘要，不构成投资建议。",
        sections=[
            ReportSection(title="核心结论", content="证据支持谨慎分析。"),
            ReportSection(title="风险与限制", content="估值风险较高，当前工具数据仍有限。"),
        ],
    )
    result = AgentRunResult(
        runId=UUID("00000000-0000-0000-0000-000000000000"),
        query="英伟达还能不能买？",
        locale="zh-CN",
        understanding=understanding,
        planningDecision=planning_decision,
        runStatus="COMPLETED",
        clarificationQuestions=[],
        plan=plan,
        toolCalls=[],
        evidence=[],
        reasoning=reasoning,
        draftReport=report,
        reflection=reflection,
        finalReport=report,
    )

    assert result.understanding.task_type == "INVESTMENT_THESIS"
    assert result.planning_decision.allowed_tools == ["market_data"]
    assert result.run_status == "COMPLETED"
    assert result.plan.steps[0].tool_name == "market_data"
    assert result.final_report.title == "NVIDIA 投研 Agent Memo"
    assert result.final_report.sections[0].title == "核心结论"
