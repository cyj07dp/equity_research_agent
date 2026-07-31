from app.tools.base import ResearchTool, ToolCapability
from app.tools.alpha_vantage import real_data_tools


class ToolRegistry:
    def __init__(self, tools: dict[str, ResearchTool] | None = None, llm_client=None) -> None:
        self.tools = tools or real_data_tools(llm_client=llm_client)

    def get_tools(self) -> dict[str, ResearchTool]:
        return self.tools

    def capabilities(self) -> list[ToolCapability]:
        return [tool.capability for tool in self.tools.values()]
