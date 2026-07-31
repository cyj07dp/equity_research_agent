import math
import re

from app.rag.sec_index import RankedSecChunk, SecChunk


DOMAIN_TERMS = {
    "risk": ["risk", "risks", "uncertainty", "adverse", "material", "风险", "不确定"],
    "competition": ["competition", "competitive", "competitors", "竞争"],
    "margin": ["margin", "gross margin", "operating margin", "利润率", "毛利率"],
    "revenue": ["revenue", "sales", "net sales", "收入"],
    "supply_chain": ["supply", "supplier", "manufacturing", "供应链"],
}


def retrieve_sec_chunks(chunks: list[SecChunk], query: str, *, top_k: int = 5) -> list[RankedSecChunk]:
    terms = query_terms(query)
    ranked = []
    for chunk in chunks:
        score, matched = score_chunk(chunk, terms)
        if score > 0:
            ranked.append(RankedSecChunk(chunk=chunk, score=score, matched_terms=matched))
    return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]


def query_terms(query: str) -> list[str]:
    terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query.lower())
    terms += re.findall(r"[\u4e00-\u9fff]{2,}", query)
    lowered = query.lower()
    for key, values in DOMAIN_TERMS.items():
        if key in lowered or any(value in query for value in values):
            terms.extend(values)
    if "风险" in query or "risk" in lowered:
        terms.extend(DOMAIN_TERMS["risk"])
    return list(dict.fromkeys(terms))


def score_chunk(chunk: SecChunk, terms: list[str]) -> tuple[float, list[str]]:
    text = chunk.text.lower()
    matched = []
    score = 0.0
    for term in terms:
        count = text.count(term.lower())
        if count:
            matched.append(term)
            score += 1.0 + math.log(count)
    if chunk.section_hint == "risk_factors" and any(term in {"risk", "risks", "风险"} for term in matched):
        score += 3.0
    return score, matched
