from uuid import UUID

from app.agent.orchestrator import ResearchAgentOrchestrator


def test_plan_and_solve_orchestrator_returns_full_trace_without_real_llm_key():
    orchestrator = ResearchAgentOrchestrator()

    result = orchestrator.run(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        query="帮我分析一下英伟达现在还能不能买",
        locale="zh-CN",
    )

    assert result.understanding
    assert result.run_status in {"COMPLETED", "DEGRADED"}
    assert result.runtime_warnings is not None
    assert result.planning_decision is not None
    assert result.plan is not None
    assert result.tool_calls is not None
    assert result.evidence is not None
    assert result.reasoning is not None
    assert result.draft_report is not None
    assert result.reflection is not None
    assert result.final_report is not None
