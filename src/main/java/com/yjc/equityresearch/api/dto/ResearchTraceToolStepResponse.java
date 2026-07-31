package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.domain.ToolCallStatus;
import java.util.Map;

public record ResearchTraceToolStepResponse(
        String toolName,
        ToolCallStatus status,
        long latencyMs,
        String summary,
        String error,
        Map<String, Object> input,
        Map<String, Object> output
) {
}
