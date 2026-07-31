package com.yjc.equityresearch.agent.python;

import com.yjc.equityresearch.domain.EvidenceItem;
import com.yjc.equityresearch.domain.ResearchReport;
import com.yjc.equityresearch.domain.ToolCallRecord;
import java.util.List;

public record AgentServiceResult(
        ResearchReport report,
        List<EvidenceItem> evidenceItems,
        List<ToolCallRecord> toolCallRecords,
        String runStatus,
        List<String> clarificationQuestions
) {
    public AgentServiceResult(
            ResearchReport report,
            List<EvidenceItem> evidenceItems,
            List<ToolCallRecord> toolCallRecords
    ) {
        this(report, evidenceItems, toolCallRecords, "COMPLETED", List.of());
    }
}
