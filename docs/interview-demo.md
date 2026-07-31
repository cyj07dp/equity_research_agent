# Interview Demo Script

## Demo 1: SEC RAG + Market Evidence

User query:

```text
帮我分析苹果最新年报里的主要风险，并结合近期股价表现给出中文研究结论。
```

Expected trace:

1. AgentPlanner selects `filings_search`, `sec_filing_retriever`, and `market_data`.
2. SEC RAG retrieves risk-factor chunks with section hints, retrieval scores, matched terms, and `sec.gov` citations.
3. Evidence Audit explains whether the retrieved evidence is enough for the answer.
4. ReportWriter produces a Chinese answer with citations.
5. Final answer avoids direct buy/sell advice.

Interview talking point:

```text
这个 demo 展示的是 evidence-grounded agent：LLM 不直接凭记忆回答年报风险，而是先规划工具，检索 SEC 原文片段，再把 citation 绑定到报告。
```

## Demo 2: Memory Affects Planning

Turn 1:

```text
我是低风险长期投资者，主要关注美股 ETF。
```

Turn 2:

```text
苹果适合我继续关注吗？
```

Expected trace:

1. Java conversation layer injects conversation context and confirmed user preferences.
2. AgentPlanner treats `riskTolerance=LOW` and `timeHorizon=LONG_TERM` as soft planning constraints.
3. Planner chooses fundamentals or SEC risk evidence instead of relying only on short-term price.
4. Final answer explains suitability under the low-risk long-term constraint.

Interview talking point:

```text
memory 不是简单拼接历史消息，而是结构化偏好进入 planner，影响工具选择和 answerPolicy；同时 eval case 会检查低风险偏好下不能出现“重仓、稳赚、闭眼买”等表达。
```

## Demo 3: Broad Market Exploration

User query:

```text
最近美股哪些方向表现比较强，我想先学习一下。
```

Expected trace:

1. AgentPlanner selects `market_overview`, `etf_discovery`, and `stock_screener`.
2. Market tools return Stooq/FMP-backed market evidence when configured.
3. Report gives learning directions and evidence limitations, not direct investment advice.

Interview talking point:

```text
当用户没有给具体股票时，agent 不硬套个股研究流程，而是规划成市场探索任务；这是工具规划能力，不是写死的 if/else 工作流。
```

## Evaluation Command

```bash
cd agent-service
source .venv-equity-research-agent/bin/activate
PYTHONPATH=src python evals/run_eval.py --run
```

Expected artifact:

```text
agent-service/evals/latest-report.json
```

The default eval mode is deterministic fixture mode. Use `--mode live` only when external providers and LLM credentials are configured and network latency is acceptable.
