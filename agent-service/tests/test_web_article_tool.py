from app.tools.registry import ToolRegistry
from app.tools.web_article import WebArticleReaderTool
from app.schemas import ArticleSummary


class StubLLMClient:
    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        return ArticleSummary(
            mainPoints=["苹果服务收入增长是文章主线。"],
            facts=["Apple reported stronger services demand."],
            dates=[],
            companies=["Apple Inc."],
            risks=["监管风险被管理层提及。"],
            limitations=[],
        )


def test_web_article_reader_extracts_title_and_text_evidence():
    html = """
    <html>
      <head><title>Apple shares rise after earnings</title></head>
      <body>
        <nav>menu</nav>
        <article>
          <h1>Apple shares rise after earnings</h1>
          <p>Apple reported revenue growth and stronger services demand.</p>
          <p>Management also discussed regulatory risks.</p>
        </article>
      </body>
    </html>
    """
    tool = WebArticleReaderTool(fetch_text=lambda url: html)

    call, evidence = tool.run({"url": "https://example.com/aapl-news"}, context={})

    assert call.status == "SUCCEEDED"
    assert call.output["title"] == "Apple shares rise after earnings"
    assert "services demand" in call.output["text"]
    assert evidence[0].source_type == "WEB_ARTICLE"
    assert evidence[0].source_url == "https://example.com/aapl-news"


def test_web_article_reader_can_add_structured_llm_summary():
    html = """
    <html>
      <head><title>Apple shares rise after earnings</title></head>
      <body><article><p>Apple reported stronger services demand.</p></article></body>
    </html>
    """
    tool = WebArticleReaderTool(fetch_text=lambda url: html, llm_client=StubLLMClient())

    call, evidence = tool.run({"url": "https://example.com/aapl-news"}, context={})

    assert call.status == "SUCCEEDED"
    assert call.output["structuredSummary"]["mainPoints"] == ["苹果服务收入增长是文章主线。"]
    assert call.output["extractionProvider"] == "web_article_reader"
    assert call.output["summaryProvider"] == "llm"
    assert "苹果服务收入增长" in evidence[0].summary


def test_web_article_reader_fails_without_url():
    tool = WebArticleReaderTool(fetch_text=lambda url: "")

    call, evidence = tool.run({}, context={})

    assert call.status == "FAILED"
    assert "url is required" in call.output["error"]
    assert evidence == []


def test_default_registry_includes_web_article_reader():
    tools = ToolRegistry().get_tools()

    assert isinstance(tools["web_article_reader"], WebArticleReaderTool)
