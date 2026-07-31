package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.domain.ToolCallRecord;
import com.yjc.equityresearch.domain.ToolCallStatus;
import java.time.OffsetDateTime;
import java.util.UUID;

public record ToolCallRecordResponse(
        UUID id,
        UUID jobId,
        String toolName,
        String inputJson,
        String outputJson,
        ToolCallStatus status,
        String errorMessage,
        OffsetDateTime startedAt,
        OffsetDateTime completedAt,
        long latencyMs
) {
    public static ToolCallRecordResponse from(ToolCallRecord record) {
        return new ToolCallRecordResponse(
                record.getId(),
                record.getJobId(),
                record.getToolName(),
                record.getInputJson(),
                record.getOutputJson(),
                record.getStatus(),
                record.getErrorMessage(),
                record.getStartedAt(),
                record.getCompletedAt(),
                record.getLatencyMs()
        );
    }
}
