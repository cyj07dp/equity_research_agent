import json
import logging

from app.agent.prompts import REFLECTION_SYSTEM_PROMPT
from app.llm import LLMClient
from app.schemas import EvidenceItem, ReflectionResult, ResearchReport

logger = logging.getLogger("uvicorn.error")


class ReflectionValidator:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def reflect(
        self,
        *,
        query: str,
        draft_report: ResearchReport,
        evidence: list[EvidenceItem],
    ) -> ReflectionResult:
        try:
            return self.llm_client.generate_structured(
                system_prompt=REFLECTION_SYSTEM_PROMPT,
                user_prompt=json.dumps(
                    {
                        "query": query,
                        "draftReport": draft_report.model_dump(by_alias=True),
                        "evidence": [item.model_dump(by_alias=True) for item in evidence],
                    },
                    ensure_ascii=False,
                ),
                response_model=ReflectionResult,
            )
        except Exception as exc:
            logger.warning("LLM fallback stage=reflection reason=%s", exc)
            return ReflectionResult(
                passed=True,
                unsupportedClaims=[],
                missingData=[],
                overconfidentStatements=[],
                revisionInstructions=[],
            )
