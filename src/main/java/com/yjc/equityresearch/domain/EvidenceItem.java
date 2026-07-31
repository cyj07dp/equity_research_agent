package com.yjc.equityresearch.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "evidence_items")
public class EvidenceItem {
    @Id
    private UUID id;

    private UUID jobId;

    @Column(nullable = false, length = 64)
    private String sourceType;

    @Column(nullable = false)
    private String sourceName;

    @Column(columnDefinition = "TEXT")
    private String sourceUrl;

    @Column(nullable = false, length = 500)
    private String title;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String summary;

    @Column(columnDefinition = "TEXT")
    private String rawContent;

    @Column(nullable = false)
    private OffsetDateTime observedAt;

    @Column(nullable = false, precision = 5, scale = 4)
    private BigDecimal confidence;

    protected EvidenceItem() {
    }

    public EvidenceItem(
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
        this.id = id;
        this.jobId = jobId;
        this.sourceType = sourceType;
        this.sourceName = sourceName;
        this.sourceUrl = sourceUrl;
        this.title = title;
        this.summary = summary;
        this.rawContent = rawContent;
        this.observedAt = observedAt;
        this.confidence = confidence;
    }

    public UUID getId() {
        return id;
    }

    public UUID getJobId() {
        return jobId;
    }

    public String getSourceType() {
        return sourceType;
    }

    public String getSourceName() {
        return sourceName;
    }

    public String getSourceUrl() {
        return sourceUrl;
    }

    public String getTitle() {
        return title;
    }

    public String getSummary() {
        return summary;
    }

    public String getRawContent() {
        return rawContent;
    }

    public OffsetDateTime getObservedAt() {
        return observedAt;
    }

    public BigDecimal getConfidence() {
        return confidence;
    }

    public EvidenceItem withJobId(UUID jobId) {
        return new EvidenceItem(id, jobId, sourceType, sourceName, sourceUrl, title, summary, rawContent, observedAt, confidence);
    }
}
