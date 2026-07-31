from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from io import StringIO
from time import perf_counter
from typing import Any, Callable
from urllib.request import Request, urlopen

from app.schemas import EvidenceItem, ToolCallResult
from app.tools.base import ResearchTool, ToolCapability

FetchTextByUrl = Callable[[str], str]

STOOQ_DAILY_URL = "https://stooq.com/q/d/l/?s={symbol}.us&i=d"

SECTOR_ETFS = [
    {"symbol": "XLK", "name": "Technology Select Sector SPDR Fund", "sector": "科技"},
    {"symbol": "XLF", "name": "Financial Select Sector SPDR Fund", "sector": "金融"},
    {"symbol": "XLV", "name": "Health Care Select Sector SPDR Fund", "sector": "医疗保健"},
    {"symbol": "XLY", "name": "Consumer Discretionary Select Sector SPDR Fund", "sector": "可选消费"},
    {"symbol": "XLP", "name": "Consumer Staples Select Sector SPDR Fund", "sector": "必选消费"},
    {"symbol": "XLE", "name": "Energy Select Sector SPDR Fund", "sector": "能源"},
    {"symbol": "XLI", "name": "Industrial Select Sector SPDR Fund", "sector": "工业"},
    {"symbol": "XLU", "name": "Utilities Select Sector SPDR Fund", "sector": "公用事业"},
    {"symbol": "XLB", "name": "Materials Select Sector SPDR Fund", "sector": "原材料"},
    {"symbol": "XLRE", "name": "Real Estate Select Sector SPDR Fund", "sector": "房地产"},
    {"symbol": "XLC", "name": "Communication Services Select Sector SPDR Fund", "sector": "通信服务"},
]

ETF_CATEGORIES = [
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "category": "美国大盘宽基"},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "category": "大型科技与成长"},
    {"symbol": "IWM", "name": "iShares Russell 2000 ETF", "category": "小盘股"},
    {"symbol": "SCHD", "name": "Schwab U.S. Dividend Equity ETF", "category": "股息质量"},
    {"symbol": "USMV", "name": "iShares MSCI USA Min Vol Factor ETF", "category": "低波动"},
    {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "category": "美国全市场"},
]

BEGINNER_STOCKS = [
    {"symbol": "AAPL", "name": "Apple", "theme": "消费电子与生态系统"},
    {"symbol": "MSFT", "name": "Microsoft", "theme": "云计算、企业软件和 AI"},
    {"symbol": "GOOGL", "name": "Alphabet", "theme": "搜索广告、云和 AI"},
    {"symbol": "AMZN", "name": "Amazon", "theme": "电商、云和物流网络"},
    {"symbol": "NVDA", "name": "NVIDIA", "theme": "AI 芯片和数据中心"},
    {"symbol": "BRK.B", "name": "Berkshire Hathaway", "theme": "多元化控股和保险"},
    {"symbol": "JPM", "name": "JPMorgan Chase", "theme": "大型银行与金融服务"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "theme": "医疗健康和防御性需求"},
    {"symbol": "V", "name": "Visa", "theme": "支付网络"},
    {"symbol": "COST", "name": "Costco", "theme": "会员制零售"},
]


class StooqClient:
    def __init__(self, *, timeout_seconds: float = 12.0, fetch_text: FetchTextByUrl | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        self._fetch_text = fetch_text

    def daily_prices(self, symbol: str) -> tuple[str, list[dict[str, Any]]]:
        normalized = _stooq_symbol(symbol)
        url = STOOQ_DAILY_URL.format(symbol=normalized.lower())
        if self._fetch_text is not None:
            text = self._fetch_text(url)
        else:
            request = Request(url, headers={"User-Agent": "equity-research-agent/0.1"})
            with urlopen(request, timeout=self.timeout_seconds) as response:
                text = response.read().decode("utf-8")
        return url, _parse_stooq_csv(text)


class MarketOverviewTool(ResearchTool):
    name = "market_overview"
    capability = ToolCapability(
        name="market_overview",
        description=(
            "Fetch recent US sector ETF performance from a free market data source. "
            "Use this for broad no-ticker market and sector questions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "lookbackDays": {"type": "integer"},
            },
        },
        outputEvidenceType="MARKET_DATA",
    )

    def __init__(self, client: StooqClient | None = None) -> None:
        self.client = client or StooqClient()

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        try:
            items = _performance_items(self.client, SECTOR_ETFS)
            if not items:
                return _failed_call(self.name, tool_input, {"error": "No sector ETF data returned."}, started), []
            output = {
                "provider": "Stooq",
                "region": str(tool_input.get("region") or "US").upper(),
                "sectorEtfs": sorted(items, key=lambda item: item.get("fiveDayReturnPct") or -999, reverse=True),
                "limitations": [
                    "板块表现使用美国 Select Sector SPDR ETF 作为代理。",
                    "Stooq 为免费历史价格来源，不提供完整基本面或新闻解释。",
                ],
            }
            call = _succeeded_call(self.name, tool_input, output, started)
            leaders = output["sectorEtfs"][:3]
            summary = "；".join(
                f"{item['sector']}({item['symbol']}) 最近约5个交易日 {item['fiveDayReturnPct']}%"
                for item in leaders
            )
            return call, [
                _evidence(
                    source_type="MARKET_DATA",
                    source_name="Stooq",
                    title="美股板块 ETF 近期表现",
                    summary=f"以板块 ETF 作为代理观察美股板块表现：{summary}。",
                    raw_content=output,
                    confidence=0.78,
                    source_url="https://stooq.com/",
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, tool_input, {"error": str(exc)}, started), []


class EtfDiscoveryTool(ResearchTool):
    name = "etf_discovery"
    capability = ToolCapability(
        name="etf_discovery",
        description="Fetch recent performance for common ETF categories a beginner can research.",
        inputSchema={
            "type": "object",
            "properties": {
                "riskProfile": {"type": "string"},
                "themes": {"type": "array", "items": {"type": "string"}},
            },
        },
        outputEvidenceType="MARKET_DATA",
    )

    def __init__(self, client: StooqClient | None = None) -> None:
        self.client = client or StooqClient()

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        try:
            items = _performance_items(self.client, ETF_CATEGORIES)
            if not items:
                return _failed_call(self.name, tool_input, {"error": "No ETF data returned."}, started), []
            output = {
                "provider": "Stooq",
                "categories": sorted(items, key=lambda item: item.get("fiveDayReturnPct") or -999, reverse=True),
                "howToUse": [
                    "ETF 表现可用于理解市场风格，不等于买入建议。",
                    "新手应比较分散度、行业集中度、费用率、波动和个人投资期限。",
                ],
            }
            call = _succeeded_call(self.name, tool_input, output, started)
            summary = "；".join(
                f"{item['category']}({item['symbol']}) 5日 {item['fiveDayReturnPct']}%"
                for item in output["categories"][:4]
            )
            return call, [
                _evidence(
                    source_type="MARKET_DATA",
                    source_name="Stooq",
                    title="新手常见 ETF 类别近期表现",
                    summary=f"常见 ETF 类别近期表现：{summary}。",
                    raw_content=output,
                    confidence=0.76,
                    source_url="https://stooq.com/",
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, tool_input, {"error": str(exc)}, started), []


class StockScreenerTool(ResearchTool):
    name = "stock_screener"
    capability = ToolCapability(
        name="stock_screener",
        description=(
            "Fetch recent performance for a liquid US large-cap watchlist. "
            "Use this as a free-data learning screener, not as investment advice."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "profile": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
        outputEvidenceType="MARKET_DATA",
    )

    def __init__(self, client: StooqClient | None = None) -> None:
        self.client = client or StooqClient()

    def run(
        self,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[ToolCallResult, list[EvidenceItem]]:
        started = perf_counter()
        limit = max(1, min(int(tool_input.get("limit") or 8), 10))
        try:
            items = _performance_items(self.client, BEGINNER_STOCKS)
            if not items:
                return _failed_call(self.name, tool_input, {"error": "No stock data returned."}, started), []
            candidates = sorted(items, key=lambda item: item.get("fiveDayReturnPct") or -999, reverse=True)[:limit]
            output = {
                "provider": "Stooq",
                "screeningCriteria": [
                    "使用高流动性大盘股作为学习样本。",
                    "按最近约 5 个交易日表现排序。",
                    "该工具不覆盖新闻、估值和财报，不能单独作为投资依据。",
                ],
                "candidates": candidates,
            }
            call = _succeeded_call(self.name, tool_input, output, started)
            summary = "；".join(
                f"{item['symbol']} 5日 {item['fiveDayReturnPct']}%"
                for item in candidates[:5]
            )
            return call, [
                _evidence(
                    source_type="MARKET_DATA",
                    source_name="Stooq",
                    title="学习型大盘股近期表现",
                    summary=f"大盘股学习样本按近期表现排序：{summary}。该列表不是买入建议。",
                    raw_content=output,
                    confidence=0.74,
                    source_url="https://stooq.com/",
                )
            ]
        except Exception as exc:
            return _failed_call(self.name, tool_input, {"error": str(exc)}, started), []


def market_exploration_tools() -> dict[str, ResearchTool]:
    shared_client = StooqClient()
    return {
        "market_overview": MarketOverviewTool(client=shared_client),
        "etf_discovery": EtfDiscoveryTool(client=shared_client),
        "stock_screener": StockScreenerTool(client=shared_client),
    }


def _performance_items(client: StooqClient, instruments: list[dict[str, str]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for instrument in instruments:
        try:
            source_url, prices = client.daily_prices(instrument["symbol"])
            performance = _performance_from_prices(prices)
            if performance:
                items.append({**instrument, **performance, "sourceUrl": source_url})
        except Exception:
            continue
    return items


def _parse_stooq_csv(text: str) -> list[dict[str, Any]]:
    rows = list(csv.DictReader(StringIO(text.strip())))
    prices: list[dict[str, Any]] = []
    for row in rows:
        try:
            prices.append({
                "date": row["Date"],
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(float(row.get("Volume") or 0)),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return prices


def _performance_from_prices(prices: list[dict[str, Any]]) -> dict[str, Any]:
    if len(prices) < 2:
        return {}
    latest = prices[-1]
    previous = prices[-2]
    five_day_base = prices[-6] if len(prices) >= 6 else prices[0]
    one_month_base = prices[-22] if len(prices) >= 22 else prices[0]
    return {
        "latestDate": latest["date"],
        "latestClose": round(latest["close"], 4),
        "oneDayReturnPct": _return_pct(previous["close"], latest["close"]),
        "fiveDayReturnPct": _return_pct(five_day_base["close"], latest["close"]),
        "oneMonthReturnPct": _return_pct(one_month_base["close"], latest["close"]),
        "volume": latest["volume"],
    }


def _return_pct(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return round((end - start) / start * 100, 2)


def _stooq_symbol(symbol: str) -> str:
    return symbol.upper().replace(".", "-")


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
    source_name: str,
    title: str,
    summary: str,
    raw_content: dict[str, Any],
    confidence: float,
    source_url: str,
) -> EvidenceItem:
    return EvidenceItem(
        sourceType=source_type,
        sourceName=source_name,
        sourceUrl=source_url,
        title=title,
        summary=summary,
        observedAt=datetime.now(UTC).isoformat(),
        relevance=0.84,
        confidence=confidence,
        rawContent=json.dumps(raw_content, ensure_ascii=False),
    )
