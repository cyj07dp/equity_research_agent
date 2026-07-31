package com.yjc.equityresearch.api.dto;

import java.util.List;
import java.util.Map;

public record ResearchTraceStageResponse(
        String name,
        String status,
        String summary,
        Map<String, Object> details,
        List<ResearchTraceToolStepResponse> steps
) {
}
