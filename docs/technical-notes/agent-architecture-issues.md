# Agent 架构待解决问题

## 当前结论

当前架构已经从固定 workflow 进化为 Plan-and-Execute + Conditional Replanning，但要成为更真实的投研 agent，还需要补齐持续对话、trace 可解释性、工具错误治理、数据质量治理和工具覆盖能力。

## 1. 持续对话能力不足

第一版后端能力已完成：`NEEDS_CLARIFICATION` 后，用户可以在同一个 conversation 中继续补充回答；系统会追加 message，并创建新的 job 继续执行。

目标方案采用 conversation/message 模型：

- `ResearchConversation` 表示一次持续研究会话。
- `ResearchMessage` 保存用户和 agent 的多轮消息。
- `ResearchJob` 继续表示一次 agent 执行快照。
- 每次用户补充信息都会追加 message，并创建新的 job。

这样可以明确回答：哪次用户输入触发了哪次工具调用、哪份报告、哪条 trace。

## 2. Trace 可解释性不足

当前 trace 能展示阶段、工具调用和 evidence，但还不能清晰展示“报告结论由哪些 evidence 支撑”。

已调整的方向：

- Planner 不再用固定 `responseMode` 或固定报告栏目约束所有问题。
- Planner 只输出动态 `answerPlan`：`answerGoal` 和 `sections[{title,purpose}]`。
- Report Writer 输出动态 `sections[{title,content,citations}]`，trace 优先展示这些 sections。
- 代码继续强约束工具调用、状态流转和 evidence 质量，不强约束业务表达栏目。

后续目标：

- 报告关键结论和 evidence 建立引用关系。
- trace 页面展示 claim -> evidence 的映射。
- 对未被 evidence 支撑的 claim，在 reflection 阶段标记并弱化。

## 3. 工具错误类型不结构化

当前工具失败大多以字符串形式保存，不利于 replanner 判断下一步动作。

后续目标是将工具错误类型结构化：

- `RATE_LIMITED`
- `TIMEOUT`
- `AUTH_MISSING`
- `NO_DATA`
- `UNSUPPORTED_MARKET`
- `PARSE_FAILED`
- `LOW_RELEVANCE`

这样 replanner 可以区分重试、降级、换工具、澄清或报告能力边界。

## 4. 数据质量治理不足

投研场景不能只关心是否拿到数据，还要判断数据是否可靠、是否新鲜、是否相关、是否与其他来源冲突。

后续 evidence 可以增强字段：

- `publishedAt`
- `freshness`
- `relevance`
- `sourceReliability`
- `claimSupportLevel`
- `limitations`

## 5. 工具能力覆盖不足

当前工具覆盖仍偏窄。真实投研需要更丰富的数据源：

- 实时或近实时新闻
- 估值和财务指标
- 行业横向比较
- earnings call transcript
- analyst estimates
- 宏观、利率、指数背景

短期优先增强免费或官方来源，避免一开始依赖付费 provider。

## 6. 多实体、多主题 query 支持仍需增强

Java 存储层已泛化为 subject/report 模型，但 planner、trace 和 report 对多个 subject 的组织还不够强。

后续目标：

- plan 支持多 subject 分组。
- tool call 和 evidence 可选绑定 subject。
- report 能清楚区分比较对象和共同结论。

## 持续对话方案 B

采用 conversation/message 作为第一阶段正式方案。

目标数据关系：

```text
ResearchConversation
  -> ResearchMessage
  -> ResearchJob
       -> ResearchReport
       -> ToolCallRecord
       -> EvidenceItem
```

`conversation` 是交互上下文，`job` 是一次执行快照。两者分开后，系统可以自然支持澄清、追问、重新执行和 trace 审计。

第一版实现范围：

- 新增 `/api/conversations` API。
- 新增 `ResearchConversation`、`ResearchMessage`。
- `ResearchJob` 关联 `conversationId` 和 `triggerMessageId`。
- Java 调 Python agent-service 时传入 conversation history。
- 不做完整聊天前端，只先完成后端 API 和 agent 入参闭环。

## Conversation 前端第一版

第一版 conversation 前端从“调试型 conversationId 控制台”调整为“正常聊天窗口”。

已整改：

- 用户首次发送消息时自动创建 conversation。
- 后续消息自动追加到当前 conversation。
- 浏览器使用 `localStorage` 保存最近的 `conversationId`，刷新后自动恢复。
- 主界面不再要求用户手动粘贴 `conversationId`。
- 当前 job 的 Trace 入口在顶部和消息操作中都可达。
- Java 日志增加 `conversationId`、`messageId`、`jobId` 链路字段。
- planner 判断需要澄清且没有可执行 steps 时，Python agent 直接返回 `NEEDS_CLARIFICATION`，不再继续生成“数据不足报告”。

这次问题暴露出的工程教训：

- `conversationId` 和 `jobId/runId` 必须在 UI 和日志中明确区分，否则排查时很容易把执行快照当成会话。
- 本地单用户阶段不必先引入 JWT/cookie，但必须有最小状态恢复机制。
- 澄清状态不是一种失败报告，而是对话控制流，应尽早返回给用户。
- Trace 是开发和演示时的核心解释入口，不能藏在不明显的 message action 里。

继续暂不做：

- 不做完整聊天产品能力，例如历史 conversation 列表、搜索、归档、重命名。
- 不做 WebSocket 或流式输出，先用轮询 job/conversation 状态。
- 不做 markdown 富文本报告渲染，报告仍跳转到 report/trace 查看。
- 不做复杂前端路由框架，先使用静态 `conversation.html`。
- 不做 claim -> evidence 映射展示，该能力放到 trace 可解释性增强阶段。
- 不做长期记忆或跨 conversation 记忆。
- 不做多用户、权限和会话隔离。

后续可继续增强：

- 会话列表和历史搜索。
- 更完整的 report 富文本展示。
- WebSocket 或 SSE 流式状态更新。
- 用户身份和多用户隔离。
