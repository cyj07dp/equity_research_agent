from time import perf_counter

from app.schemas import EvidenceItem, ResearchPlan, ToolCallResult
from app.tools.base import ResearchTool


class ToolRouter:
    def __init__(self, tools: dict[str, ResearchTool]) -> None:
        self.tools = tools

    def execute(
        self,
        *,
        plan: ResearchPlan,
        context: dict,
    ) -> tuple[list[ToolCallResult], list[EvidenceItem]]:
        tool_calls: list[ToolCallResult] = []
        evidence: list[EvidenceItem] = []

        for step in plan.steps:
            tool_name = step.tool_name or step.tool
            if tool_name is None:
                tool_calls.append(_failed_tool_call("UNKNOWN", step.tool_input, "Plan step has no tool name."))
                continue

            tool = self.tools.get(tool_name)
            if tool is None:
                tool_calls.append(_failed_tool_call(tool_name, step.tool_input))
                continue

            try:
                call, items = tool.run(tool_input=step.tool_input, context=context)
            except Exception as exc:
                call = _failed_tool_call(tool_name, step.tool_input, str(exc))
                items = []
            tool_calls.append(call)
            evidence.extend(items)

        return tool_calls, evidence


def _failed_tool_call(
    tool_name: str,
    tool_input: dict,
    message: str = "Tool is not registered.",
) -> ToolCallResult:
    started = perf_counter()
    return ToolCallResult(
        toolName=tool_name,
        input=tool_input,
        output={"error": message},
        status="FAILED",
        latencyMs=int((perf_counter() - started) * 1000),
    )
