package com.yjc.equityresearch.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "tool_call_records")
public class ToolCallRecord {
    @Id
    private UUID id;

    @Column(nullable = false)
    private UUID jobId;

    @Column(nullable = false, length = 128)
    private String toolName;

    @Column(nullable = false, columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private String inputJson;

    @Column(columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private String outputJson;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private ToolCallStatus status;

    @Column(columnDefinition = "TEXT")
    private String errorMessage;

    @Column(nullable = false)
    private OffsetDateTime startedAt;

    @Column(nullable = false)
    private OffsetDateTime completedAt;

    @Column(nullable = false)
    private long latencyMs;

    protected ToolCallRecord() {
    }

    public ToolCallRecord(
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
        this.id = id;
        this.jobId = jobId;
        this.toolName = toolName;
        this.inputJson = inputJson;
        this.outputJson = outputJson;
        this.status = status;
        this.errorMessage = errorMessage;
        this.startedAt = startedAt;
        this.completedAt = completedAt;
        this.latencyMs = latencyMs;
    }

    public UUID getId() {
        return id;
    }

    public UUID getJobId() {
        return jobId;
    }

    public String getToolName() {
        return toolName;
    }

    public String getInputJson() {
        return inputJson;
    }

    public String getOutputJson() {
        return outputJson;
    }

    public ToolCallStatus getStatus() {
        return status;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public OffsetDateTime getCompletedAt() {
        return completedAt;
    }

    public long getLatencyMs() {
        return latencyMs;
    }
}
