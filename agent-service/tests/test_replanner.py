from app.agent.replanner import ConditionalReplanner
from app.schemas import ReplanningDecision, ResearchPlanStep
from app.tools.base import ToolCapability


class StubLLMClient:
    def __init__(self, response):
        self.response = response

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        return self.response


def test_replanner_normalizes_additional_tool_steps():
    replanner = ConditionalReplanner(
        llm_client=StubLLMClient(
            ReplanningDecision(
                action="call_additional_tools",
                rationale="新闻工具失败，尝试读取用户提供网页。",
                additionalSteps=[
                    ResearchPlanStep(
                        stepId="article",
                        toolName="web_article_reader",
                        toolInput={"url": "https://example.com/article"},
                    )
                ],
                clarificationQuestions=["unused"],
            )
        )
    )

    result = replanner.replan(
        query="分析这篇文章",
        understanding=_minimal_model_dump_like(),
        planning_decision=_minimal_planning_decision(),
        tool_calls=[],
        evidence=[],
        tool_capabilities=[ToolCapability(name="web_article_reader", description="Read article.", inputSchema={})],
    )

    assert result.action == "CALL_ADDITIONAL_TOOLS"
    assert [step.tool_name for step in result.additional_steps] == ["web_article_reader"]
    assert result.clarification_questions == []


def _minimal_model_dump_like():
    from app.schemas import QueryUnderstanding, ResearchTaskType

    return QueryUnderstanding(
        taskType=ResearchTaskType.RECENT_NEWS,
        intentSummary="用户希望分析文章。",
        intentBreakdown=[],
        entities=[],
        companies=[],
        timeHorizon="current",
        analysisAspects=["news"],
        comparisonMode=False,
        userDecisionContext="article_research",
        requiresLiveData=False,
        outputStyle="research_memo",
        constraints=[],
        clarificationQuestions=[],
        confidence=0.8,
    )


def _minimal_planning_decision():
    from app.schemas import PlanningDecision

    return PlanningDecision(
        answerability="TOOL_REQUIRED",
        needsTools=True,
        needsClarification=False,
        allowedTools=["web_article_reader"],
        evidenceNeeds=["article_content"],
        clarificationQuestions=[],
        maxSteps=1,
        rationale="需要读取文章。",
        objective="分析文章。",
        steps=[],
    )
