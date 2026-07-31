package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.domain.ResearchJob;
import com.yjc.equityresearch.domain.ResearchJobStatus;
import java.util.UUID;

public record CreateResearchJobResponse(UUID jobId, ResearchJobStatus status) {
    public static CreateResearchJobResponse from(ResearchJob job) {
        return new CreateResearchJobResponse(job.getId(), job.getStatus());
    }
}
