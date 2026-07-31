from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecChunk:
    ticker: str
    cik: str
    form: str
    filing_date: str
    report_date: str | None
    source_url: str
    section_hint: str
    chunk_index: int
    text: str


@dataclass(frozen=True)
class RankedSecChunk:
    chunk: SecChunk
    score: float
    matched_terms: list[str]
