from app.agent.query_understanding import QueryUnderstandingService
from app.schemas import QueryUnderstanding, ResearchTaskType


class StubLLMClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_query_understanding_uses_llm_semantics():
    llm_response = QueryUnderstanding.model_validate(
        {
            "taskType": "INVESTMENT_THESIS",
            "companies": [
                {
                    "mention": "英伟达",
                    "canonicalName": "NVIDIA Corporation",
                    "candidates": [
                        {
                            "ticker": "NVDA",
                            "exchange": "NASDAQ",
                            "market": "US",
                            "confidence": 0.97,
                        }
                    ],
                    "needsClarification": False,
                    "ambiguityReason": None,
                }
            ],
            "timeHorizon": "medium_term",
            "analysisAspects": ["valuation", "fundamentals", "recent_news", "risks"],
            "comparisonMode": False,
            "userDecisionContext": "whether_to_buy",
            "requiresLiveData": True,
            "outputStyle": "research_memo",
            "constraints": [],
            "clarificationQuestions": [],
            "confidence": 0.94,
        }
    )
    service = QueryUnderstandingService(llm_client=StubLLMClient(llm_response))

    result = service.understand("英伟达现在还能不能买？")

    assert result.task_type == ResearchTaskType.INVESTMENT_THESIS
    assert result.companies[0].candidates[0].ticker == "NVDA"
    assert result.analysis_aspects == ["valuation", "fundamentals", "recent_news", "risks"]
    assert result.comparison_mode is False
    assert result.user_decision_context == "whether_to_buy"


def test_query_understanding_can_represent_comparison_questions():
    llm_response = QueryUnderstanding.model_validate(
        {
            "taskType": "COMPANY_COMPARISON",
            "intentSummary": "用户希望比较比亚迪和特斯拉的长期优势。",
            "intentBreakdown": [
                {
                    "point": "用户要求比较两个公司。",
                    "planningImpact": "后续规划应对齐比较维度。",
                }
            ],
            "companies": [
                {
                    "mention": "比亚迪",
                    "canonicalName": "BYD Company Limited",
                    "candidates": [
                        {
                            "ticker": "1211",
                            "exchange": "HKEX",
                            "market": "HK",
                            "confidence": 0.82,
                        }
                    ],
                    "needsClarification": True,
                    "ambiguityReason": "可能指 A 股或港股上市证券",
                },
                {
                    "mention": "特斯拉",
                    "canonicalName": "Tesla, Inc.",
                    "candidates": [
                        {
                            "ticker": "TSLA",
                            "exchange": "NASDAQ",
                            "market": "US",
                            "confidence": 0.95,
                        }
                    ],
                    "needsClarification": False,
                    "ambiguityReason": None,
                },
            ],
            "timeHorizon": "long_term",
            "analysisAspects": ["competitive_advantage", "financials", "valuation", "risks"],
            "comparisonMode": True,
            "userDecisionContext": "which_company_has_better_long_term_advantage",
            "requiresLiveData": True,
            "outputStyle": "comparison_memo",
            "constraints": ["compare on the same dimensions"],
            "clarificationQuestions": ["比亚迪需要分析 A 股还是港股？"],
            "confidence": 0.88,
        }
    )
    service = QueryUnderstandingService(llm_client=StubLLMClient(llm_response))

    result = service.understand("比亚迪和特斯拉谁更有长期优势？")

    assert result.task_type == ResearchTaskType.COMPANY_COMPARISON
    assert result.comparison_mode is True
    assert result.analysis_aspects == ["competitive_advantage", "financials", "valuation", "risks"]
    assert result.constraints == ["compare on the same dimensions"]
    assert result.intent_breakdown[0].planning_impact == "后续规划应对齐比较维度。"


def test_query_understanding_injects_current_date_and_supports_ambiguous_entities():
    llm_response = QueryUnderstanding.model_validate(
        {
            "taskType": "COMPANY_COMPARISON",
            "intentSummary": "用户希望对比特斯拉和纳斯达克相关对象从2026年初至今的表现。",
            "intentBreakdown": [
                {
                    "point": "特斯拉可解析为 Tesla, Inc. / TSLA。",
                    "planningImpact": "该对象可进入公司类研究工具。",
                },
                {
                    "point": "纳斯达克存在公司与指数歧义。",
                    "planningImpact": "澄清前不应执行完整比较。",
                },
                {
                    "point": "用户指定 2026-01-01 至当前日期。",
                    "planningImpact": "不要误判为未来不可用数据。",
                },
            ],
            "entities": [
                {
                    "mention": "特斯拉",
                    "resolutionStatus": "RESOLVED",
                    "bestGuess": {"name": "Tesla, Inc.", "identifier": "TSLA", "typeHint": "company"},
                    "candidates": [],
                    "notes": "明确公司标的。",
                },
                {
                    "mention": "纳斯达克",
                    "resolutionStatus": "AMBIGUOUS",
                    "bestGuess": None,
                    "candidates": [
                        {"name": "Nasdaq, Inc.", "identifier": "NDAQ", "typeHint": "company"},
                        {"name": "Nasdaq Composite", "identifier": None, "typeHint": "index"},
                    ],
                    "notes": "可能指公司或指数。",
                },
            ],
            "constraints": [
                {
                    "kind": "time_range",
                    "rawText": "2026年1.1至今",
                    "normalizedText": "2026-01-01 至 2026-06-09",
                    "needsClarification": False,
                }
            ],
            "companies": [
                {
                    "mention": "特斯拉",
                    "canonicalName": "Tesla, Inc.",
                    "candidates": [
                        {
                            "ticker": "TSLA",
                            "exchange": "NASDAQ",
                            "market": "US",
                            "confidence": 0.98,
                        }
                    ],
                    "needsClarification": False,
                    "ambiguityReason": None,
                }
            ],
            "timeHorizon": "2026-01-01_to_current_date",
            "analysisAspects": ["market_performance", "fundamentals", "valuation", "news", "risks"],
            "comparisonMode": True,
            "userDecisionContext": "multi_dimension_comparison",
            "requiresLiveData": True,
            "outputStyle": "comparison_memo",
            "clarificationQuestions": ["你这里的“纳斯达克”是指 Nasdaq 公司（NDAQ），还是纳斯达克指数？"],
            "confidence": 0.84,
        }
    )
    llm = StubLLMClient(llm_response)
    service = QueryUnderstandingService(llm_client=llm)

    result = service.understand(
        "对比评估一下特斯拉和纳斯达克，纳斯达克公司。时间范围为2026年1.1至今。各方面都进行对比",
        current_date="2026-06-09",
        timezone="Asia/Shanghai",
        locale="zh-CN",
    )

    assert "2026-06-09" in llm.calls[0]["user_prompt"]
    assert "Asia/Shanghai" in llm.calls[0]["user_prompt"]
    assert result.entities[1].resolution_status == "AMBIGUOUS"
    assert result.constraints[0].normalized_text == "2026-01-01 至 2026-06-09"
    assert result.clarification_questions == ["你这里的“纳斯达克”是指 Nasdaq 公司（NDAQ），还是纳斯达克指数？"]


def test_query_understanding_returns_default_when_llm_fails():
    service = QueryUnderstandingService(llm_client=StubLLMClient(RuntimeError("LLM unavailable")))

    result = service.understand("随便看看")

    assert result.task_type == ResearchTaskType.INVESTMENT_THESIS
    assert result.companies == []
    assert result.analysis_aspects == ["market_data", "recent_news", "fundamentals", "risks"]
    assert result.comparison_mode is False
    assert result.user_decision_context == "general_research"
    assert result.constraints == []
    assert result.confidence == 0.1
