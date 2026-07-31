package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.domain.ResearchJob;
import com.yjc.equityresearch.domain.ResearchJobStatus;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

public record ResearchJobResponse(
        UUID jobId,
        String query,
        ResearchJobStatus status,
        UUID conversationId,
        UUID triggerMessageId,
        UUID reportId,
        String errorMessage,
        List<String> clarificationQuestions,
        OffsetDateTime createdAt,
        OffsetDateTime startedAt,
        OffsetDateTime completedAt
) {
    public static ResearchJobResponse from(ResearchJob job) {
        return new ResearchJobResponse(
                job.getId(),
                job.getQuery(),
                job.getStatus(),
                job.getConversationId(),
                job.getTriggerMessageId(),
                job.getReportId(),
                job.getErrorMessage(),
                job.getClarificationQuestions(),
                job.getCreatedAt(),
                job.getStartedAt(),
                job.getCompletedAt()
        );
    }
}
