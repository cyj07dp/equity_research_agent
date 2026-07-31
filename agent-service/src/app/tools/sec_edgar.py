from __future__ import annotations

import json
import os
import re
from html import unescape
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Callable
from urllib.request import Request, urlopen

from app.rag.sec_index import SecChunk
from app.rag.sec_retriever import retrieve_sec_chunks
from app.rag.text_splitter import split_sec_text
from app.schemas import EvidenceItem, ToolCallResult
from app.tools.alpha_vantage import _ticker_from_context_or_input
from app.tools.base import ResearchTool, ToolCapability

FetchJsonByUrl = Callable[[str], dict[str, Any]]
FetchTextByUrl = Callable[[str], str]

SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


class SecEdgarClient:
    def __init__(
        self,
        *,
        user_agent: str | None = None,
        timeout_seconds: float = 15.0,
        fetch_json: FetchJsonByUrl | None = None,
        fetch_text: FetchTextByUrl | None = None,
    ) -> None:
        self.user_agent = user_agent if user_agent is not None else os.getenv(
            "SEC_USER_AGENT",
            "equity-research-agent/0.1 contact@example.com",
        )
        self.timeout_seconds = timeout_seconds
        self._fetch_json = fetch_json
        self._fetch_text = fetch_text

    def get_json(self, url: str) -> dict[str, Any]:
        if self._fetch_json is not None:
            return self._fetch_json(url)

        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_text(self, url: str) -> str:
        if self._fetch_text is not None:
            return self._fetch_text(url)

        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,text/plain,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8", errors="replace")

    def resolve_company(self, ticker: str) -> dict[str, Any]:
        payload = self.get_json(SEC_COMPANY_TICKERS_URL)
        normalized = ticker.upper()
        for item in payload.values():
            if str(item.get("ticker", "")).upper() == normalized:
                cik = str(item.get("cik_str", "")).zfill(10)
                return {
                    "ticker": normalized,
                    "cik": cik,
                    "name": item.get("title") or normalized,
                }
        raise RuntimeError(f"Unable to resolve SEC CIK for ticker: {ticker}")

    def submissions(self, cik: str) -> dict[str, Any]:
        return self.get_json(SEC_SUBMISSIONS_URL.format(cik=cik))

    def company_facts(self, cik: str) -> dict[str, Any]:
        return self.get_json(SEC_COMPANY_FACTS_URL.format(cik=cik))


class SecFilingsSearchTool(ResearchTool):
    name = "filings_search"
    capability = ToolCapability(
        name="filings_search",
        description="Search official SEC EDGAR recent filings such as 10-K, 10-Q and 8-K for a US-listed company.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "formTypes": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
            },
        },
        outputEvidenceType="SEC_FILINGS",
    )

    def __init__(self, client: SecEdgarClient | None = None) -> None:
        self.client = client or SecEdgarClient()

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        ticker = _ticker_from_context_or_input(context=context, tool_input=tool_input)
        limit = int(tool_input.get("limit") or 5)
        form_types = {str(item).upper() for item in tool_input.get("formTypes") or []}
        try:
            company = self.client.resolve_company(ticker)
            payload = self.client.submissions(company["cik"])
            recent = payload.get("filings", {}).get("recent", {})
            filings = _recent_filings(company=company, recent=recent, form_types=form_types, limit=limit)
            if not filings:
                return _failed_call(self.name, {"ticker": ticker}, {"error": "No matching SEC filings found."}, started), []
            output = {**company, "filings": filings}
            call = _succeeded_call(self.name, {"ticker": ticker, "formTypes": list(form_types), "limit": limit}, output, started)
            summary = "; ".join(
                f"{item['form']} filed {item['filingDate']} for report date {item.get('reportDate') or 'N/A'}"
                for item in filings
            )
            return call, [
                _evidence(
                    source_type="SEC_FILINGS",
                    title=f"{ticker} SEC 最近公告",
                    summary=summary,
                    raw_content=output,
                    confidence=0.94,
                    source_url=SEC_SUBMISSIONS_URL.format(cik=company["cik"]),
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, {"ticker": ticker}, {"error": str(exc)}, started), []


class SecCompanyFactsTool(ResearchTool):
    name = "sec_company_facts"
    capability = ToolCapability(
        name="sec_company_facts",
        description="Fetch official SEC XBRL company facts for key financial statement metrics.",
        inputSchema={"type": "object", "properties": {"ticker": {"type": "string"}}},
        outputEvidenceType="SEC_COMPANY_FACTS",
    )

    def __init__(self, client: SecEdgarClient | None = None) -> None:
        self.client = client or SecEdgarClient()

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        ticker = _ticker_from_context_or_input(context=context, tool_input=tool_input)
        try:
            company = self.client.resolve_company(ticker)
            payload = self.client.company_facts(company["cik"])
            facts = _extract_core_facts(payload.get("facts", {}).get("us-gaap", {}))
            if not facts:
                return _failed_call(self.name, {"ticker": ticker}, {"error": "No supported SEC company facts found."}, started), []
            output = {**company, "entityName": payload.get("entityName"), "facts": facts}
            call = _succeeded_call(self.name, {"ticker": ticker}, output, started)
            summary = "; ".join(
                f"{name} {fact['value']} {fact.get('unit') or ''} for {fact.get('periodEnd')}"
                for name, fact in facts.items()
            )
            return call, [
                _evidence(
                    source_type="SEC_COMPANY_FACTS",
                    title=f"{ticker} SEC XBRL 核心财务事实",
                    summary=summary,
                    raw_content=output,
                    confidence=0.95,
                    source_url=SEC_COMPANY_FACTS_URL.format(cik=company["cik"]),
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, {"ticker": ticker}, {"error": str(exc)}, started), []


class SecFilingRetrievalTool(ResearchTool):
    name = "sec_filing_retriever"
    capability = ToolCapability(
        name="sec_filing_retriever",
        description=(
            "Retrieve relevant passages from official SEC filing documents for a US-listed company. "
            "Use it when the user asks about risks, business changes, management discussion, filings, or disclosure details."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "query": {"type": "string"},
                "formTypes": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
            },
        },
        outputEvidenceType="SEC_RAG",
    )

    def __init__(self, client: SecEdgarClient | None = None) -> None:
        self.client = client or SecEdgarClient()

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        ticker = _ticker_from_context_or_input(context=context, tool_input=tool_input)
        query = str(tool_input.get("query") or context.get("query") or ticker)
        limit = int(tool_input.get("limit") or 3)
        form_types = {str(item).upper() for item in tool_input.get("formTypes") or ["10-K", "10-Q", "8-K"]}
        try:
            company = self.client.resolve_company(ticker)
            payload = self.client.submissions(company["cik"])
            recent = payload.get("filings", {}).get("recent", {})
            filings = _recent_filings(company=company, recent=recent, form_types=form_types, limit=limit)
            chunks: list[SecChunk] = []
            for filing in filings:
                filing_url = filing.get("filingUrl")
                if not filing_url:
                    continue
                text = _clean_filing_text(self.client.get_text(filing_url))
                chunks.extend(_sec_chunks_from_text(
                    text=text,
                    ticker=ticker,
                    cik=company["cik"],
                    filing=filing,
                    source_url=filing_url,
                ))
            ranked_chunks = retrieve_sec_chunks(chunks, query, top_k=5)
            if not chunks:
                return _failed_call(
                    self.name,
                    {"ticker": ticker, "query": query, "formTypes": list(form_types), "limit": limit},
                    {"error": "No relevant SEC filing passages retrieved."},
                    started,
                ), []
            if not ranked_chunks:
                ranked_chunks = [
                    _zero_score_ranked_chunk(chunk)
                    for chunk in chunks[:5]
                ]
            top_chunks = [_ranked_chunk_output(item) for item in ranked_chunks]
            output = {**company, "query": query, "retrievedChunks": top_chunks}
            call = _succeeded_call(
                self.name,
                {"ticker": ticker, "query": query, "formTypes": list(form_types), "limit": limit},
                output,
                started,
            )
            summary = "；".join(
                f"{chunk['form']} {chunk['filingDate']}：{chunk['text'][:180]}"
                for chunk in top_chunks[:3]
            )
            return call, [
                _evidence(
                    source_type="SEC_RAG",
                    title=f"{ticker} SEC filing 检索片段",
                    summary=summary,
                    raw_content=output,
                    confidence=0.9,
                    source_url=top_chunks[0]["sourceUrl"],
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, {"ticker": ticker, "query": query}, {"error": str(exc)}, started), []


def _recent_filings(
    *,
    company: dict[str, Any],
    recent: dict[str, list[Any]],
    form_types: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    forms = recent.get("form") or []
    accession_numbers = recent.get("accessionNumber") or []
    filing_dates = recent.get("filingDate") or []
    report_dates = recent.get("reportDate") or []
    primary_documents = recent.get("primaryDocument") or []
    filings: list[dict[str, Any]] = []

    for index, form in enumerate(forms):
        form_name = str(form).upper()
        if form_types and form_name not in form_types:
            continue
        accession = _get(accession_numbers, index)
        document = _get(primary_documents, index)
        filing = {
            "form": form_name,
            "accessionNumber": accession,
            "filingDate": _get(filing_dates, index),
            "reportDate": _get(report_dates, index),
            "primaryDocument": document,
            "filingUrl": _filing_url(company["cik"], accession, document),
        }
        filings.append(filing)
        if len(filings) >= limit:
            break
    return filings


def _extract_core_facts(us_gaap: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fact_groups = [
        ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        ["NetIncomeLoss"],
        ["Assets"],
        ["Liabilities"],
        ["CashAndCashEquivalentsAtCarryingValue"],
        ["NetCashProvidedByUsedInOperatingActivities"],
    ]
    target_period = _target_period(us_gaap, fact_groups)
    if target_period is None:
        return {}

    facts: dict[str, dict[str, Any]] = {}
    for aliases in fact_groups:
        selected_name, selected_fact = _select_fact_for_period(
            us_gaap=us_gaap,
            aliases=aliases,
            target_period=target_period,
        )
        if selected_name is not None and selected_fact is not None:
            facts[selected_name] = selected_fact
    return facts


def _target_period(us_gaap: dict[str, Any], fact_groups: list[list[str]]) -> tuple[int, str, str] | None:
    candidates: list[dict[str, Any]] = []
    for aliases in fact_groups:
        for fact_name in aliases:
            fact = us_gaap.get(fact_name)
            if not fact:
                continue
            candidates.extend(_valid_fact_items(fact))
            break
    if not candidates:
        return None
    latest = max(candidates, key=lambda item: _period_sort_key(item))
    return int(latest.get("fy")), str(latest.get("fp")), str(latest.get("end"))


def _select_fact_for_period(
    *,
    us_gaap: dict[str, Any],
    aliases: list[str],
    target_period: tuple[int, str, str],
) -> tuple[str | None, dict[str, Any] | None]:
    for fact_name in aliases:
        fact = us_gaap.get(fact_name)
        if not fact:
            continue
        selected = _fact_for_period(fact, target_period=target_period)
        if selected is not None:
            return fact_name, selected
    return None, None


def _fact_for_period(fact: dict[str, Any], target_period: tuple[int, str, str]) -> dict[str, Any] | None:
    target_year, target_fiscal_period, target_end = target_period
    for item in _valid_fact_items(fact):
        if (
            int(item.get("fy")) == target_year
            and str(item.get("fp")) == target_fiscal_period
            and str(item.get("end")) == target_end
        ):
            return _fact_output(item=item, unit=_unit_for_fact(fact))
    return None


def _valid_fact_items(fact: dict[str, Any]) -> list[dict[str, Any]]:
    units = fact.get("units") or {}
    candidates = units.get("USD") or units.get("shares") or []
    return [
        item
        for item in candidates
        if item.get("val") is not None
        and item.get("end")
        and item.get("fy") is not None
        and item.get("fp")
        and item.get("form") in {"10-K", "10-Q"}
    ]


def _period_sort_key(item: dict[str, Any]) -> tuple[str, int, int]:
    fiscal_period_rank = {"FY": 4, "Q4": 4, "Q3": 3, "Q2": 2, "Q1": 1}.get(str(item.get("fp")), 0)
    form_rank = {"10-K": 2, "10-Q": 1}.get(str(item.get("form")), 0)
    return str(item.get("end")), fiscal_period_rank, form_rank


def _unit_for_fact(fact: dict[str, Any]) -> str:
    units = fact.get("units") or {}
    if units.get("USD"):
        return "USD"
    if units.get("shares"):
        return "shares"
    return "unknown"


def _fact_output(*, item: dict[str, Any], unit: str) -> dict[str, Any]:
    return {
        "value": item.get("val"),
        "unit": unit,
        "periodEnd": item.get("end"),
        "fiscalYear": item.get("fy"),
        "fiscalPeriod": item.get("fp"),
        "form": item.get("form"),
    }


def _get(values: list[Any], index: int) -> Any:
    if index >= len(values):
        return None
    return values[index]


def _filing_url(cik: str, accession_number: str | None, primary_document: str | None) -> str | None:
    if not accession_number or not primary_document:
        return None
    cik_no_padding = str(int(cik))
    accession_compact = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_no_padding}/{accession_compact}/{primary_document}"


def _clean_filing_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw_html)
    text = re.sub(r"(?i)</(p|div|section|tr|li|h1|h2|h3|h4)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def _sec_chunks_from_text(
    *,
    text: str,
    ticker: str,
    cik: str,
    filing: dict[str, Any],
    source_url: str,
) -> list[SecChunk]:
    return [
        SecChunk(
            ticker=ticker,
            cik=cik,
            form=str(filing.get("form") or ""),
            filing_date=str(filing.get("filingDate") or ""),
            report_date=filing.get("reportDate"),
            source_url=source_url,
            section_hint=section_hint,
            chunk_index=index,
            text=chunk,
        )
        for index, (section_hint, chunk) in enumerate(split_sec_text(text))
    ]


def _ranked_chunk_output(ranked_chunk) -> dict[str, Any]:
    chunk = ranked_chunk.chunk
    return {
        "form": chunk.form,
        "filingDate": chunk.filing_date,
        "reportDate": chunk.report_date,
        "sectionHint": chunk.section_hint,
        "score": ranked_chunk.score,
        "matchedTerms": ranked_chunk.matched_terms,
        "text": chunk.text,
        "sourceUrl": chunk.source_url,
    }


def _zero_score_ranked_chunk(chunk: SecChunk):
    from app.rag.sec_index import RankedSecChunk

    return RankedSecChunk(chunk=chunk, score=0.0, matched_terms=[])


def _ranked_chunks(
    *,
    text: str,
    query: str,
    filing: dict[str, Any],
    source_url: str,
    limit: int,
) -> list[dict[str, Any]]:
    chunks = _chunk_text(text)
    scored: list[dict[str, Any]] = []
    terms = _query_terms(query)
    for index, chunk in enumerate(chunks):
        score = _chunk_score(chunk, terms)
        if score <= 0:
            continue
        scored.append(
            {
                "form": filing.get("form"),
                "filingDate": filing.get("filingDate"),
                "reportDate": filing.get("reportDate"),
                "chunkIndex": index,
                "score": score,
                "text": chunk,
                "sourceUrl": source_url,
            }
        )
    if not scored:
        for index, chunk in enumerate(chunks[:limit]):
            scored.append(
                {
                    "form": filing.get("form"),
                    "filingDate": filing.get("filingDate"),
                    "reportDate": filing.get("reportDate"),
                    "chunkIndex": index,
                    "score": 0,
                    "text": chunk,
                    "sourceUrl": source_url,
                }
            )
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def _chunk_text(text: str, *, max_chars: int = 900) -> list[str]:
    paragraphs = [line.strip() for line in text.splitlines() if len(line.strip()) >= 80]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 > max_chars and current:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks[:80]


def _query_terms(query: str) -> set[str]:
    english_terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query.lower())
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,}", query)
    domain_terms = {
        "risk",
        "risks",
        "revenue",
        "margin",
        "cash",
        "debt",
        "competition",
        "growth",
        "风险",
        "收入",
        "利润",
        "现金",
        "债务",
        "竞争",
        "增长",
        "业务",
    }
    return set(english_terms + chinese_terms) | domain_terms


def _chunk_score(chunk: str, terms: set[str]) -> int:
    lowered = chunk.lower()
    return sum(lowered.count(term.lower()) for term in terms)


def _succeeded_call(
    tool_name: str,
    tool_input: dict[str, Any],
    output: dict[str, Any],
    started: float,
) -> ToolCallResult:
    return ToolCallResult(
        toolName=tool_name,
        input=tool_input,
        output=output,
        status="SUCCEEDED",
        latencyMs=int((perf_counter() - started) * 1000),
    )


def _failed_call(
    tool_name: str,
    tool_input: dict[str, Any],
    output: dict[str, Any],
    started: float,
) -> ToolCallResult:
    return ToolCallResult(
        toolName=tool_name,
        input=tool_input,
        output=output,
        status="FAILED",
        latencyMs=int((perf_counter() - started) * 1000),
    )


def _evidence(
    *,
    source_type: str,
    title: str,
    summary: str,
    raw_content: dict[str, Any],
    confidence: float,
    source_url: str,
) -> EvidenceItem:
    return EvidenceItem(
        sourceType=source_type,
        sourceName="SEC EDGAR",
        sourceUrl=source_url,
        title=title,
        summary=summary,
        observedAt=datetime.now(UTC).isoformat(),
        relevance=0.9,
        confidence=confidence,
        rawContent=json.dumps(raw_content, ensure_ascii=False),
    )
