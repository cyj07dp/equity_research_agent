from app.tools.market_exploration import EtfDiscoveryTool, MarketOverviewTool, StockScreenerTool, StooqClient


def test_market_overview_returns_sector_etf_performance_with_links():
    call, evidence = MarketOverviewTool(client=_fake_stooq_client()).run(tool_input={}, context={})

    assert call.status == "SUCCEEDED"
    assert call.tool_name == "market_overview"
    assert call.output["provider"] == "Stooq"
    assert call.output["sectorEtfs"][0]["sourceUrl"].startswith("https://stooq.com/")
    assert evidence[0].source_type == "MARKET_DATA"
    assert evidence[0].source_name == "Stooq"
    assert evidence[0].source_url == "https://stooq.com/"
    assert "5个交易日" in evidence[0].summary


def test_etf_discovery_returns_recent_etf_category_performance():
    call, evidence = EtfDiscoveryTool(client=_fake_stooq_client()).run(tool_input={"riskProfile": "beginner"}, context={})

    assert call.status == "SUCCEEDED"
    assert evidence[0].source_type == "MARKET_DATA"
    assert "ETF 类别近期表现" in evidence[0].title
    assert "不是买入建议" not in evidence[0].summary
    assert call.output["categories"][0]["fiveDayReturnPct"] is not None


def test_stock_screener_returns_watchlist_sorted_by_recent_performance():
    call, evidence = StockScreenerTool(client=_fake_stooq_client()).run(tool_input={"limit": 3}, context={})

    assert call.status == "SUCCEEDED"
    assert len(call.output["candidates"]) == 3
    assert evidence[0].source_type == "MARKET_DATA"
    returns = [item["fiveDayReturnPct"] for item in call.output["candidates"]]
    assert returns == sorted(returns, reverse=True)
    assert "不是买入建议" in evidence[0].summary


def test_market_overview_fails_when_provider_returns_no_rows():
    call, evidence = MarketOverviewTool(client=StooqClient(fetch_text=lambda _: "Date,Open,High,Low,Close,Volume\n")).run(
        tool_input={},
        context={},
    )

    assert call.status == "FAILED"
    assert evidence == []


def _fake_stooq_client() -> StooqClient:
    def fetch_text(url: str) -> str:
        symbol_bias = sum(ord(char) for char in url) % 7
        rows = ["Date,Open,High,Low,Close,Volume"]
        base = 100 + symbol_bias
        for index in range(30):
            close = base + index * (1 + symbol_bias / 20)
            rows.append(f"2026-05-{index + 1:02d},{close - 1},{close + 1},{close - 2},{close},1000000")
        return "\n".join(rows)

    return StooqClient(fetch_text=fetch_text)
