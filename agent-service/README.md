# Agent Service

这是 `Equity Research Agent` 的 Python Agent 核心服务。

当前版本是最小原型，目标是证明 agent-first 架构：

```text
自然语言 query
  -> query understanding
  -> LLM research planner
  -> tool router
  -> evidence
  -> evidence reasoning
  -> report drafting
  -> reflection
  -> final report
  -> AgentRunResult
```

## 本地运行

安装依赖：

```bash
python -m venv .venv-equity-research-agent
source .venv-equity-research-agent/bin/activate
python -m pip install -e ".[dev]"
```

LLM 配置通过 `.env` 提供：

```bash
LLM_PROVIDER=openai-compatible
LLM_API_KEY=your_api_key
LLM_MODEL=your_model_name
LLM_BASE_URL=
```

`LLM_BASE_URL` 留空时使用 OpenAI 默认地址；如果使用兼容 OpenAI API 的服务商，填对应的 base URL。

运行测试：

```bash
python -m pytest
```

启动服务：

```bash
uvicorn app.main:app --reload --app-dir src
```

## API 示例

```bash
curl -X POST http://localhost:8000/agent-runs \
  -H 'Content-Type: application/json' \
  -d '{
    "runId": "00000000-0000-0000-0000-000000000000",
    "query": "帮我分析一下 Palantir 最近的增长机会和主要风险",
    "locale": "zh-CN"
  }'
```

当前版本支持通过 OpenAI-compatible API 调用真实 LLM；未配置或调用失败时返回结构化默认值兜底。工具层已包含 Alpha Vantage、SEC EDGAR、网页文章读取和市场探索工具，后续可继续补充更多外部数据适配器。
