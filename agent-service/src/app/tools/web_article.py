from __future__ import annotations

import html
import json
import re
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Callable
from urllib.request import Request, urlopen

from app.agent.prompts import ARTICLE_SUMMARY_SYSTEM_PROMPT
from app.llm import LLMClient
from app.schemas import ArticleSummary, EvidenceItem, ToolCallResult
from app.tools.base import ResearchTool, ToolCapability

FetchText = Callable[[str], str]


class WebArticleReaderTool(ResearchTool):
    name = "web_article_reader"
    capability = ToolCapability(
        name="web_article_reader",
        description=(
            "Read a public web article URL, extract title and main text, and optionally organize it into "
            "structured article evidence with the LLM."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "maxChars": {"type": "integer"},
            },
            "required": ["url"],
        },
        outputEvidenceType="WEB_ARTICLE",
    )

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        fetch_text: FetchText | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self._fetch_text = fetch_text
        self.llm_client = llm_client

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        url = str(tool_input.get("url") or "").strip()
        max_chars = int(tool_input.get("maxChars") or 5000)
        if not url:
            return _failed_call(self.name, tool_input, {"error": "url is required."}, started), []
        try:
            html_text = self._fetch(url)
            title = _extract_title(html_text) or url
            text = _extract_text(html_text, max_chars=max_chars)
            if not text:
                return _failed_call(self.name, {"url": url}, {"error": "No readable article text extracted."}, started), []
            output = {
                "url": url,
                "title": title,
                "text": text,
                "textLength": len(text),
                "extractionProvider": "web_article_reader",
            }
            structured_summary = self._summarize_article(url=url, title=title, text=text)
            summary_text = text[:1000]
            if structured_summary is not None:
                output["structuredSummary"] = structured_summary.model_dump(by_alias=True)
                output["summaryProvider"] = "llm"
                summary_text = _summary_text_from_structured_summary(structured_summary)
            else:
                output["summaryProvider"] = "extracted_text"
            call = _succeeded_call(self.name, {"url": url, "maxChars": max_chars}, output, started)
            return call, [
                EvidenceItem(
                    sourceType="WEB_ARTICLE",
                    sourceName=_source_name_from_url(url),
                    sourceUrl=url,
                    title=title,
                    summary=summary_text,
                    observedAt=datetime.now(UTC).isoformat(),
                    relevance=0.8,
                    confidence=0.76 if structured_summary is not None else 0.68,
                    rawContent=json.dumps(output, ensure_ascii=False),
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, {"url": url}, {"error": str(exc)}, started), []

    def _fetch(self, url: str) -> str:
        if self._fetch_text is not None:
            return self._fetch_text(url)
        request = Request(
            url,
            headers={
                "User-Agent": "equity-research-agent/0.1",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    def _summarize_article(self, *, url: str, title: str, text: str) -> ArticleSummary | None:
        if self.llm_client is None:
            return None
        try:
            return self.llm_client.generate_structured(
                system_prompt=ARTICLE_SUMMARY_SYSTEM_PROMPT,
                user_prompt=json.dumps(
                    {
                        "url": url,
                        "title": title,
                        "text": text,
                    },
                    ensure_ascii=False,
                ),
                response_model=ArticleSummary,
            )
        except Exception:
            return None


def _extract_title(html_text: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        match = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _normalize_text(_strip_tags(match.group(1)))


def _extract_text(html_text: str, *, max_chars: int) -> str:
    cleaned = re.sub(r"(?is)<script.*?</script>", " ", html_text)
    cleaned = re.sub(r"(?is)<style.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?is)<nav.*?</nav>", " ", cleaned)
    cleaned = re.sub(r"(?is)<footer.*?</footer>", " ", cleaned)
    article_match = re.search(r"(?is)<article[^>]*>(.*?)</article>", cleaned)
    if article_match:
        cleaned = article_match.group(1)
    cleaned = re.sub(r"(?i)</(p|div|section|h1|h2|h3|li)>", "\n", cleaned)
    text = _normalize_text(_strip_tags(cleaned))
    return text[:max_chars]


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(value))


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _source_name_from_url(url: str) -> str:
    match = re.match(r"https?://([^/]+)", url)
    return match.group(1) if match else "Web Article"


def _summary_text_from_structured_summary(summary: ArticleSummary) -> str:
    parts = []
    if summary.main_points:
        parts.append("要点：" + "；".join(summary.main_points))
    if summary.facts:
        parts.append("事实：" + "；".join(summary.facts))
    if summary.dates:
        parts.append("日期：" + "；".join(summary.dates))
    if summary.companies:
        parts.append("公司：" + "；".join(summary.companies))
    if summary.risks:
        parts.append("风险：" + "；".join(summary.risks))
    if summary.limitations:
        parts.append("限制：" + "；".join(summary.limitations))
    return " ".join(parts)


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
