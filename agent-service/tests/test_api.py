from fastapi.testclient import TestClient

from app.main import app


def test_create_agent_run_endpoint_returns_agent_result():
    client = TestClient(app)

    response = client.post(
        "/agent-runs",
        json={
            "runId": "00000000-0000-0000-0000-000000000000",
            "query": "帮我分析一下英伟达最近的机会和风险",
            "locale": "zh-CN",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["understanding"]
    assert payload["runStatus"] in {"COMPLETED", "DEGRADED"}
    assert "runtimeWarnings" in payload
    assert payload["plan"]
    assert "clarificationQuestions" in payload
    assert "toolCalls" in payload
    assert "evidence" in payload
    assert payload["reasoning"]
    assert payload["draftReport"]
    assert payload["reflection"]
    assert payload["finalReport"]


def test_create_conversation_summary_endpoint_returns_structured_summary():
    client = TestClient(app)

    response = client.post(
        "/conversation-summary",
        json={
            "locale": "zh-CN",
            "messages": [
                {"role": "USER", "content": "我是低风险长期投资者，主要看美股 ETF。"},
                {"role": "ASSISTANT", "content": "可以先从分散化和回撤控制角度研究。"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert payload["summary"]["importantHistory"]
    assert payload["summary"]["notEvidence"]
