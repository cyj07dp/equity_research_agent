# Agent Memory Design

## 目标

本模块提供可控、可解释的用户偏好记忆，让投研 Agent 在跨会话时能复用用户的默认市场、风险偏好、投资期限和报告风格。

记忆不替代证据。用户偏好只能作为回答约束和默认假设，不能作为市场事实、公司事实或新闻事实使用。

## 分层

### 1. 会话上下文记忆

当前 conversation 内的历史消息已经传给 Python agent-service，用于理解追问和省略表达，例如“苹果呢”“那微软呢”。

不新增表。

### 2. 显式用户偏好记忆

当前阶段实现。偏好由用户主动设置，后端持久化，并在每次 agent run 时传给 Python。

典型字段：

- `preferred_locale`：默认语言。
- `default_market`：默认市场，例如 `US`、`HK`、`CN`。
- `risk_tolerance`：风险偏好，例如 `LOW`、`MEDIUM`、`HIGH`。
- `time_horizon`：投资期限，例如 `SHORT_TERM`、`MEDIUM_TERM`、`LONG_TERM`。
- `report_style`：报告风格，例如 `CONCISE`、`DETAILED_MEMO`、`BEGINNER_FRIENDLY`。
- `preferred_sectors`：关注行业，JSON 数组字符串。
- `excluded_sectors`：排除行业，JSON 数组字符串。
- `preferred_assets`：常看标的，JSON 数组字符串。
- `notes`：用户补充说明。

### 3. 长期抽取记忆

后续扩展。可以从历史对话异步抽取稳定偏好，但不在当前 MVP 实现。

## 表设计

```sql
CREATE TABLE agent_users (
    id UUID PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    auth_provider VARCHAR(50) NOT NULL DEFAULT 'local',
    external_subject VARCHAR(255),
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX idx_agent_users_provider_subject
ON agent_users(auth_provider, external_subject);
```

```sql
CREATE TABLE agent_user_preferences (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES agent_users(id) ON DELETE CASCADE,
    preferred_locale VARCHAR(32) NOT NULL DEFAULT 'zh-CN',
    default_market VARCHAR(32),
    risk_tolerance VARCHAR(32),
    time_horizon VARCHAR(32),
    report_style VARCHAR(32),
    preferred_sectors TEXT NOT NULL DEFAULT '[]',
    excluded_sectors TEXT NOT NULL DEFAULT '[]',
    preferred_assets TEXT NOT NULL DEFAULT '[]',
    notes TEXT,
    memory_source VARCHAR(32) NOT NULL DEFAULT 'USER_PROVIDED',
    confidence NUMERIC(5,4) NOT NULL DEFAULT 1.0000,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX idx_agent_user_preferences_user_id
ON agent_user_preferences(user_id);
```

当前没有正式登录系统，MVP 使用一个 `default_user`。未来接入认证后，将 conversation 归属到真实 `user_id`。

## API

- `GET /api/me/preferences`：读取当前用户偏好。
- `PUT /api/me/preferences`：更新当前用户偏好。

## Agent 调用契约

Java 调 Python 时增加：

```json
{
  "userPreferences": {
    "preferredLocale": "zh-CN",
    "defaultMarket": "US",
    "riskTolerance": "MEDIUM",
    "timeHorizon": "LONG_TERM",
    "reportStyle": "CONCISE",
    "preferredSectors": ["AI", "semiconductor"],
    "excludedSectors": [],
    "preferredAssets": ["AAPL", "QQQ"],
    "notes": ""
  }
}
```

Python prompt 规则：

- 用户偏好只代表回答约束，不代表事实证据。
- 不得因为偏好编造市场数据、公司基本面或新闻。
- 当用户问题和偏好冲突时，优先遵循当前问题。
- 当用户问题缺少市场、期限或风险偏好时，可以使用偏好作为默认假设，并在回答中说明。

## MVP 不做

- 正式 JWT 登录。
- 自动从历史会话抽取偏好。
- 向量库记忆。
- 多用户权限隔离。
- 偏好变更审计表。
