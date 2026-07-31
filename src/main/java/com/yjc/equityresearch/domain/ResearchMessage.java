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
@Table(name = "research_messages")
public class ResearchMessage {
    @Id
    private UUID id;

    @Column(nullable = false)
    private UUID conversationId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private ResearchMessageRole role;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 64)
    private ResearchMessageType messageType;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    private UUID jobId;

    @Column(nullable = false)
    private OffsetDateTime createdAt;

    protected ResearchMessage() {
    }

    public ResearchMessage(
            UUID id,
            UUID conversationId,
            ResearchMessageRole role,
            ResearchMessageType messageType,
            String content,
            UUID jobId,
            OffsetDateTime createdAt
    ) {
        this.id = id;
        this.conversationId = conversationId;
        this.role = role;
        this.messageType = messageType;
        this.content = content;
        this.jobId = jobId;
        this.createdAt = createdAt;
    }

    public UUID getId() {
        return id;
    }

    public UUID getConversationId() {
        return conversationId;
    }

    public ResearchMessageRole getRole() {
        return role;
    }

    public ResearchMessageType getMessageType() {
        return messageType;
    }

    public String getContent() {
        return content;
    }

    public UUID getJobId() {
        return jobId;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void attachJob(UUID jobId) {
        this.jobId = jobId;
    }
}
