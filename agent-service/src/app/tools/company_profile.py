from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from app.schemas import EvidenceItem, ToolCallResult
from app.tools.base import ResearchTool, ToolCapability


@dataclass(frozen=True)
class CompanyProfile:
    name: str
    ticker: str
    exchange: str
    confidence: float
    source: str

    def to_output(self) -> dict[str, Any]:
        return asdict(self)


class CompanySearchTool(ResearchTool):
    name = "company_search"
    capability = ToolCapability(
        name="company_search",
        description="Resolve a user-mentioned public company or tradable security to a ticker candidate from query understanding.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string"}, "ticker": {"type": "string"}}},
        outputEvidenceType="COMPANY_PROFILE",
    )

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        query = str(context.get("query", tool_input.get("query", "")))
        company = company_from_context_or_input(context=context, tool_input=tool_input)
        output = company.to_output()
        call = ToolCallResult(
            toolName=self.name,
            input={"query": query, **({"ticker": company.ticker} if company.ticker != "UNKNOWN" else {})},
            output=output,
            status="SUCCEEDED",
            latencyMs=int((perf_counter() - started) * 1000),
        )
        evidence = EvidenceItem(
            sourceType="COMPANY_PROFILE",
            sourceName="Query Understanding",
            sourceUrl=None,
            title=f"{company.name} 公司识别结果",
            summary=f"系统将用户问题解析为 {company.name}，ticker 为 {company.ticker}，交易所为 {company.exchange}。",
            observedAt=datetime.now(UTC).isoformat(),
            relevance=0.95,
            confidence=company.confidence,
            rawContent=json.dumps(output, ensure_ascii=False),
        )
        return call, [evidence]


def company_from_context_or_input(
    *,
    context: dict[str, Any],
    tool_input: dict[str, Any],
) -> CompanyProfile:
    understanding = context.get("understanding")
    if understanding is not None and getattr(understanding, "companies", None):
        first_company = understanding.companies[0]
        if first_company.candidates:
            first_candidate = max(first_company.candidates, key=lambda candidate: candidate.confidence)
            return CompanyProfile(
                name=first_company.canonical_name,
                ticker=first_candidate.ticker,
                exchange=first_candidate.exchange,
                confidence=first_candidate.confidence,
                source="query-understanding",
            )

    ticker = str(tool_input.get("ticker") or "UNKNOWN").upper()
    return CompanyProfile(
        name=str(tool_input.get("name") or "Unknown Public Company"),
        ticker=ticker,
        exchange=str(tool_input.get("exchange") or "UNKNOWN"),
        confidence=0.1,
        source="tool-input-fallback",
    )
