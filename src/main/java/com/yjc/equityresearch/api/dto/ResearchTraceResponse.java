package com.yjc.equityresearch.api.dto;

import java.util.List;
import java.util.Map;

public record ResearchTraceResponse(
        ResearchTraceSummaryResponse summary,
        ResearchReportResponse report,
        List<ResearchTraceStageResponse> stages,
        List<EvidenceGroupResponse> evidenceGroups,
        Map<String, Object> rawAgentTrace
) {
}
