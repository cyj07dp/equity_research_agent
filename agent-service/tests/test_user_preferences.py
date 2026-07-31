from app.agent.orchestrator import _effective_query
from app.schemas import ConversationMessage, UserPreferences


def test_effective_query_injects_enabled_user_preferences_as_constraints():
    effective_query = _effective_query(
        query="苹果最近怎么样",
        conversation_messages=[],
        user_preferences=UserPreferences(
            enabled=True,
            defaultMarket="US",
            riskTolerance="LOW",
            timeHorizon="LONG_TERM",
            reportStyle="CONCISE",
            preferredSectors=["AI", "Semiconductor"],
            excludedSectors=["Crypto"],
            preferredAssets=["ETF"],
            notes="更关注回撤控制",
        ),
    )

    assert "[用户长期偏好]" in effective_query
    assert "默认市场：美股" in effective_query
    assert "风险偏好：保守" in effective_query
    assert "投资期限：长期" in effective_query
    assert "报告风格：简洁结论" in effective_query
    assert "关注行业：AI、Semiconductor" in effective_query
    assert "排除行业：Crypto" in effective_query
    assert "常看资产：ETF" in effective_query
    assert "备注：更关注回撤控制" in effective_query
    assert "[偏好使用规则]" in effective_query
    assert "不能作为事实证据" in effective_query
    assert "如果与用户最新问题冲突，优先遵循最新问题" in effective_query
    assert "[用户最新输入]" in effective_query
    assert "用户最新输入: 苹果最近怎么样" in effective_query


def test_effective_query_omits_disabled_user_preferences():
    effective_query = _effective_query(
        query="苹果最近怎么样",
        conversation_messages=[],
        user_preferences=UserPreferences(
            enabled=False,
            defaultMarket="US",
            riskTolerance="LOW",
        ),
    )

    assert effective_query == "苹果最近怎么样"
    assert "[用户长期偏好]" not in effective_query
    assert "LOW" not in effective_query


def test_effective_query_combines_conversation_context_and_preferences():
    effective_query = _effective_query(
        query="我说的是 Apple Inc.",
        conversation_messages=[
            ConversationMessage(role="USER", content="苹果最近怎么样"),
            ConversationMessage(role="ASSISTANT", content="你指的是 Apple Inc. 还是苹果产业链？"),
        ],
        user_preferences=UserPreferences(
            enabled=True,
            defaultMarket="US",
            riskTolerance="BALANCED",
        ),
    )

    assert "[用户长期偏好]" in effective_query
    assert "[会话历史]" in effective_query
    assert "USER: 苹果最近怎么样" in effective_query
    assert "ASSISTANT: 你指的是 Apple Inc. 还是苹果产业链？" in effective_query
    assert effective_query.endswith("用户最新输入: 我说的是 Apple Inc.")
