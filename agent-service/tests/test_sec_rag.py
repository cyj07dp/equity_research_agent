from app.rag.sec_index import SecChunk
from app.rag.sec_retriever import retrieve_sec_chunks
from app.rag.text_splitter import split_sec_text


def test_splitter_labels_risk_factor_section():
    text = """
    Item 1. Business
    Apple sells products and services globally through multiple channels and partners in many regions.
    Item 1A. Risk Factors
    The company faces intense competition and supply chain risks that may adversely affect revenue.
    """

    chunks = split_sec_text(text, max_chars=300)

    assert any(section == "risk_factors" for section, _ in chunks)


def test_retriever_prioritizes_risk_factor_chunk():
    chunks = [
        SecChunk("AAPL", "0000320193", "10-K", "2025-11-01", "2025-09-27", "https://example.com/1", "business", 0, "The company sells devices."),
        SecChunk("AAPL", "0000320193", "10-K", "2025-11-01", "2025-09-27", "https://example.com/2", "risk_factors", 1, "Risk Factors. The company faces competition and supply chain risks."),
    ]

    result = retrieve_sec_chunks(chunks, "主要风险和竞争", top_k=1)

    assert result[0].chunk.section_hint == "risk_factors"
    assert "competition" in result[0].matched_terms
