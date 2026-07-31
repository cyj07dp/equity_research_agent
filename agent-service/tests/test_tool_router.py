from app.agent.tool_router import ToolRouter
from app.schemas import EvidenceItem, ResearchPlan, ResearchPlanStep, ToolCallResult
from app.tools.base import ResearchTool, ToolCapability


class StubTool(ResearchTool):
    name = "market_data"
    capability = ToolCapability(
        name="market_data",
        description="Fetch market data.",
        inputSchema={"type": "object"},
    )

    def run(self, tool_input, context):
        return (
            ToolCallResult(
                toolName="market_data",
                input=tool_input,
                output={"summary": "NVDA moved actively."},
                status="SUCCEEDED",
                latencyMs=1,
            ),
            [
                EvidenceItem(
                    sourceType="MARKET_DATA",
                    sourceName="Stub Market Tool",
                    sourceUrl="https://example.com/market/NVDA",
                    title="NVDA market data",
                    summary="NVDA moved actively.",
                    observedAt="2026-06-04T00:00:00+00:00",
                    relevance=0.8,
                    confidence=0.7,
                    rawContent='{"summary":"NVDA moved actively."}',
                )
            ],
        )


def test_tool_router_executes_registered_plan_steps():
    router = ToolRouter(tools={"market_data": StubTool()})
    plan = ResearchPlan(
        objective="Analyze NVDA",
        steps=[
            ResearchPlanStep(
                stepId="market",
                toolName="market_data",
                purpose="Fetch market context",
                toolInput={"ticker": "NVDA"},
                expectedEvidence="market evidence",
                required=True,
            )
        ],
    )

    tool_calls, evidence = router.execute(plan=plan, context={"query": "英伟达还能不能买？"})

    assert tool_calls[0].tool_name == "market_data"
    assert evidence[0].source_type == "MARKET_DATA"


def test_tool_router_records_unknown_tool_without_crashing():
    router = ToolRouter(tools={})
    plan = ResearchPlan(
        objective="Analyze NVDA",
        steps=[
            ResearchPlanStep(
                stepId="unknown",
                toolName="unknown_tool",
                purpose="Try unavailable tool",
                toolInput={},
                expectedEvidence="unknown evidence",
                required=False,
            )
        ],
    )

    tool_calls, evidence = router.execute(plan=plan, context={})

    assert tool_calls[0].tool_name == "unknown_tool"
    assert tool_calls[0].status == "FAILED"
    assert evidence == []
