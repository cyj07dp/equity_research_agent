package com.yjc.equityresearch.agent;

import static org.assertj.core.api.Assertions.assertThat;

import com.yjc.equityresearch.agent.python.AgentServiceClient;
import com.yjc.equityresearch.agent.python.AgentServiceResult;
import com.yjc.equityresearch.domain.EvidenceItem;
import com.yjc.equityresearch.domain.ResearchReport;
import com.yjc.equityresearch.domain.ToolCallRecord;
import com.yjc.equityresearch.domain.ToolCallStatus;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ResearchAgentOrchestratorTest {
    @Test
    void callsPythonAgentClientAndReturnsReportEvidenceAndToolTraces() {
        UUID jobId = UUID.randomUUID();
        AgentServiceClient client = (runId, query, locale) -> new AgentServiceResult(
                new ResearchReport(
                        UUID.randomUUID(),
                        runId,
                        "NVIDIA Corporation",
                        "company",
                        "NVDA",
                        "英伟达投研报告",
                        "中文概览",
                        "用户希望分析英伟达。",
                        "中文摘要",
                        "中文机会",
                        "中文风险",
                        "中文证据摘要",
                        "中文不确定性",
                        "",
                        "[]",
                        "不构成投资建议。",
                        "{}",
                        OffsetDateTime.now()
                ),
                List.of(new EvidenceItem(
                        UUID.randomUUID(),
                        runId,
                        "MARKET_DATA",
                        "Python Agent",
                        "https://example.com/market/NVDA",
                        "市场",
                        "中文 evidence",
                        "{\"price\":\"120.50\"}",
                        OffsetDateTime.now(),
                        new BigDecimal("0.8000")
                )),
                List.of(new ToolCallRecord(
                        UUID.randomUUID(),
                        runId,
                        "market_data",
                        "{}",
                        "{}",
                        ToolCallStatus.SUCCEEDED,
                        null,
                        OffsetDateTime.now(),
                        OffsetDateTime.now(),
                        1
                ))
        );
        ResearchAgentOrchestrator orchestrator = new ResearchAgentOrchestrator(client);

        ResearchWorkflowResult result = orchestrator.run(jobId, "帮我分析一下英伟达");

        assertThat(result.report().getSubjectIdentifier()).isEqualTo("NVDA");
        assertThat(result.report().getSubjectName()).isEqualTo("NVIDIA Corporation");
        assertThat(result.evidenceItems()).hasSize(1);
        assertThat(result.toolCallRecords()).hasSize(1);
        assertThat(result.toolCallRecords())
                .extracting(record -> record.getStatus())
                .containsOnly(ToolCallStatus.SUCCEEDED);
        assertThat(result.toolCallRecords())
                .extracting(record -> record.getToolName())
                .containsExactly("market_data");
    }
}
