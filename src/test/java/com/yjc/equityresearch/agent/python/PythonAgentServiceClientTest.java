package com.yjc.equityresearch.agent.python;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import com.yjc.equityresearch.config.IdGenerator;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

class PythonAgentServiceClientTest {
    @Test
    void sendsConversationMessagesWhenProvided() throws IOException {
        UUID runId = UUID.randomUUID();
        AtomicReference<String> requestBody = new AtomicReference<>("");
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/agent-runs", exchange -> {
            requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            writeOctetStreamJson(exchange, agentRunJson(runId));
        });
        server.start();

        PythonAgentServiceClient client = new PythonAgentServiceClient(
                RestClient.builder(),
                new ObjectMapper(),
                "http://localhost:" + server.getAddress().getPort(),
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                new IdGenerator()
        );

        try {
            client.run(
                    runId,
                    "我指的是 Apple Inc.",
                    "zh-CN",
                    List.of(
                            new AgentConversationMessage("USER", "现在要不要买苹果"),
                            new AgentConversationMessage("ASSISTANT", "你指的是 Apple Inc. 吗？"),
                            new AgentConversationMessage("USER", "我指的是 Apple Inc.")
                    )
            );

            assertThat(requestBody.get())
                    .contains("\"conversationMessages\"")
                    .contains("现在要不要买苹果")
                    .contains("你指的是 Apple Inc. 吗？");
        } finally {
            server.stop(0);
        }
    }

    @Test
    void sendsUserPreferencesWhenProvided() throws IOException {
        UUID runId = UUID.randomUUID();
        AtomicReference<String> requestBody = new AtomicReference<>("");
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/agent-runs", exchange -> {
            requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            writeOctetStreamJson(exchange, agentRunJson(runId));
        });
        server.start();

        PythonAgentServiceClient client = new PythonAgentServiceClient(
                RestClient.builder(),
                new ObjectMapper(),
                "http://localhost:" + server.getAddress().getPort(),
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                new IdGenerator()
        );

        try {
            client.run(
                    runId,
                    "苹果最近怎么样",
                    "zh-CN",
                    List.of(),
                    new AgentUserPreferences(
                            "zh-CN",
                            "US",
                            "LOW",
                            "LONG_TERM",
                            "CONCISE",
                            List.of("AI", "Semiconductor"),
                            List.of("Crypto"),
                            List.of("ETF"),
                            "更关注回撤控制",
                            true
                    )
            );

            assertThat(requestBody.get())
                    .contains("\"userPreferences\"")
                    .contains("\"defaultMarket\":\"US\"")
                    .contains("\"riskTolerance\":\"LOW\"")
                    .contains("\"timeHorizon\":\"LONG_TERM\"")
                    .contains("\"preferredSectors\":[\"AI\",\"Semiconductor\"]")
                    .contains("\"excludedSectors\":[\"Crypto\"]")
                    .contains("\"preferredAssets\":[\"ETF\"]")
                    .contains("\"enabled\":true");
        } finally {
            server.stop(0);
        }
    }

    @Test
    void callsConversationSummaryEndpointAndReturnsSummaryJson() throws IOException {
        AtomicReference<String> requestBody = new AtomicReference<>("");
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/conversation-summary", exchange -> {
            requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            writeOctetStreamJson(exchange, """
                    {
                      "summary": {
                        "userProfile": {"riskTolerance": "LOW"},
                        "researchContext": {"market": "US"},
                        "openQuestions": ["更关注 ETF 还是个股？"],
                        "importantHistory": ["用户偏好低风险长期投资。"],
                        "notEvidence": ["历史偏好不是市场证据。"]
                      }
                    }
                    """);
        });
        server.start();

        PythonAgentServiceClient client = new PythonAgentServiceClient(
                RestClient.builder(),
                new ObjectMapper(),
                "http://localhost:" + server.getAddress().getPort(),
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                new IdGenerator()
        );

        try {
            String summary = client.summarizeConversation(
                    List.of(new AgentConversationMessage("USER", "我是低风险长期投资者")),
                    "{\"importantHistory\":[\"已有摘要\"]}",
                    "zh-CN"
            );

            assertThat(requestBody.get())
                    .contains("\"messages\"")
                    .contains("我是低风险长期投资者")
                    .contains("\"existingSummary\":{\"importantHistory\":[\"已有摘要\"]}");
            assertThat(summary)
                    .contains("\"userProfile\":{\"riskTolerance\":\"LOW\"}")
                    .contains("\"importantHistory\":[\"用户偏好低风险长期投资。\"]")
                    .contains("\"notEvidence\":[\"历史偏好不是市场证据。\"]");
        } finally {
            server.stop(0);
        }
    }

    @Test
    void parsesJsonResponseEvenWhenPythonReturnsOctetStreamContentType() throws IOException {
        UUID runId = UUID.randomUUID();
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/agent-runs", exchange -> writeOctetStreamJson(exchange, agentRunJson(runId)));
        server.start();

        PythonAgentServiceClient client = new PythonAgentServiceClient(
                RestClient.builder(),
                new ObjectMapper(),
                "http://localhost:" + server.getAddress().getPort(),
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                new IdGenerator()
        );

        try {
            AgentServiceResult result = client.run(runId, "现在要不要买苹果", "zh-CN");

            assertThat(result.report().getSubjectIdentifier()).isEqualTo("AAPL");
            assertThat(result.report().getSubjectName()).isEqualTo("Apple Inc.");
            assertThat(result.report().getTitle()).isEqualTo("苹果投研报告");
            assertThat(result.report().getKeyFindings()).contains("苹果");
            assertThat(result.evidenceItems()).hasSize(1);
            assertThat(result.toolCallRecords()).hasSize(1);
        } finally {
            server.stop(0);
        }
    }

    @Test
    void mapsFinalReportSectionsWithoutRepeatingGenericEvidenceSummary() throws IOException {
        UUID runId = UUID.randomUUID();
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/agent-runs", exchange -> writeOctetStreamJson(exchange, agentRunJsonWithOnlySecEvidence(runId)));
        server.start();

        PythonAgentServiceClient client = new PythonAgentServiceClient(
                RestClient.builder(),
                new ObjectMapper(),
                "http://localhost:" + server.getAddress().getPort(),
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                new IdGenerator()
        );

        try {
            AgentServiceResult result = client.run(runId, "现在要不要买苹果", "zh-CN");

            assertThat(result.report().getSubjectSummary()).isEqualTo("Apple Inc. 公司概览");
            assertThat(result.report().getEvidenceSummary()).isEqualTo("泛化证据摘要，不应重复填入所有栏目。");
            assertThat(result.report().getKeyFindings())
                    .contains("核心回答")
                    .contains("证据限制")
                    .doesNotContain("泛化证据摘要，不应重复填入所有栏目。");
        } finally {
            server.stop(0);
        }
    }

    @Test
    void preservesStructuredCitationsForFrontendReferenceList() throws IOException {
        UUID runId = UUID.randomUUID();
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/agent-runs", exchange -> writeOctetStreamJson(exchange, agentRunJsonWithStructuredCitations(runId)));
        server.start();

        PythonAgentServiceClient client = new PythonAgentServiceClient(
                RestClient.builder(),
                new ObjectMapper(),
                "http://localhost:" + server.getAddress().getPort(),
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                new IdGenerator()
        );

        try {
            AgentServiceResult result = client.run(runId, "苹果最近怎么样", "zh-CN");

            assertThat(result.report().getCitations()).contains("Alpha Vantage - AAPL 最新行情");
            assertThat(result.report().getCitationsJson())
                    .contains("\"id\":1")
                    .contains("\"sourceName\":\"Alpha Vantage\"")
                    .contains("\"url\":\"https://example.com/aapl\"");
            assertThat(result.report().getRawJson())
                    .contains("\"citations\":[{\"id\":1");
        } finally {
            server.stop(0);
        }
    }

    @Test
    void preservesFullAgentTraceFieldsInReportRawJson() throws IOException {
        UUID runId = UUID.randomUUID();
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/agent-runs", exchange -> writeOctetStreamJson(exchange, agentRunJsonWithFullTrace(runId)));
        server.start();

        PythonAgentServiceClient client = new PythonAgentServiceClient(
                RestClient.builder(),
                new ObjectMapper(),
                "http://localhost:" + server.getAddress().getPort(),
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                new IdGenerator()
        );

        try {
            AgentServiceResult result = client.run(runId, "我不太会看市场，帮我找研究样本", "zh-CN");

            assertThat(result.clarificationQuestions()).containsExactly("你的投资期限是多久？");
            assertThat(result.report().getRawJson())
                    .contains("\"planningDecision\"")
                    .contains("\"replanningDecision\"")
                    .contains("\"plan\"")
                    .contains("\"reasoning\"")
                    .contains("\"draftReport\"")
                    .contains("\"reflection\"")
                    .contains("\"clarificationQuestions\":[\"你的投资期限是多久？\"]");
        } finally {
            server.stop(0);
        }
    }

    @Test
    void mapsClarificationResponseWithoutFinalReport() throws IOException {
        UUID runId = UUID.randomUUID();
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/agent-runs", exchange -> writeOctetStreamJson(exchange, agentRunJsonNeedsClarification(runId)));
        server.start();

        PythonAgentServiceClient client = new PythonAgentServiceClient(
                RestClient.builder(),
                new ObjectMapper(),
                "http://localhost:" + server.getAddress().getPort(),
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                new IdGenerator()
        );

        try {
            AgentServiceResult result = client.run(runId, "对比特斯拉和纳斯达克", "zh-CN");

            assertThat(result.runStatus()).isEqualTo("NEEDS_CLARIFICATION");
            assertThat(result.clarificationQuestions()).containsExactly("你这里的“纳斯达克”是指 Nasdaq 公司（NDAQ），还是纳斯达克指数？");
            assertThat(result.report().getTitle()).contains("需要补充信息");
            assertThat(result.report().getSubjectType()).isEqualTo("ambiguous");
            assertThat(result.report().getRawJson())
                    .contains("\"runStatus\":\"NEEDS_CLARIFICATION\"")
                    .contains("\"finalReport\":null");
            assertThat(result.evidenceItems()).isEmpty();
            assertThat(result.toolCallRecords()).isEmpty();
        } finally {
            server.stop(0);
        }
    }

    private void writeOctetStreamJson(HttpExchange exchange, String body) throws IOException {
        assertThat(exchange.getRequestHeaders().getFirst(HttpHeaders.ACCEPT))
                .contains(MediaType.APPLICATION_JSON_VALUE);
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_OCTET_STREAM_VALUE);
        exchange.sendResponseHeaders(200, bytes.length);
        try (OutputStream outputStream = exchange.getResponseBody()) {
            outputStream.write(bytes);
        }
    }

    private String agentRunJson(UUID runId) {
        return """
                {
                  "runId": "%s",
                  "query": "现在要不要买苹果",
                  "understanding": {
                    "companies": [
                      {
                        "canonicalName": "Apple Inc.",
                        "candidates": [
                          {"ticker": "AAPL"}
                        ]
                      }
                    ]
                  },
                  "toolCalls": [
                    {
                      "toolName": "market_data",
                      "input": {"ticker": "AAPL"},
                      "output": {"summary": "market evidence"},
                      "status": "SUCCEEDED",
                      "latencyMs": 20
                    }
                  ],
                  "replanningDecision": {
                    "action": "CONTINUE_WITH_AVAILABLE_EVIDENCE",
                    "rationale": "已有证据足够生成谨慎研究框架。",
                    "additionalSteps": [],
                    "clarificationQuestions": [],
                    "capabilityGap": ""
                  },
                  "evidence": [
                    {
                      "sourceType": "MARKET_DATA",
                      "sourceName": "Mock Market",
                      "sourceUrl": "https://example.com/aapl",
                      "title": "AAPL market",
                      "summary": "苹果市场证据",
                      "observedAt": "2026-06-06T07:22:48Z",
                      "confidence": 0.8
                    }
                  ],
                  "finalReport": {
                    "title": "苹果投研报告",
                    "companySummary": "Apple Inc. 公司概览",
                    "questionUnderstanding": "用户询问是否买入苹果。",
                    "keyFindings": ["苹果仍需结合估值和风险判断。"],
                    "opportunities": ["生态优势"],
                    "risks": ["估值波动"],
                    "evidenceSummary": "证据摘要",
                    "uncertainty": "数据有限",
                    "citations": ["Mock Market"],
                    "nonAdvisoryStatement": "本报告不构成投资建议。"
                  }
                }
                """.formatted(runId);
    }

    private String agentRunJsonWithOnlySecEvidence(UUID runId) {
        return """
                {
                  "runId": "%s",
                  "query": "现在要不要买苹果",
                  "understanding": {
                    "companies": [
                      {
                        "canonicalName": "Apple Inc.",
                        "candidates": [
                          {"ticker": "AAPL"}
                        ]
                      }
                    ]
                  },
                  "toolCalls": [
                    {
                      "toolName": "sec_company_facts",
                      "input": {"ticker": "AAPL"},
                      "output": {"summary": "sec evidence"},
                      "status": "SUCCEEDED",
                      "latencyMs": 20
                    }
                  ],
                  "evidence": [
                    {
                      "sourceType": "SEC_COMPANY_FACTS",
                      "sourceName": "SEC EDGAR",
                      "sourceUrl": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
                      "title": "AAPL SEC facts",
                      "summary": "SEC facts generic summary",
                      "observedAt": "2026-06-06T07:22:48Z",
                      "confidence": 0.95
                    }
                  ],
                  "finalReport": {
                    "title": "苹果投研报告",
                    "companySummary": "Apple Inc. 公司概览",
                    "questionUnderstanding": "用户询问是否买入苹果。",
                    "keyFindings": ["核心结论"],
                    "sections": [
                      {
                        "title": "核心回答",
                        "content": "当前证据只能支持部分研究判断，不能直接形成买入结论。",
                        "citations": ["SEC EDGAR"]
                      },
                      {
                        "title": "证据限制",
                        "content": "新闻工具限流，缺少近期新闻证据。",
                        "citations": []
                      }
                    ],
                    "evidenceSummary": "泛化证据摘要，不应重复填入所有栏目。",
                    "uncertainty": "数据有限",
                    "citations": ["SEC EDGAR"],
                    "nonAdvisoryStatement": "本报告不构成投资建议。"
                  }
                }
                """.formatted(runId);
    }

    private String agentRunJsonWithFullTrace(UUID runId) {
        return """
                {
                  "runId": "%s",
                  "query": "我不太会看市场，帮我找研究样本",
                  "runStatus": "COMPLETED",
                  "clarificationQuestions": ["你的投资期限是多久？"],
                  "understanding": {
                    "companies": [],
                    "taskType": "BEGINNER_GUIDANCE"
                  },
                  "planningDecision": {
                    "answerability": "PARTIAL_WITH_TOOLS",
                    "needsTools": true,
                    "needsClarification": true,
                    "allowedTools": ["market_overview"],
                    "evidenceNeeds": ["market_context"],
                    "clarificationQuestions": ["你的投资期限是多久？"],
                    "maxSteps": 1,
                    "rationale": "需要先给研究框架。",
                    "objective": "生成市场探索框架。",
                    "steps": [
                      {"stepId": "overview", "toolName": "market_overview", "toolInput": {"region": "US"}}
                    ]
                  },
                  "plan": {
                    "objective": "生成市场探索框架。",
                    "steps": [
                      {"stepId": "overview", "toolName": "market_overview", "toolInput": {"region": "US"}}
                    ]
                  },
                  "toolCalls": [
                    {
                      "toolName": "market_overview",
                      "input": {"region": "US"},
                      "output": {"indexProxies": [{"symbol": "SPY"}, {"symbol": "QQQ"}]},
                      "status": "SUCCEEDED",
                      "latencyMs": 10
                    }
                  ],
                  "evidence": [
                    {
                      "sourceType": "MARKET_EXPLORATION",
                      "sourceName": "Market Exploration",
                      "sourceUrl": null,
                      "title": "市场探索",
                      "summary": "市场探索证据",
                      "observedAt": "2026-06-06T07:22:48Z",
                      "confidence": 0.8
                    }
                  ],
                  "reasoning": {
                    "thesis": "只能给研究样本。",
                    "supportingPoints": ["需要补充用户约束。"],
                    "risks": ["不应直接推荐。"],
                    "valuationNotes": [],
                    "missingData": ["投资期限"],
                    "uncertainty": "高"
                  },
                  "draftReport": {
                    "title": "市场探索",
                    "companySummary": "无具体公司",
                    "questionUnderstanding": "用户想学习市场。",
                    "keyFindings": ["仅提供研究样本。"],
                    "opportunities": ["学习宽基"],
                    "risks": ["市场风险"],
                    "evidenceSummary": "市场探索证据",
                    "uncertainty": "高",
                    "citations": [],
                    "nonAdvisoryStatement": "不构成投资建议。"
                  },
                  "reflection": {
                    "passed": true,
                    "unsupportedClaims": [],
                    "missingData": ["投资期限"],
                    "overconfidentStatements": [],
                    "revisionInstructions": []
                  },
                  "finalReport": {
                    "title": "市场探索",
                    "companySummary": "无具体公司",
                    "questionUnderstanding": "用户想学习市场。",
                    "keyFindings": ["仅提供研究样本。"],
                    "opportunities": ["学习宽基"],
                    "risks": ["市场风险"],
                    "evidenceSummary": "市场探索证据",
                    "uncertainty": "高",
                    "citations": [],
                    "nonAdvisoryStatement": "不构成投资建议。"
                  }
                }
                """.formatted(runId);
    }

    private String agentRunJsonWithStructuredCitations(UUID runId) {
        return """
                {
                  "runId": "%s",
                  "query": "苹果最近怎么样",
                  "understanding": {
                    "companies": [
                      {
                        "canonicalName": "Apple Inc.",
                        "candidates": [
                          {"ticker": "AAPL"}
                        ]
                      }
                    ]
                  },
                  "toolCalls": [],
                  "evidence": [
                    {
                      "sourceType": "MARKET_DATA",
                      "sourceName": "Alpha Vantage",
                      "sourceUrl": "https://example.com/aapl",
                      "title": "AAPL 最新行情",
                      "summary": "AAPL 行情证据",
                      "observedAt": "2026-06-06T07:22:48Z",
                      "confidence": 0.8
                    }
                  ],
                  "finalReport": {
                    "title": "苹果投研报告",
                    "answerSummary": "AAPL 短期表现需要结合行情判断。[1]",
                    "companySummary": "Apple Inc. 公司概览",
                    "questionUnderstanding": "用户询问苹果最近表现。",
                    "sections": [
                      {
                        "title": "核心回答",
                        "content": "当前只拿到行情证据，因此只能部分回答。[1]",
                        "citations": [1]
                      }
                    ],
                    "evidenceSummary": "AAPL 行情证据",
                    "uncertainty": "缺少新闻和财务证据。",
                    "citations": [
                      {
                        "id": 1,
                        "title": "AAPL 最新行情",
                        "sourceName": "Alpha Vantage",
                        "url": "https://example.com/aapl",
                        "supports": "短期行情判断"
                      }
                    ],
                    "nonAdvisoryStatement": "本报告不构成投资建议。"
                  }
                }
                """.formatted(runId);
    }

    private String agentRunJsonNeedsClarification(UUID runId) {
        return """
                {
                  "runId": "%s",
                  "query": "对比特斯拉和纳斯达克",
                  "runStatus": "NEEDS_CLARIFICATION",
                  "clarificationQuestions": ["你这里的“纳斯达克”是指 Nasdaq 公司（NDAQ），还是纳斯达克指数？"],
                  "understanding": {
                    "intentSummary": "用户希望比较特斯拉和纳斯达克相关对象。",
                    "intentBreakdown": [
                      {"point": "特斯拉可解析为 TSLA。", "planningImpact": "该对象已明确。"},
                      {"point": "纳斯达克存在歧义。", "planningImpact": "澄清前不应执行完整比较。"}
                    ],
                    "entities": [
                      {
                        "mention": "特斯拉",
                        "resolutionStatus": "RESOLVED",
                        "bestGuess": {"name": "Tesla, Inc.", "identifier": "TSLA", "typeHint": "company"},
                        "candidates": [],
                        "notes": "明确公司标的。"
                      },
                      {
                        "mention": "纳斯达克",
                        "resolutionStatus": "AMBIGUOUS",
                        "bestGuess": null,
                        "candidates": [
                          {"name": "Nasdaq, Inc.", "identifier": "NDAQ", "typeHint": "company"},
                          {"name": "Nasdaq Composite", "identifier": null, "typeHint": "index"}
                        ],
                        "notes": "可能指公司或指数。"
                      }
                    ],
                    "companies": [
                      {
                        "canonicalName": "Tesla, Inc.",
                        "candidates": [
                          {"ticker": "TSLA"}
                        ]
                      }
                    ]
                  },
                  "planningDecision": {
                    "answerability": "CLARIFICATION_REQUIRED",
                    "needsTools": false,
                    "needsClarification": true,
                    "allowedTools": [],
                    "evidenceNeeds": [],
                    "clarificationQuestions": ["你这里的“纳斯达克”是指 Nasdaq 公司（NDAQ），还是纳斯达克指数？"],
                    "maxSteps": 0,
                    "rationale": "第二个比较对象存在歧义。",
                    "objective": "澄清比较对象。",
                    "steps": []
                  },
                  "plan": {"objective": "澄清比较对象。", "steps": []},
                  "toolCalls": [],
                  "evidence": [],
                  "reasoning": null,
                  "draftReport": null,
                  "reflection": null,
                  "finalReport": null
                }
                """.formatted(runId);
    }
}
