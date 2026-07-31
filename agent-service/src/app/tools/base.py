from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.schemas import EvidenceItem, ToolCallResult


class ToolCapability(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(alias="inputSchema")
    when_to_use: str = Field(default="", alias="whenToUse")
    output_evidence_type: str = Field(default="", alias="outputEvidenceType")
    limitations: list[str] = Field(default_factory=list)
    can_run_in_parallel: bool = Field(default=True, alias="canRunInParallel")
    requires_external_api_key: bool = Field(default=False, alias="requiresExternalApiKey")

    model_config = {"populate_by_name": True}


class ResearchTool(ABC):
    name: str
    capability: ToolCapability

    @abstractmethod
    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        raise NotImplementedError
