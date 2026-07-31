from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.schemas import EvidenceItem, ToolCallResult
from app.tools.base import ResearchTool, ToolCapability
from app.tools.company_profile import CompanySearchTool, company_from_context_or_input

if TYPE_CHECKING:
    from app.llm import LLMClient

FetchJson = Callable[[dict[str, str]], dict[str, Any]]


class AlphaVantageClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://www.alphavantage.co/query",
        timeout_seconds: float = 15.0,
        fetch_json: FetchJson | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("ALPHA_VANTAGE_API_KEY")
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self._fetch_json = fetch_json

    def get(self, params: dict[str, str]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("ALPHA_VANTAGE_API_KEY is not configured.")

        request_params = {**params, "apikey": self.api_key}
        if self._fetch_json is not None:
            return self._fetch_json(request_params)

        url = f"{self.base_url}?{urlencode(request_params)}"
        request = Request(url, headers={"User-Agent": "equity-research-agent/0.1"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class AlphaVantageMarketDataTool(ResearchTool):
    name = "market_data"
    capability = ToolCapability(
        name="market_data",
        description="Fetch real latest quote data, price, volume and daily change from Alpha Vantage.",
        inputSchema={"type": "object", "properties": {"ticker": {"type": "string"}}},
        outputEvidenceType="MARKET_DATA",
    )

    def __init__(self, client: AlphaVantageClient | None = None) -> None:
        self.client = client or AlphaVantageClient()

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        ticker = _ticker_from_context_or_input(context=context, tool_input=tool_input)
        try:
            payload = self.client.get({"function": "GLOBAL_QUOTE", "symbol": ticker})
            quote = payload.get("Global Quote") or {}
            if not quote:
                return _failed_call(self.name, {"ticker": ticker}, payload, started), []
            output = {
                "ticker": quote.get("01. symbol") or ticker,
                "open": quote.get("02. open"),
                "high": quote.get("03. high"),
                "low": quote.get("04. low"),
                "price": quote.get("05. price"),
                "volume": quote.get("06. volume"),
                "latestTradingDay": quote.get("07. latest trading day"),
                "previousClose": quote.get("08. previous close"),
                "change": quote.get("09. change"),
                "changePercent": quote.get("10. change percent"),
            }
            call = _succeeded_call(self.name, {"ticker": ticker}, output, started)
            summary = (
                f"{output['ticker']} 最新价格 {output['price']}，当日涨跌 {output['change']} "
                f"({output['changePercent']})，成交量 {output['volume']}，"
                f"交易日 {output['latestTradingDay']}。"
            )
            return call, [
                _evidence(
                    source_type="MARKET_DATA",
                    title=f"{ticker} 最新行情",
                    summary=summary,
                    raw_content=output,
                    confidence=0.86,
                    source_url=_alpha_vantage_url(function="GLOBAL_QUOTE", symbol=ticker),
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, {"ticker": ticker}, {"error": str(exc)}, started), []


class AlphaVantageFundamentalsTool(ResearchTool):
    name = "fundamentals"
    capability = ToolCapability(
        name="fundamentals",
        description="Fetch real company overview, valuation and profitability metrics from Alpha Vantage.",
        inputSchema={"type": "object", "properties": {"ticker": {"type": "string"}}},
        outputEvidenceType="FUNDAMENTALS",
    )

    def __init__(self, client: AlphaVantageClient | None = None) -> None:
        self.client = client or AlphaVantageClient()

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        ticker = _ticker_from_context_or_input(context=context, tool_input=tool_input)
        try:
            payload = self.client.get({"function": "OVERVIEW", "symbol": ticker})
            if not payload.get("Symbol"):
                return _failed_call(self.name, {"ticker": ticker}, payload, started), []
            output = {
                "ticker": payload.get("Symbol"),
                "name": payload.get("Name"),
                "currency": payload.get("Currency"),
                "marketCapitalization": payload.get("MarketCapitalization"),
                "peRatio": payload.get("PERatio"),
                "pegRatio": payload.get("PEGRatio"),
                "priceToBookRatio": payload.get("PriceToBookRatio"),
                "revenueTTM": payload.get("RevenueTTM"),
                "profitMargin": payload.get("ProfitMargin"),
                "operatingMarginTTM": payload.get("OperatingMarginTTM"),
                "eps": payload.get("EPS"),
                "analystTargetPrice": payload.get("AnalystTargetPrice"),
                "quarterlyEarningsGrowthYOY": payload.get("QuarterlyEarningsGrowthYOY"),
                "quarterlyRevenueGrowthYOY": payload.get("QuarterlyRevenueGrowthYOY"),
            }
            call = _succeeded_call(self.name, {"ticker": ticker}, output, started)
            summary = (
                f"{output['name']} ({output['ticker']}) Market Cap {output['marketCapitalization']} "
                f"{output['currency'] or ''}，PE {output['peRatio']}，Revenue TTM {output['revenueTTM']}，"
                f"Profit Margin {output['profitMargin']}，EPS {output['eps']}，"
                f"Analyst Target Price {output['analystTargetPrice']}。"
            )
            return call, [
                _evidence(
                    source_type="FUNDAMENTALS",
                    title=f"{ticker} 基本面与估值指标",
                    summary=summary,
                    raw_content=output,
                    confidence=0.84,
                    source_url=_alpha_vantage_url(function="OVERVIEW", symbol=ticker),
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, {"ticker": ticker}, {"error": str(exc)}, started), []


class AlphaVantageNewsSearchTool(ResearchTool):
    name = "news_search"
    capability = ToolCapability(
        name="news_search",
        description="Fetch real recent company news and market narratives from Alpha Vantage news sentiment.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "ticker": {"type": "string"},
            },
        },
        outputEvidenceType="NEWS",
    )

    def __init__(self, client: AlphaVantageClient | None = None) -> None:
        self.client = client or AlphaVantageClient()

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        ticker = _ticker_from_context_or_input(context=context, tool_input=tool_input)
        try:
            payload = self.client.get(
                {
                    "function": "NEWS_SENTIMENT",
                    "tickers": ticker,
                    "limit": "5",
                    "sort": "LATEST",
                }
            )
            feed = payload.get("feed") or []
            if not feed:
                return _failed_call(self.name, {"ticker": ticker}, payload, started), []
            articles = [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "timePublished": item.get("time_published"),
                    "source": item.get("source"),
                    "summary": item.get("summary"),
                    "overallSentimentLabel": item.get("overall_sentiment_label"),
                }
                for item in feed[:5]
            ]
            output = {"ticker": ticker, "articles": articles}
            call = _succeeded_call(self.name, {"ticker": ticker}, output, started)
            article_summaries = [
                f"{item.get('title')} ({item.get('source')}, sentiment={item.get('overallSentimentLabel')})"
                for item in articles
                if item.get("title")
            ]
            return call, [
                _evidence(
                    source_type="NEWS",
                    title=f"{ticker} 近期新闻",
                    summary="; ".join(article_summaries),
                    raw_content=output,
                    confidence=0.78,
                    source_url=_alpha_vantage_url(function="NEWS_SENTIMENT", tickers=ticker),
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, {"ticker": ticker}, {"error": str(exc)}, started), []


def real_data_tools(
    client: AlphaVantageClient | None = None,
    llm_client: LLMClient | None = None,
) -> dict[str, ResearchTool]:
    from app.tools.market_exploration import market_exploration_tools
    from app.tools.sec_edgar import SecCompanyFactsTool, SecFilingRetrievalTool, SecFilingsSearchTool
    from app.tools.web_article import WebArticleReaderTool

    alpha_client = client or AlphaVantageClient()
    tools = {
        "company_search": CompanySearchTool(),
        "market_data": AlphaVantageMarketDataTool(client=alpha_client),
        "news_search": AlphaVantageNewsSearchTool(client=alpha_client),
        "fundamentals": AlphaVantageFundamentalsTool(client=alpha_client),
        "filings_search": SecFilingsSearchTool(),
        "sec_company_facts": SecCompanyFactsTool(),
        "sec_filing_retriever": SecFilingRetrievalTool(),
        "web_article_reader": WebArticleReaderTool(llm_client=llm_client),
    }
    tools.update(market_exploration_tools())
    return tools


def _ticker_from_context_or_input(
    *,
    context: dict[str, Any],
    tool_input: dict[str, Any],
) -> str:
    company = company_from_context_or_input(context=context, tool_input=tool_input)
    ticker = company.ticker if company.ticker != "UNKNOWN" else str(tool_input.get("ticker") or "UNKNOWN")
    return ticker.upper()


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
        sourceName="Alpha Vantage",
        sourceUrl=source_url,
        title=title,
        summary=summary,
        observedAt=datetime.now(UTC).isoformat(),
        relevance=0.86,
        confidence=confidence,
        rawContent=json.dumps(raw_content, ensure_ascii=False),
    )


def _alpha_vantage_url(**params: str) -> str:
    return f"https://www.alphavantage.co/query?{urlencode(params)}"
