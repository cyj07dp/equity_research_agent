import json
from pathlib import Path


def test_eval_cases_have_required_fields():
    cases_path = Path(__file__).parents[1] / "evals" / "cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))

    assert cases
    for case in cases:
        assert case["id"]
        assert case["query"]
        assert isinstance(case["expectedTools"], list)
        assert isinstance(case["requiredEvidenceTypes"], list)
        assert isinstance(case["requiredCitationDomains"], list)
        assert isinstance(case["forbiddenPhrases"], list)


def test_sec_rag_eval_cases_have_required_fields():
    cases_path = Path(__file__).parents[1] / "evals" / "sec_rag_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))

    assert cases
    for case in cases:
        assert case["id"]
        assert case["ticker"]
        assert case["query"]
        assert case["expectedSection"]
        assert isinstance(case["mustMatchTerms"], list)
