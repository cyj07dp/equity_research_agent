# Market Exploration Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let broad beginner or market-direction queries produce useful non-advisory exploration output without forcing company-specific tools or long synchronous workflows.

**Architecture:** Extend Python query understanding with market/portfolio task types, constrain planner output by task type, and add lightweight market exploration tools that do not require a user-supplied ticker. Keep Java timeout as a fallback, while leaving durable Python-to-Java stage events for the next focused change set.

**Tech Stack:** Python FastAPI agent-service, Pydantic schemas, OpenAI-compatible structured LLM calls, Spring Boot Java backend.

---

### Task 1: Query Types And Planner Guardrails

**Files:**
- Modify: `agent-service/src/app/schemas.py`
- Modify: `agent-service/src/app/agent/prompts.py`
- Modify: `agent-service/src/app/agent/research_planner.py`
- Test: `agent-service/tests/test_research_planner.py`

- [ ] Add `MARKET_EXPLORATION`, `BEGINNER_GUIDANCE`, and `PORTFOLIO_STRATEGY` to `ResearchTaskType`.
- [ ] Update the query-understanding prompt so broad no-ticker questions can be classified as market exploration instead of forced company research.
- [ ] Update the planning prompt and Python post-processing so plans are capped at six steps, no-ticker plans cannot use company-only tools, and `web_article_reader` requires a concrete URL.
- [ ] Add tests for planner filtering.

### Task 2: No-Ticker Market Exploration Tools

**Files:**
- Create: `agent-service/src/app/tools/market_exploration.py`
- Modify: `agent-service/src/app/tools/alpha_vantage.py`
- Test: `agent-service/tests/test_market_exploration_tools.py`

- [ ] Add `market_overview`, `etf_discovery`, and `stock_screener` tools.
- [ ] Keep output non-advisory: evidence should describe exploration candidates, screening criteria, and risks, not say what to buy.
- [ ] Register the tools in `real_data_tools`.
- [ ] Add tests for deterministic output without external API calls.

### Task 3: Orchestrator Routing For Broad Beginner Queries

**Files:**
- Modify: `agent-service/src/app/agent/orchestrator.py`
- Test: `agent-service/tests/test_agent_run.py`
- Test: `agent-service/tests/test_report_reflection.py`

- [ ] If QueryUnderstanding has no concrete ticker but is market/portfolio/beginner guidance, let planner use only market exploration tools.
- [ ] If QueryUnderstanding has no concrete ticker and only needs clarification, return a concise clarification report without tool execution.
- [ ] Trigger report revision when `reflection.revisionInstructions` is non-empty, even if `passed=true`.
- [ ] Add tests for broad beginner queries and reflection revision.

### Task 4: Verification

**Commands:**
- Python: `cd agent-service && ./.venv-equity-research-agent/bin/python -m pytest -q`
- Java: `'/Applications/IntelliJ IDEA.app/Contents/plugins/maven/lib/maven3/bin/mvn' test`

- [ ] Run focused Python tests after each task.
- [ ] Run full Python and Java test suites before completion.
