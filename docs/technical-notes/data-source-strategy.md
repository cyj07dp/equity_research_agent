# 投研 Agent 数据源策略

日期：2026-06-06

## 结论

投研 Agent 不应该把某一个网站直接当成“全部数据源”。更合理的做法是按问题类型拆分工具，再为每个工具选择合适的数据源。

第一阶段建议采用：

- 结构化 API 负责行情、财务、估值等数值型数据。
- 官方来源负责公告、财报、监管文件。
- 新闻和网页来源负责近期事件、市场叙事和中文语境补充。
- LLM 只基于工具返回的 evidence 推理，不直接自行判断网页或数据源真假。

当前接入的 Alpha Vantage 可以作为第一批结构化 provider，但应被视为可替换 provider，而不是最终唯一来源。

## 数据源分层

### 1. 结构化行情与财务数据

适合数据：

- 最新价格、涨跌幅、成交量。
- 市值、PE、PEG、PB、EPS。
- Revenue TTM、利润率、增长率。
- 分红、拆股、历史价格。

适合来源：

- Alpha Vantage。
- Financial Modeling Prep。
- Finnhub。
- Polygon。
- Tiingo。
- Nasdaq Data Link。

特点：

- 适合工具调用。
- 返回 JSON/CSV，字段稳定。
- 易于保存 raw payload 和引用。
- 通常需要 API key，免费额度有限。

风险：

- 免费版限流明显。
- 不同 provider 字段口径可能不同。
- 部分数据延迟或覆盖不完整。

当前项目状态：

- `market_data` 已接入 Alpha Vantage `GLOBAL_QUOTE`。
- `fundamentals` 已接入 Alpha Vantage `OVERVIEW`。
- `news_search` 已接入 Alpha Vantage `NEWS_SENTIMENT`。
- 没有 `ALPHA_VANTAGE_API_KEY` 时工具失败，不生成 fake evidence。

### 2. 官方公告和财报数据

适合数据：

- 10-K、10-Q、8-K。
- 年报、季报、财报电话会材料。
- 公司投资者关系页面。
- 监管公告和重大事项。

适合来源：

- SEC EDGAR。
- 公司 Investor Relations 页面。
- 港交所披露易。
- 巨潮资讯。
- 上交所、深交所公告。

特点：

- 可信度最高。
- 适合回答“财报有什么隐患”“现金流质量怎么样”“管理层说了什么”。
- 文档较长，需要摘要、分段检索和引用。

风险：

- 格式复杂，PDF/HTML/XBRL 都可能出现。
- 需要处理发布时间、报告期和单位。
- 不适合简单网页抓取，需要专门 parser。

建议工具：

- `filings_search`
- `filing_section_reader`
- `earnings_release_reader`
- `company_ir_reader`

### 3. 新闻和网页来源

适合数据：

- 近期新闻。
- 产品、监管、诉讼、并购、裁员等事件。
- 市场叙事和分析观点。
- 中文用户更容易理解的背景材料。

适合来源：

- Alpha Vantage News。
- Reuters、CNBC、MarketWatch 等新闻源。
- TradesMax 等中文美股资讯网站。
- 公司新闻稿。
- 搜索引擎结果。

特点：

- 适合补充“最近发生了什么”。
- 适合中文报告表达。
- 需要区分事实新闻、评论观点和广告/会员内容。

风险：

- 网页结构不稳定。
- 抓取需要遵守 robots、条款和频率限制。
- 文章内容可能有版权限制，系统应摘要和引用，不应大段复制。
- 观点文章不能等同于事实数据。

建议工具：

- `news_search`
- `web_article_reader`
- `article_summarizer`
- `source_reliability_ranker`

## TradesMax 是否适合作为数据源

TradesMax 更适合作为中文美股新闻和分析观点来源，不适合作为第一优先级的行情或财务数据源。

原因：

- 它更像面向用户的资讯/分析网站，而不是标准金融数据 API。
- 当前没有把它作为稳定公开 API provider 的证据。
- 网页内容适合做新闻摘要、事件补充、中文语境解释。
- 行情、估值、财务指标应优先来自结构化 API 或官方披露。

如果后续接入 TradesMax，建议只放在这类工具中：

- `news_search`
- `web_article_reader`
- `chinese_market_context`

不建议用于：

- `market_data`
- `fundamentals`
- `valuation_metrics`
- `financial_statement`

## Provider 选择原则

选择一个数据源之前，需要回答：

1. 它是否有稳定 API？
2. 是否允许程序化访问？
3. 是否需要 API key？
4. 免费额度是否够开发和演示？
5. 数据覆盖哪些市场？
6. 字段是否稳定？
7. 是否提供时间戳、来源 URL 和原始数据？
8. 是否适合保存到 PostgreSQL？
9. 是否可以在报告中引用？
10. 如果失败，是否能返回可解释错误？

## 工具设计原则

工具不应该只返回给 LLM 的自然语言 summary。每个工具应同时返回：

- 标准化字段：供后端保存和后续计算。
- 中文 summary：供 LLM 快速理解。
- raw payload：供调试和追溯。
- source name。
- source URL。
- observed_at。
- confidence。
- failure reason。

LLM 不负责判断工具返回内容真假。工具层和 provider 层负责表达：

- 数据来源。
- 数据时间。
- 是否成功。
- 是否限流。
- 是否缺字段。
- 是否来自官方、API、新闻或网页。

Prompt 只应该要求 LLM：

- 只基于 evidence 推理。
- 不从常识补充事实。
- 缺少数据时明确说明。
- 区分事实、推断和不确定性。

## 推荐演进顺序

### 阶段 1：结构化 API 最小闭环

目标：

- 保留 Alpha Vantage provider。
- 明确 API key 配置。
- 确保无 key、限流、空响应时工具失败可见。

已完成：

- `market_data`
- `fundamentals`
- `news_search`

下一步：

- 在报告和 tool trace 中更清楚展示工具失败原因。
- 添加 provider 字段，区分 `Alpha Vantage`、`SEC`、`TradesMax` 等来源。

### 阶段 2：官方披露工具

目标：

- 接入 SEC EDGAR。
- 支持美股 10-K / 10-Q / 8-K 搜索和摘要。
- 让 Agent 能回答财报、现金流、风险因素类问题。

优先工具：

- `filings_search`
- `filing_summary`
- `risk_factor_reader`

### 阶段 3：网页新闻工具

目标：

- 增加 `web_article_reader`。
- 支持输入 URL 抽取标题、发布时间、正文摘要和来源。
- TradesMax 可以在这一阶段作为候选中文来源。
- 在原文抽取后使用 LLM 生成结构化 article evidence，包括 main points、facts、dates、companies、risks 和 limitations。

优先约束：

- 不大段复制原文。
- 保留 URL。
- 限制抓取频率。
- 标记文章类型：新闻、评论、广告、会员内容、未知。
- 第三方整理工具只能作为二次整理 provider，不能替代原始 URL 和原始抽取文本。

当前状态：

- `web_article_reader` 已支持 URL 正文抽取。
- 当工具注册时传入 LLM client，会额外生成结构化 `ArticleSummary`。
- 结构化摘要会保存到 tool output 的 `structuredSummary`，并作为 evidence summary 传给后续 reasoning。
- 未来可以把 YouMind、Get笔记等作为 `external_article_organizer` provider 接入同一层，但需要保留原 URL、provider 名称和整理限制。

### 阶段 4：多 provider 聚合

目标：

- 同一个工具支持多个 provider。
- 失败时自动尝试备选 provider。
- 对多个来源的同类数据做一致性检查。

示例：

- `market_data`: Alpha Vantage -> Finnhub -> Polygon。
- `fundamentals`: FMP -> Alpha Vantage -> SEC。
- `news_search`: Alpha Vantage News -> web search -> selected websites。

## 当前实现调整建议

短期不需要删除 Alpha Vantage 工具，但需要避免把它写死成唯一方案。

建议后续把代码命名和结构调整为：

```text
tools/
  providers/
    alpha_vantage.py
    sec_edgar.py
    web_article.py
  market_data.py
  fundamentals.py
  news_search.py
```

这样工具接口稳定，provider 可以替换。

当前的 `app.tools.alpha_vantage` 可以先保留，等第二个 provider 接入时再做结构迁移。

## 未决问题

1. 第一批付费或免费 API provider 是否只使用 Alpha Vantage，还是同时比较 Financial Modeling Prep / Finnhub？
2. 是否需要优先支持 A 股和港股？如果需要，Alpha Vantage 覆盖可能不够。
3. TradesMax 是否允许程序化抓取？需要进一步检查 robots、条款和页面结构。
4. 新闻源是否需要中文优先，还是中英文混合后由 LLM 生成中文报告？
5. 报告中是否展示 provider 名称和更新时间，还是只在 tool trace 中展示？
