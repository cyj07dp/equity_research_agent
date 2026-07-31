package com.yjc.equityresearch.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.yjc.equityresearch.api.dto.ResearchTraceResponse;
import com.yjc.equityresearch.domain.EvidenceItem;
import com.yjc.equityresearch.domain.ResearchJob;
import com.yjc.equityresearch.domain.ResearchJobStatus;
import com.yjc.equityresearch.domain.ResearchReport;
import com.yjc.equityresearch.domain.ToolCallRecord;
import com.yjc.equityresearch.domain.ToolCallStatus;
import com.yjc.equityresearch.repository.EvidenceItemRepository;
import com.yjc.equityresearch.repository.ResearchJobRepository;
import com.yjc.equityresearch.repository.ResearchReportRepository;
import com.yjc.equityresearch.repository.ToolCallRecordRepository;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ResearchTraceServiceTest {
    @Test
    void getTraceReturnsJobReportToolCallsEvidenceAndParsedAgentTrace() {
        UUID jobId = UUID.randomUUID();
        UUID reportId = UUID.randomUUID();
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchReportRepository reportRepository = org.mockito.Mockito.mock(ResearchReportRepository.class);
        EvidenceItemRepository evidenceItemRepository = org.mockito.Mockito.mock(EvidenceItemRepository.class);
        ToolCallRecordRepository toolCallRecordRepository = org.mockito.Mockito.mock(ToolCallRecordRepository.class);
        ResearchTraceService service = new ResearchTraceService(
                jobRepository,
                reportRepository,
                evidenceItemRepository,
                toolCallRecordRepository,
                new ObjectMapper()
        );
        ResearchJob job = new ResearchJob(jobId, "现在要不要买苹果", ResearchJobStatus.SUCCEEDED, OffsetDateTime.now());
        job.markSucceeded(reportId, OffsetDateTime.now());
        ResearchReport report = new ResearchReport(
                reportId,
                jobId,
                "Apple Inc.",
                "company",
                "AAPL",
                "苹果投研报告",
                "概览",
                "用户询问是否买入苹果。",
                "摘要",
                "机会",
                "风险",
                "价格摘要",
                "不确定性",
                "Alpha Vantage",
                "[]",
                "不构成投资建议。",
                """
                        {
                          "understanding": {"taskType": "INVESTMENT_THESIS"},
                          "planningDecision": {
                            "answerability": "PARTIAL_WITH_TOOLS",
                            "needsTools": true,
                            "needsClarification": true,
                            "allowedTools": ["market_data"],
                            "clarificationQuestions": ["你的投资期限是多久？"],
                            "rationale": "需要补充约束。",
                            "answerPlan": {
                              "answerGoal": "回答用户是否应该研究苹果。",
                              "sections": [
                                {"title": "核心回答", "purpose": "直接回应用户问题。"},
                                {"title": "证据限制", "purpose": "说明缺少哪些信息。"}
                              ]
                            }
                          },
                          "clarificationQuestions": ["你的投资期限是多久？"],
                          "plan": {"objective": "分析苹果", "steps": [{"toolName": "market_data"}]},
                          "dataSufficiency": {
                            "status": "PARTIAL",
                            "summary": "当前 evidence 只能支持部分回答。",
                            "expectedEvidence": ["market_data", "recent_news"],
                            "availableEvidence": ["MARKET_DATA: AAPL 行情"],
                            "missingEvidence": ["recent_news"],
                            "coverageNotes": ["缺少近期新闻。"]
                          },
                          "reasoning": {"thesis": "证据不足，保持谨慎。"},
                          "reflection": {"passed": true}
                        }
                        """,
                OffsetDateTime.now()
        );
        EvidenceItem evidence = new EvidenceItem(
                UUID.randomUUID(),
                jobId,
                "MARKET_DATA",
                "Alpha Vantage",
                "https://example.com",
                "AAPL 行情",
                "价格摘要",
                "{\"price\":\"307.34\"}",
                OffsetDateTime.now(),
                new BigDecimal("0.8600")
        );
        ToolCallRecord toolCall = new ToolCallRecord(
                UUID.randomUUID(),
                jobId,
                "market_data",
                "{\"ticker\":\"AAPL\"}",
                "{\"price\":\"307.34\"}",
                ToolCallStatus.SUCCEEDED,
                null,
                OffsetDateTime.now(),
                OffsetDateTime.now(),
                120
        );

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(reportRepository.findByJobId(jobId)).thenReturn(Optional.of(report));
        when(evidenceItemRepository.findByJobId(jobId)).thenReturn(List.of(evidence));
        when(toolCallRecordRepository.findByJobIdOrderByStartedAtAsc(jobId)).thenReturn(List.of(toolCall));

        ResearchTraceResponse response = service.getTrace(jobId);

        assertThat(response.summary().jobId()).isEqualTo(jobId);
        assertThat(response.summary().toolSuccessCount()).isEqualTo(1);
        assertThat(response.summary().toolFailureCount()).isEqualTo(0);
        assertThat(response.summary().evidenceCount()).isEqualTo(1);
        assertThat(response.summary().clarificationQuestions()).containsExactly("你的投资期限是多久？");
        assertThat(response.summary().warnings())
                .noneMatch(warning -> warning.contains("缺少近期新闻"));
        assertThat(response.report().reportId()).isEqualTo(reportId);
        assertThat(response.stages()).extracting("name")
                .contains("query_understanding", "planning_decision", "planning", "tool_execution", "evidence", "evidence_reasoning", "reflection", "final_report");
        assertThat(response.stages().stream()
                .filter(stage -> stage.name().equals("evidence_reasoning"))
                .findFirst()
                .orElseThrow()
                .summary()).contains("部分回答");
        assertThat(response.stages().stream()
                .filter(stage -> stage.name().equals("tool_execution"))
                .findFirst()
                .orElseThrow()
                .steps()).hasSize(1);
        assertThat(response.evidenceGroups()).hasSize(1);
        assertThat(response.evidenceGroups().getFirst().sourceType()).isEqualTo("MARKET_DATA");
        @SuppressWarnings("unchecked")
        Map<String, Object> understanding = (Map<String, Object>) response.rawAgentTrace().get("understanding");
        assertThat(understanding).containsEntry("taskType", "INVESTMENT_THESIS");
    }

    @Test
    void getTraceShowsClarificationAsSkippedExecutionAndWaitingReport() {
        UUID jobId = UUID.randomUUID();
        UUID reportId = UUID.randomUUID();
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchReportRepository reportRepository = org.mockito.Mockito.mock(ResearchReportRepository.class);
        EvidenceItemRepository evidenceItemRepository = org.mockito.Mockito.mock(EvidenceItemRepository.class);
        ToolCallRecordRepository toolCallRecordRepository = org.mockito.Mockito.mock(ToolCallRecordRepository.class);
        ResearchTraceService service = new ResearchTraceService(
                jobRepository,
                reportRepository,
                evidenceItemRepository,
                toolCallRecordRepository,
                new ObjectMapper()
        );
        ResearchJob job = new ResearchJob(jobId, "对比特斯拉和纳斯达克", ResearchJobStatus.NEEDS_CLARIFICATION, OffsetDateTime.now());
        job.markNeedsClarification(
                List.of("你这里的“纳斯达克”是指 Nasdaq 公司（NDAQ），还是纳斯达克指数？"),
                reportId,
                OffsetDateTime.now()
        );
        ResearchReport report = new ResearchReport(
                reportId,
                jobId,
                "特斯拉 / 纳斯达克",
                "ambiguous",
                null,
                "需要补充信息后继续研究。",
                "已识别特斯拉，但纳斯达克存在歧义。",
                "用户希望比较特斯拉和纳斯达克相关对象。",
                "等待用户澄清。",
                "等待用户澄清。",
                "等待用户澄清。",
                "等待用户澄清。",
                "",
                "",
                "[]",
                "本报告仅用于组织研究问题，不构成投资建议。",
                """
                        {
                          "runStatus": "NEEDS_CLARIFICATION",
                          "clarificationQuestions": ["你这里的“纳斯达克”是指 Nasdaq 公司（NDAQ），还是纳斯达克指数？"],
                          "understanding": {
                            "intentSummary": "用户希望比较特斯拉和纳斯达克相关对象。",
                            "entities": [
                              {"mention": "特斯拉", "resolutionStatus": "RESOLVED"},
                              {"mention": "纳斯达克", "resolutionStatus": "AMBIGUOUS"}
                            ]
                          },
                          "planningDecision": {
                            "answerability": "CLARIFICATION_REQUIRED",
                            "needsTools": false,
                            "needsClarification": true,
                            "clarificationQuestions": ["你这里的“纳斯达克”是指 Nasdaq 公司（NDAQ），还是纳斯达克指数？"]
                          },
                          "plan": {"objective": "澄清比较对象。", "steps": []},
                          "toolCalls": [],
                          "evidence": [],
                          "finalReport": null
                        }
                        """,
                OffsetDateTime.now()
        );

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(reportRepository.findByJobId(jobId)).thenReturn(Optional.of(report));
        when(evidenceItemRepository.findByJobId(jobId)).thenReturn(List.of());
        when(toolCallRecordRepository.findByJobIdOrderByStartedAtAsc(jobId)).thenReturn(List.of());

        ResearchTraceResponse response = service.getTrace(jobId);

        assertThat(response.summary().warnings()).isEmpty();
        assertThat(response.summary().clarificationQuestions())
                .containsExactly("你这里的“纳斯达克”是指 Nasdaq 公司（NDAQ），还是纳斯达克指数？");
        assertThat(response.stages().stream()
                .filter(stage -> stage.name().equals("tool_execution"))
                .findFirst()
                .orElseThrow()
                .status()).isEqualTo("skipped");
        assertThat(response.stages().stream()
                .filter(stage -> stage.name().equals("evidence"))
                .findFirst()
                .orElseThrow()
                .status()).isEqualTo("skipped");
        assertThat(response.stages().stream()
                .filter(stage -> stage.name().equals("final_report"))
                .findFirst()
                .orElseThrow()
                .status()).isEqualTo("waiting_clarification");
    }

    @Test
    void getTraceReadsExpectedEvidenceFromPythonPlanMetadataAndIgnoresUnknownTools() {
        UUID jobId = UUID.randomUUID();
        UUID reportId = UUID.randomUUID();
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchReportRepository reportRepository = org.mockito.Mockito.mock(ResearchReportRepository.class);
        EvidenceItemRepository evidenceItemRepository = org.mockito.Mockito.mock(EvidenceItemRepository.class);
        ToolCallRecordRepository toolCallRecordRepository = org.mockito.Mockito.mock(ToolCallRecordRepository.class);
        ResearchTraceService service = new ResearchTraceService(
                jobRepository,
                reportRepository,
                evidenceItemRepository,
                toolCallRecordRepository,
                new ObjectMapper()
        );
        ResearchJob job = new ResearchJob(jobId, "分析苹果年报风险", ResearchJobStatus.SUCCEEDED, OffsetDateTime.now());
        job.markSucceeded(reportId, OffsetDateTime.now());
        ResearchReport report = new ResearchReport(
                reportId,
                jobId,
                "Apple Inc.",
                "company",
                "AAPL",
                "苹果风险报告",
                "概览",
                "用户询问年报风险。",
                "摘要",
                "",
                "",
                "",
                "",
                "",
                "[]",
                "本报告不构成投资建议。",
                """
                        {
                          "runtimeWarnings": ["工具已执行但未获得可用于支撑回答的 evidence。"],
                          "plan": {
                            "objective": "分析苹果年报风险。",
                            "steps": [
                              {
                                "toolName": "sec_filing_retriever",
                                "outputEvidenceType": "SEC_RAG",
                                "expectedEvidenceTypes": ["SEC_RAG"]
                              },
                              {
                                "toolName": "future_tool_without_java_mapping"
                              }
                            ]
                          }
                        }
                        """,
                OffsetDateTime.now()
        );

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(reportRepository.findByJobId(jobId)).thenReturn(Optional.of(report));
        when(evidenceItemRepository.findByJobId(jobId)).thenReturn(List.of());
        when(toolCallRecordRepository.findByJobIdOrderByStartedAtAsc(jobId)).thenReturn(List.of());

        assertThatCode(() -> service.getTrace(jobId)).doesNotThrowAnyException();
        ResearchTraceResponse response = service.getTrace(jobId);

        assertThat(response.summary().warnings())
                .contains("计划调用 sec_filing_retriever，但未获得 SEC_RAG evidence。");
        assertThat(response.summary().warnings())
                .contains("运行降级：工具已执行但未获得可用于支撑回答的 evidence。");
        assertThat(response.summary().warnings())
                .noneMatch(warning -> warning.contains("future_tool_without_java_mapping"));
    }
}
