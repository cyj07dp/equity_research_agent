from datetime import date

from app.agent.prompts import QUERY_UNDERSTANDING_SYSTEM_PROMPT, query_understanding_user_prompt
from app.llm import LLMClient
from app.schemas import QueryUnderstanding, ResearchTaskType


class QueryUnderstandingService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def understand(
        self,
        query: str,
        *,
        current_date: str | None = None,
        timezone: str = "Asia/Shanghai",
        locale: str = "zh-CN",
    ) -> QueryUnderstanding:
        effective_current_date = current_date or date.today().isoformat()
        try:
            return self.llm_client.generate_structured(
                system_prompt=QUERY_UNDERSTANDING_SYSTEM_PROMPT,
                user_prompt=query_understanding_user_prompt(
                    query,
                    current_date=effective_current_date,
                    timezone=timezone,
                    locale=locale,
                ),
                response_model=QueryUnderstanding,
            )
        except Exception:
            return QueryUnderstanding(
                taskType=ResearchTaskType.INVESTMENT_THESIS,
                intentSummary="LLM 不可用，无法可靠理解用户问题。",
                intentBreakdown=[
                    {
                        "point": "QueryUnderstanding LLM 调用不可用。",
                        "planningImpact": "应进入保守澄清或默认兜底路径，避免生成无依据研究结论。",
                    }
                ],
                entities=[],
                companies=[],
                timeHorizon="unspecified",
                analysisAspects=["market_data", "recent_news", "fundamentals", "risks"],
                comparisonMode=False,
                userDecisionContext="general_research",
                requiresLiveData=True,
                outputStyle="research_memo",
                constraints=[],
                clarificationQuestions=[],
                confidence=0.1,
            )
