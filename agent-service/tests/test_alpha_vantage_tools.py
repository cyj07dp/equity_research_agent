from app.tools.alpha_vantage import (
    AlphaVantageClient,
    AlphaVantageFundamentalsTool,
    AlphaVantageMarketDataTool,
)
from app.tools.registry import ToolRegistry


def test_market_data_tool_converts_alpha_vantage_quote_to_evidence():
    client = AlphaVantageClient(
        api_key="test-key",
        fetch_json=lambda params: {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "195.64",
                "06. volume": "54321000",
                "09. change": "1.25",
                "10. change percent": "0.6432%",
                "07. latest trading day": "2026-06-05",
            }
        },
    )
    tool = AlphaVantageMarketDataTool(client=client)

    call, evidence = tool.run({"ticker": "AAPL"}, context={})

    assert call.status == "SUCCEEDED"
    assert call.output["ticker"] == "AAPL"
    assert call.output["price"] == "195.64"
    assert evidence[0].source_type == "MARKET_DATA"
    assert "195.64" in evidence[0].summary
    assert "Alpha Vantage" in evidence[0].source_name


def test_fundamentals_tool_converts_alpha_vantage_overview_to_evidence():
    client = AlphaVantageClient(
        api_key="test-key",
        fetch_json=lambda params: {
            "Symbol": "AAPL",
            "Name": "Apple Inc",
            "MarketCapitalization": "2930000000000",
            "PERatio": "30.1",
            "RevenueTTM": "383000000000",
            "ProfitMargin": "0.263",
            "EPS": "6.43",
            "AnalystTargetPrice": "210.00",
            "Currency": "USD",
        },
    )
    tool = AlphaVantageFundamentalsTool(client=client)

    call, evidence = tool.run({"ticker": "AAPL"}, context={})

    assert call.status == "SUCCEEDED"
    assert call.output["name"] == "Apple Inc"
    assert evidence[0].source_type == "FUNDAMENTALS"
    assert "PE" in evidence[0].summary
    assert "Revenue TTM" in evidence[0].summary


def test_real_data_tool_fails_without_api_key_without_fake_evidence():
    tool = AlphaVantageMarketDataTool(client=AlphaVantageClient(api_key=None))

    call, evidence = tool.run({"ticker": "AAPL"}, context={})

    assert call.status == "FAILED"
    assert "ALPHA_VANTAGE_API_KEY" in call.output["error"]
    assert evidence == []


def test_default_registry_uses_real_data_tools():
    tools = ToolRegistry().get_tools()

    assert isinstance(tools["market_data"], AlphaVantageMarketDataTool)
    assert isinstance(tools["fundamentals"], AlphaVantageFundamentalsTool)
