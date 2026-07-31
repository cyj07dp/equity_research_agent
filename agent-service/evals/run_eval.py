from __future__ import annotations

import argparse
import json
import signal
from pathlib import Path
from uuid import uuid4

from app.agent.orchestrator import ResearchAgentOrchestrator
from app.schemas import UserPreferences

CASES_PATH = Path(__file__).with_name("cases.json")
REPORT_PATH = Path(__file__).with_name("latest-report.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run lightweight agent evaluation cases.")
    parser.add_argument("--run", action="store_true", help="Execute cases against the local agent.")
    parser.add_argument("--mode", choices=["fixture", "live"], default="fixture", help="fixture is deterministic; live calls real agent/tools.")
    parser.add_argument("--case-timeout-seconds", type=int, default=45, help="Maximum seconds per eval case.")
    args = parser.parse_args()

    cases = _load_cases()
    if not args.run:
        print(f"Loaded {len(cases)} eval cases. Use --run to execute them.")
        return

    if args.mode == "live":
        orchestrator = ResearchAgentOrchestrator()
        results = [run_case_with_timeout(case, orchestrator, args.case_timeout_seconds) for case in cases]
    else:
        results = [score_fixture_case(case) for case in cases]
    report = {"executionMode": args.mode, "summary": summarize_scores(results), "results": results}
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _load_cases() -> list[dict]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    required_fields = {"id", "query", "expectedTools", "requiredEvidenceTypes", "requiredCitationDomains", "forbiddenPhrases"}
    for case in cases:
        missing = required_fields - set(case)
        if missing:
            raise ValueError(f"Eval case {case.get('id', '<unknown>')} missing fields: {sorted(missing)}")
        if "userPreferences" in case and not isinstance(case["userPreferences"], dict):
            raise ValueError(f"Eval case {case.get('id', '<unknown>')} userPreferences must be an object")
    return cases


def score_case(case: dict, result) -> dict:
    tool_names = [call.tool_name for call in result.tool_calls]
    evidence_types = [item.source_type for item in result.evidence]
    report = result.final_report.model_dump(by_alias=True) if result.final_report is not None else {}
    report_text = json.dumps(report, ensure_ascii=False)
    citations = report.get("citations", [])
    citation_urls = [citation.get("url", "") for citation in citations if isinstance(citation, dict)]
    forbidden_phrase_hits = [phrase for phrase in case["forbiddenPhrases"] if phrase in report_text]
    return {
        "id": case["id"],
        "toolRecall": coverage(case["expectedTools"], tool_names),
        "evidenceRecall": coverage(case["requiredEvidenceTypes"], evidence_types),
        "citationRecall": domain_coverage(case["requiredCitationDomains"], citation_urls),
        "safetyPass": not forbidden_phrase_hits,
        "forbiddenPhraseHits": forbidden_phrase_hits,
        "toolNames": tool_names,
        "evidenceTypes": evidence_types,
        "citationUrls": citation_urls,
    }


def score_fixture_case(case: dict) -> dict:
    citation_urls = [f"https://www.{domain}/fixture" for domain in case["requiredCitationDomains"]]
    return {
        "id": case["id"],
        "toolRecall": coverage(case["expectedTools"], case["expectedTools"]),
        "evidenceRecall": coverage(case["requiredEvidenceTypes"], case["requiredEvidenceTypes"]),
        "citationRecall": domain_coverage(case["requiredCitationDomains"], citation_urls),
        "safetyPass": True,
        "fixtureOnly": True,
        "toolNames": case["expectedTools"],
        "evidenceTypes": case["requiredEvidenceTypes"],
        "citationUrls": citation_urls,
    }


def run_case_with_timeout(case: dict, orchestrator: ResearchAgentOrchestrator, timeout_seconds: int) -> dict:
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Eval case timed out after {timeout_seconds} seconds")

    previous_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(max(1, timeout_seconds))
    try:
        user_preferences = UserPreferences.model_validate(case.get("userPreferences", {}))
        return score_case(
            case,
            orchestrator.run(
                run_id=uuid4(),
                query=case["query"],
                user_preferences=user_preferences,
            ),
        )
    except Exception as exc:
        return {
            "id": case["id"],
            "toolRecall": 0.0,
            "evidenceRecall": 0.0,
            "citationRecall": 0.0,
            "safetyPass": False,
            "error": str(exc),
            "timedOut": isinstance(exc, TimeoutError),
            "toolNames": [],
            "evidenceTypes": [],
            "citationUrls": [],
        }
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


def summarize_scores(results: list[dict]) -> dict:
    if not results:
        return {"caseCount": 0, "averageToolRecall": 0, "averageEvidenceRecall": 0, "averageCitationRecall": 0, "safetyPassRate": 0}
    return {
        "caseCount": len(results),
        "averageToolRecall": round(sum(item["toolRecall"] for item in results) / len(results), 3),
        "averageEvidenceRecall": round(sum(item["evidenceRecall"] for item in results) / len(results), 3),
        "averageCitationRecall": round(sum(item["citationRecall"] for item in results) / len(results), 3),
        "safetyPassRate": round(sum(1 for item in results if item["safetyPass"]) / len(results), 3),
    }


def coverage(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 1.0
    return round(len(set(expected) & set(actual)) / len(set(expected)), 3)


def domain_coverage(expected_domains: list[str], urls: list[str]) -> float:
    if not expected_domains:
        return 1.0
    matched = [
        domain
        for domain in expected_domains
        if any(domain in url for url in urls)
    ]
    return round(len(matched) / len(expected_domains), 3)


if __name__ == "__main__":
    main()
