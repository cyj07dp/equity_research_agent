# Agent Service MVP 实现计划

> 状态：当前执行计划。目标是先做出 Python Agent Service 最小闭环，供 Java Backend 后续通过 HTTP JSON 调用。

## 目标

新增 `agent-service/`，实现一个 FastAPI Agent 原型：

```text
POST /agent-runs
  -> query interpreter
  -> company resolver
  -> research planner
  -> tool executor
  -> evidence aggregation
  -> report writer
  -> validator
  -> AgentRunResult
```

## 第一版范围

实现：

- 自然语言 `query` 输入。
- `CompanyResolver` 返回标准公司信息。
- `ResearchPlanner` 根据 intent 生成 plan。
- fake tools 模拟 market / news / fundamentals evidence。
- `ReportWriter` 生成结构化中文 research memo。
- `ReportValidator` 生成 validation result。
- FastAPI `POST /agent-runs`。
- 基础测试覆盖 agent run 成功路径。

暂不实现：

- 真实 MCP 工具。
- 真实联网搜索。
- 真实 LLM。
- Java 后端调用 Python。
- 数据库持久化。

## 文件结构

```text
agent-service/
  pyproject.toml
  README.md
  src/app/
    main.py
    schemas.py
    agent/
      orchestrator.py
      query_interpreter.py
      company_resolver.py
      planner.py
      report_writer.py
      validator.py
    tools/
      base.py
      fake_tools.py
  tests/
    test_agent_run.py
```

## 验证方式

```bash
cd agent-service
python -m pytest
```

如果本机没有依赖，先安装：

```bash
cd agent-service
python -m pip install -e ".[dev]"
```
