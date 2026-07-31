package com.yjc.equityresearch.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "research_jobs")
public class ResearchJob {
    @Id
    private UUID id;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String query;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private ResearchJobStatus status;

    @Column(nullable = false)
    private OffsetDateTime createdAt;

    private OffsetDateTime startedAt;

    private OffsetDateTime completedAt;

    @Column(columnDefinition = "TEXT")
    private String errorMessage;

    @Column(columnDefinition = "TEXT")
    private String clarificationQuestions;

    private UUID conversationId;

    private UUID triggerMessageId;

    private UUID reportId;

    protected ResearchJob() {
    }

    public ResearchJob(UUID id, String query, ResearchJobStatus status, OffsetDateTime createdAt) {
        this.id = id;
        this.query = query;
        this.status = status;
        this.createdAt = createdAt;
    }

    public ResearchJob(
            UUID id,
            String query,
            ResearchJobStatus status,
            OffsetDateTime createdAt,
            UUID conversationId,
            UUID triggerMessageId
    ) {
        this(id, query, status, createdAt);
        this.conversationId = conversationId;
        this.triggerMessageId = triggerMessageId;
    }

    public UUID getId() {
        return id;
    }

    public String getQuery() {
        return query;
    }

    public ResearchJobStatus getStatus() {
        return status;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public OffsetDateTime getCompletedAt() {
        return completedAt;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public List<String> getClarificationQuestions() {
        if (clarificationQuestions == null || clarificationQuestions.isBlank()) {
            return List.of();
        }
        return Arrays.stream(clarificationQuestions.split("\\R"))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .toList();
    }

    public UUID getReportId() {
        return reportId;
    }

    public UUID getConversationId() {
        return conversationId;
    }

    public UUID getTriggerMessageId() {
        return triggerMessageId;
    }

    public void markRunning(OffsetDateTime startedAt) {
        this.status = ResearchJobStatus.RUNNING;
        this.startedAt = startedAt;
        this.clarificationQuestions = null;
    }

    public void markSucceeded(UUID reportId, OffsetDateTime completedAt) {
        this.status = ResearchJobStatus.SUCCEEDED;
        this.reportId = reportId;
        this.completedAt = completedAt;
        this.errorMessage = null;
        this.clarificationQuestions = null;
    }

    public void markNeedsClarification(List<String> clarificationQuestions, UUID reportId, OffsetDateTime completedAt) {
        this.status = ResearchJobStatus.NEEDS_CLARIFICATION;
        this.reportId = reportId;
        this.completedAt = completedAt;
        this.errorMessage = null;
        this.clarificationQuestions = String.join("\n", clarificationQuestions == null ? List.of() : clarificationQuestions);
    }

    public void markFailed(String errorMessage, OffsetDateTime completedAt) {
        this.status = ResearchJobStatus.FAILED;
        this.errorMessage = errorMessage;
        this.completedAt = completedAt;
        this.clarificationQuestions = null;
    }
}
