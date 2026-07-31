from fastapi import FastAPI

from app.agent.prompts import CONVERSATION_SUMMARY_SYSTEM_PROMPT, conversation_summary_user_prompt
from app.agent.orchestrator import ResearchAgentOrchestrator
from app.llm import create_llm_client_from_env
from app.schemas import AgentRunRequest, AgentRunResult, ConversationSummary, ConversationSummaryRequest, ConversationSummaryResult

app = FastAPI(title="Equity Research Agent Service")
orchestrator = ResearchAgentOrchestrator()
summary_llm_client = create_llm_client_from_env()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agent-runs", response_model=AgentRunResult)
def create_agent_run(request: AgentRunRequest) -> AgentRunResult:
    return orchestrator.run(
        run_id=request.run_id,
        query=request.query,
        locale=request.locale,
        conversation_messages=request.conversation_messages,
        user_preferences=request.user_preferences,
    )


@app.post("/conversation-summary", response_model=ConversationSummaryResult)
def create_conversation_summary(request: ConversationSummaryRequest) -> ConversationSummaryResult:
    try:
        summary = summary_llm_client.generate_structured(
            system_prompt=CONVERSATION_SUMMARY_SYSTEM_PROMPT,
            user_prompt=conversation_summary_user_prompt(
                messages=[message.model_dump() for message in request.messages],
                existing_summary=request.existing_summary,
                locale=request.locale,
            ),
            response_model=ConversationSummary,
        )
        return ConversationSummaryResult(summary=summary)
    except Exception:
        return ConversationSummaryResult(summary=_fallback_conversation_summary(request))


def _fallback_conversation_summary(request: ConversationSummaryRequest) -> ConversationSummary:
    important_history = [
        f"{message.role}: {' '.join(message.content.split())[:160]}"
        for message in request.messages[-12:]
        if message.content.strip()
    ]
    return ConversationSummary(
        userProfile={},
        researchContext={},
        openQuestions=[],
        importantHistory=important_history,
        notEvidence=["该摘要由历史对话压缩生成，只用于理解上下文，不是市场事实或投资证据。"],
    )
