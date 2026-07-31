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

class ResearchAgentOrchestratorPythonClientTest {
    @Test
    void delegatesToPythonAgentServiceWithNaturalLanguageQuery() {
        UUID jobId = UUID.randomUUID();
        AgentServiceClient client = (runId, query, locale) -> new AgentServiceResult(
                new ResearchReport(
                        UUID.randomUUID(),
                        runId,
                        "NVIDIA Corporation",
                        "company",
                        "NVDA",
                        "英伟达投研报告",
                        "中文公司概览",
                        "用户希望分析英伟达。",
                        "中文执行摘要",
                        "中文机会",
                        "中文风险",
                        "中文证据摘要",
                        "中文不确定性",
                        "",
                        "[]",
                        "本报告不构成投资建议。",
                        "{\"finalReport\":true}",
                        OffsetDateTime.now()
                ),
                List.of(new EvidenceItem(
                        UUID.randomUUID(),
                        runId,
                        "MARKET_DATA",
                        "Python Agent",
                        "https://example.com/market/NVDA",
                        "市场数据",
                        "中文 evidence",
                        "{\"price\":\"120.50\"}",
                        OffsetDateTime.now(),
                        new BigDecimal("0.8000")
                )),
                List.of(new ToolCallRecord(
                        UUID.randomUUID(),
                        runId,
                        "market_data",
                        "{\"ticker\":\"NVDA\"}",
                        "{\"summary\":\"中文 evidence\"}",
                        ToolCallStatus.SUCCEEDED,
                        null,
                        OffsetDateTime.now(),
                        OffsetDateTime.now(),
                        10
                ))
        );
        ResearchAgentOrchestrator orchestrator = new ResearchAgentOrchestrator(client);

        ResearchWorkflowResult result = orchestrator.run(jobId, "帮我生成一份英伟达中文投研报告");

        assertThat(result.report().getKeyFindings()).isEqualTo("中文执行摘要");
        assertThat(result.report().getNonAdvisoryStatement()).contains("不构成投资建议");
        assertThat(result.evidenceItems()).hasSize(1);
        assertThat(result.toolCallRecords()).hasSize(1);
    }
}
