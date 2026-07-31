# Equity Research Agent

一个面向可解释、可追溯投研流程的全栈后端项目。Spring Boot 负责异步任务、对话、用户偏好、持久化和追踪 API；Python Agent Service 负责理解研究问题、制定计划、调用数据工具、评估证据并生成带引用的结构化报告。

> 本项目用于软件工程与 AI Agent 技术演示，不构成投资建议，也不保证数据的实时性、完整性或准确性。

## 核心能力

- 自然语言投研请求与多轮研究对话
- 异步研究任务和状态查询
- Plan-and-Solve 研究规划、条件重规划与工具路由
- Alpha Vantage 行情、基本面与新闻工具
- SEC EDGAR 文件检索和轻量级文本 RAG
- 基于 Stooq 的市场概览、ETF 发现和股票筛选
- 网页文章读取、证据标准化、引用与数据充分性评估
- 一次反思校验和结构化研究报告生成
- PostgreSQL 持久化与 Flyway 数据库迁移
- Agent 工具调用轨迹、证据和报告查询
- 用户研究偏好、会话摘要和记忆建议
- Java/Python 自动化测试与确定性 Agent 评估

## 系统架构

```text
Client / Browser
       |
       v
Spring Boot API (8080)
  - research jobs
  - conversations
  - preferences
  - reports and traces
       |
       +------> PostgreSQL (5432)
       |
       v
FastAPI Agent Service (8000)
  - query understanding
  - planning and replanning
  - tool routing
  - evidence reasoning
  - report writing and reflection
       |
       +------> OpenAI-compatible LLM
       +------> Alpha Vantage
       +------> SEC EDGAR
       +------> Stooq / web sources
```

## 技术栈

| 模块 | 技术 |
| --- | --- |
| Java 后端 | Java 21、Spring Boot 3、Spring Web、Spring Data JPA |
| Agent 服务 | Python 3.11+、FastAPI、Pydantic、OpenAI SDK |
| 数据库 | PostgreSQL 16、Flyway |
| 测试 | JUnit 5、Mockito、pytest |
| 本地基础设施 | Docker Compose |

## 目录结构

```text
.
├── src/                         # Spring Boot 源码、资源与测试
├── agent-service/
│   ├── src/app/                 # Python Agent runtime
│   ├── tests/                   # Python 测试
│   └── evals/                   # 确定性与 live 评估工具
├── docs/                        # 设计、实施计划和技术说明
├── openspec/                    # OpenSpec 项目配置
├── docker-compose.yml           # PostgreSQL 本地环境
├── pom.xml                      # Java/Maven 配置
└── .env.example                 # 环境变量模板
```

## 快速开始

### 1. 前置要求

- Java 21
- Maven 3.9+
- Python 3.11+
- Docker 与 Docker Compose

### 2. 配置环境变量

```bash
cp .env.example .env
```

至少配置：

```dotenv
LLM_API_KEY=your_api_key
LLM_MODEL=your_model_name
SEC_USER_AGENT=your-app-name/0.1 your_email@example.com
```

使用 OpenAI-compatible 服务时同时设置 `LLM_BASE_URL`。使用 Alpha Vantage 工具时设置 `ALPHA_VANTAGE_API_KEY`。`.env` 已被 Git 忽略，请勿提交真实密钥。

### 3. 启动 PostgreSQL

```bash
docker compose up -d postgres
```

### 4. 启动 Python Agent Service

```bash
cd agent-service
python3.11 -m venv .venv-equity-research-agent
source .venv-equity-research-agent/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --app-dir src
```

检查服务：

```bash
curl http://localhost:8000/health
```

### 5. 启动 Spring Boot

在另一个终端回到项目根目录：

```bash
mvn spring-boot:run
```

Java API 默认地址为 `http://localhost:8080`。

## API 示例

创建研究任务：

```bash
curl -X POST http://localhost:8080/api/research-jobs \
  -H 'Content-Type: application/json' \
  -d '{"query":"分析 NVIDIA 的增长驱动、主要风险和最近 SEC 文件中的关键信息"}'
```

查询任务与追踪信息：

```bash
curl http://localhost:8080/api/research-jobs/{jobId}
curl http://localhost:8080/api/research-jobs/{jobId}/tool-calls
curl http://localhost:8080/api/research-jobs/{jobId}/trace
```

查询报告：

```bash
curl http://localhost:8080/api/reports/{reportId}
```

项目还提供对话和用户偏好 API：

- `/api/conversations`
- `/api/me/preferences`

启动 Java 服务后，可访问：

- `http://localhost:8080/conversation.html`
- `http://localhost:8080/trace.html`

## 测试与评估

运行 Java 测试：

```bash
mvn test
```

运行 Python 测试：

```bash
cd agent-service
source .venv-equity-research-agent/bin/activate
python -m pytest
```

运行不访问外部服务的 fixture 评估：

```bash
cd agent-service
source .venv-equity-research-agent/bin/activate
PYTHONPATH=src python evals/run_eval.py --run
```

如需调用真实 LLM 和数据源，可参考 [Agent Service 文档](agent-service/README.md) 使用 live 模式。

## 设计取舍

- 长耗时 AI 工作被建模为异步任务，避免阻塞 HTTP 请求。
- Java 产品后端与 Python Agent runtime 通过 HTTP/JSON 解耦，可独立演进。
- 工具输出统一转换为 evidence，报告引用和调用轨迹可以审计。
- PostgreSQL 同时承载关系型实体与 JSON 形式的工具输出和报告元数据。
- Agent 使用有界规划与一次反思，避免无上限循环带来的成本和稳定性问题。

更完整的架构背景、演进记录和数据源策略见 [`docs/`](docs/)。

## 当前限制

- 外部数据能力受免费 API 配额、网络状况和数据源覆盖范围限制。
- SEC RAG 当前使用轻量级文本切分和关键词排序，尚未接入向量数据库。
- 未配置 LLM 时，部分流程会使用确定性降级结果，不能代表完整报告质量。
- 当前任务执行基于应用内异步线程，尚未使用独立消息队列。
- 尚未实现预测、回测、生产级身份认证和部署配置。

## License

本项目使用 [MIT License](LICENSE)。
