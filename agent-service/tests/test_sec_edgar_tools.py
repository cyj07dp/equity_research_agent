from app.tools.registry import ToolRegistry
from app.tools.sec_edgar import SecCompanyFactsTool, SecEdgarClient, SecFilingRetrievalTool, SecFilingsSearchTool


def test_sec_filings_search_returns_recent_filings_evidence():
    client = SecEdgarClient(
        user_agent="test@example.com",
        fetch_json=lambda url: _sec_payload(url),
    )
    tool = SecFilingsSearchTool(client=client)

    call, evidence = tool.run({"ticker": "AAPL", "limit": 2}, context={})

    assert call.status == "SUCCEEDED"
    assert call.output["ticker"] == "AAPL"
    assert call.output["cik"] == "0000320193"
    assert call.output["filings"][0]["form"] == "10-K"
    assert evidence[0].source_type == "SEC_FILINGS"
    assert "10-K" in evidence[0].summary
    assert "sec.gov" in evidence[0].source_url


def test_sec_company_facts_summarizes_core_financial_facts():
    client = SecEdgarClient(
        user_agent="test@example.com",
        fetch_json=lambda url: _sec_payload(url),
    )
    tool = SecCompanyFactsTool(client=client)

    call, evidence = tool.run({"ticker": "AAPL"}, context={})

    assert call.status == "SUCCEEDED"
    assert call.output["ticker"] == "AAPL"
    assert call.output["facts"]["Revenues"]["value"] == 383000
    assert evidence[0].source_type == "SEC_COMPANY_FACTS"
    assert "Revenues" in evidence[0].summary
    assert "NetIncomeLoss" in evidence[0].summary


def test_sec_company_facts_prefers_consistent_recent_fiscal_period_and_revenue_alias():
    client = SecEdgarClient(
        user_agent="test@example.com",
        fetch_json=lambda url: _sec_payload_with_stale_revenue(url),
    )
    tool = SecCompanyFactsTool(client=client)

    call, evidence = tool.run({"ticker": "AAPL"}, context={})

    assert call.status == "SUCCEEDED"
    assert "Revenues" not in call.output["facts"]
    assert call.output["facts"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["fiscalYear"] == 2026
    assert call.output["facts"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["fiscalPeriod"] == "Q2"
    assert call.output["facts"]["NetIncomeLoss"]["fiscalPeriod"] == "Q2"
    assert "2018-09-29" not in evidence[0].summary


def test_sec_filing_retriever_returns_relevant_document_passages():
    client = SecEdgarClient(
        user_agent="test@example.com",
        fetch_json=lambda url: _sec_payload(url),
        fetch_text=lambda url: _sec_filing_text(url),
    )
    tool = SecFilingRetrievalTool(client=client)

    call, evidence = tool.run({"ticker": "AAPL", "query": "risk competition", "limit": 1}, context={})

    assert call.status == "SUCCEEDED"
    assert call.output["retrievedChunks"]
    assert call.output["retrievedChunks"][0]["form"] == "10-K"
    assert "competition" in call.output["retrievedChunks"][0]["text"].lower()
    assert evidence[0].source_type == "SEC_RAG"
    assert evidence[0].source_url.endswith("aapl-20250927.htm")


def test_sec_tool_fails_with_clear_error_when_company_not_found():
    client = SecEdgarClient(
        user_agent="test@example.com",
        fetch_json=lambda url: {"0": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."}},
    )
    tool = SecFilingsSearchTool(client=client)

    call, evidence = tool.run({"ticker": "UNKNOWN"}, context={})

    assert call.status == "FAILED"
    assert "Unable to resolve SEC CIK" in call.output["error"]
    assert evidence == []


def test_default_registry_includes_sec_tools():
    tools = ToolRegistry().get_tools()

    assert isinstance(tools["filings_search"], SecFilingsSearchTool)
    assert isinstance(tools["sec_company_facts"], SecCompanyFactsTool)
    assert isinstance(tools["sec_filing_retriever"], SecFilingRetrievalTool)


def _sec_payload(url: str):
    if url.endswith("/files/company_tickers.json"):
        return {"0": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."}}
    if url.endswith("/submissions/CIK0000320193.json"):
        return {
            "name": "Apple Inc.",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-25-000079", "0000320193-25-000008"],
                    "filingDate": ["2025-11-01", "2025-08-01"],
                    "reportDate": ["2025-09-27", "2025-06-28"],
                    "form": ["10-K", "10-Q"],
                    "primaryDocument": ["aapl-20250927.htm", "aapl-20250628.htm"],
                }
            },
        }
    if url.endswith("/api/xbrl/companyfacts/CIK0000320193.json"):
        return {
            "entityName": "Apple Inc.",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"fy": 2025, "fp": "FY", "form": "10-K", "end": "2025-09-27", "val": 383000}
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"fy": 2025, "fp": "FY", "form": "10-K", "end": "2025-09-27", "val": 97000}
                            ]
                        }
                    },
                }
            },
        }
    raise AssertionError(f"Unexpected URL: {url}")


def _sec_payload_with_stale_revenue(url: str):
    if url.endswith("/files/company_tickers.json"):
        return {"0": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."}}
    if url.endswith("/api/xbrl/companyfacts/CIK0000320193.json"):
        return {
            "entityName": "Apple Inc.",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"fy": 2018, "fp": "FY", "form": "10-K", "end": "2018-09-29", "val": 265595}
                            ]
                        }
                    },
                    "RevenueFromContractWithCustomerExcludingAssessedTax": {
                        "units": {
                            "USD": [
                                {"fy": 2026, "fp": "Q2", "form": "10-Q", "end": "2026-03-28", "val": 254940}
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"fy": 2026, "fp": "Q2", "form": "10-Q", "end": "2026-03-28", "val": 71675}
                            ]
                        }
                    },
                    "Assets": {
                        "units": {
                            "USD": [
                                {"fy": 2026, "fp": "Q2", "form": "10-Q", "end": "2026-03-28", "val": 371082}
                            ]
                        }
                    },
                }
            },
        }
    raise AssertionError(f"Unexpected URL: {url}")


def _sec_filing_text(url: str) -> str:
    if url.endswith("aapl-20250927.htm"):
        return """
        <html><body>
        <p>Business overview: The company sells products and services globally through multiple channels.</p>
        <p>Risk Factors: The company faces intense competition across smartphones, personal computers and services.
        These risks may affect revenue growth, margins and operating results in future periods.</p>
        </body></html>
        """
    raise AssertionError(f"Unexpected filing URL: {url}")
