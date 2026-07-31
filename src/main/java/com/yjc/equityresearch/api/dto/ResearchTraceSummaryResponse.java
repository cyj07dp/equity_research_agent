package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.domain.ResearchJobStatus;
import java.util.List;
import java.util.UUID;

public record ResearchTraceSummaryResponse(
        UUID jobId,
        String query,
        ResearchJobStatus status,
        String subjectName,
        String subjectType,
        String subjectIdentifier,
        int toolSuccessCount,
        int toolFailureCount,
        int evidenceCount,
        List<String> warnings,
        List<String> clarificationQuestions
) {
}
