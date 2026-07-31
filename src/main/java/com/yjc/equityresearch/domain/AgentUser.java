package com.yjc.equityresearch.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "agent_users")
public class AgentUser {
    @Id
    private UUID id;

    @Column(nullable = false, length = 100)
    private String displayName;

    @Column(nullable = false, length = 50)
    private String authProvider;

    private String externalSubject;

    @Column(nullable = false, length = 32)
    private String status;

    @Column(nullable = false)
    private OffsetDateTime createdAt;

    @Column(nullable = false)
    private OffsetDateTime updatedAt;

    protected AgentUser() {
    }

    public AgentUser(
            UUID id,
            String displayName,
            String authProvider,
            String externalSubject,
            String status,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt
    ) {
        this.id = id;
        this.displayName = displayName;
        this.authProvider = authProvider;
        this.externalSubject = externalSubject;
        this.status = status;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public UUID getId() {
        return id;
    }

    public String getDisplayName() {
        return displayName;
    }
}
