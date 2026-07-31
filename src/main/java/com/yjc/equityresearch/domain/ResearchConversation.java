package com.yjc.equityresearch.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "research_conversations")
public class ResearchConversation {
    @Id
    private UUID id;

    @Column(nullable = false)
    private String title;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private ResearchConversationStatus status;

    @Column(nullable = false)
    private OffsetDateTime createdAt;

    @Column(nullable = false)
    private OffsetDateTime updatedAt;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String conversationSummary = "";

    protected ResearchConversation() {
    }

    public ResearchConversation(
            UUID id,
            String title,
            ResearchConversationStatus status,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt
    ) {
        this.id = id;
        this.title = title;
        this.status = status;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.conversationSummary = "";
    }

    public UUID getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public ResearchConversationStatus getStatus() {
        return status;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public String getConversationSummary() {
        return conversationSummary == null ? "" : conversationSummary;
    }

    public void updateConversationSummary(String conversationSummary, OffsetDateTime now) {
        this.conversationSummary = conversationSummary == null ? "" : conversationSummary;
        this.updatedAt = now;
    }

    public void markRunning(OffsetDateTime now) {
        this.status = ResearchConversationStatus.RUNNING;
        this.updatedAt = now;
    }

    public void markWaitingUser(OffsetDateTime now) {
        this.status = ResearchConversationStatus.WAITING_USER;
        this.updatedAt = now;
    }

    public void markActive(OffsetDateTime now) {
        this.status = ResearchConversationStatus.ACTIVE;
        this.updatedAt = now;
    }

    public void markFailed(OffsetDateTime now) {
        this.status = ResearchConversationStatus.FAILED;
        this.updatedAt = now;
    }
}
