package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.domain.EvidenceItem;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

public record EvidenceItemResponse(
        UUID id,
        UUID jobId,
        String sourceType,
        String sourceName,
        String sourceUrl,
        String title,
        String summary,
        String rawContent,
        OffsetDateTime observedAt,
        BigDecimal confidence
) {
    public static EvidenceItemResponse from(EvidenceItem item) {
        return new EvidenceItemResponse(
                item.getId(),
                item.getJobId(),
                item.getSourceType(),
                item.getSourceName(),
                item.getSourceUrl(),
                item.getTitle(),
                item.getSummary(),
                item.getRawContent(),
                item.getObservedAt(),
                item.getConfidence()
        );
    }
}
