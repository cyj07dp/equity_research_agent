package com.yjc.equityresearch.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "agent_user_preferences")
public class AgentUserPreference {
    @Id
    private UUID id;

    @Column(nullable = false)
    private UUID userId;

    @Column(nullable = false, length = 32)
    private String preferredLocale;

    @Column(length = 32)
    private String defaultMarket;

    @Column(length = 32)
    private String riskTolerance;

    @Column(length = 32)
    private String timeHorizon;

    @Column(length = 32)
    private String reportStyle;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String preferredSectors;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String excludedSectors;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String preferredAssets;

    @Column(columnDefinition = "TEXT")
    private String notes;

    @Column(nullable = false, length = 32)
    private String memorySource;

    @Column(nullable = false, precision = 5, scale = 4)
    private BigDecimal confidence;

    @Column(nullable = false)
    private boolean enabled;

    @Column(nullable = false)
    private OffsetDateTime createdAt;

    @Column(nullable = false)
    private OffsetDateTime updatedAt;

    protected AgentUserPreference() {
    }

    public AgentUserPreference(
            UUID id,
            UUID userId,
            String preferredLocale,
            String defaultMarket,
            String riskTolerance,
            String timeHorizon,
            String reportStyle,
            String preferredSectors,
            String excludedSectors,
            String preferredAssets,
            String notes,
            String memorySource,
            BigDecimal confidence,
            boolean enabled,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt
    ) {
        this.id = id;
        this.userId = userId;
        this.preferredLocale = preferredLocale;
        this.defaultMarket = defaultMarket;
        this.riskTolerance = riskTolerance;
        this.timeHorizon = timeHorizon;
        this.reportStyle = reportStyle;
        this.preferredSectors = preferredSectors;
        this.excludedSectors = excludedSectors;
        this.preferredAssets = preferredAssets;
        this.notes = notes;
        this.memorySource = memorySource;
        this.confidence = confidence;
        this.enabled = enabled;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public void update(
            String preferredLocale,
            String defaultMarket,
            String riskTolerance,
            String timeHorizon,
            String reportStyle,
            String preferredSectors,
            String excludedSectors,
            String preferredAssets,
            String notes,
            boolean enabled,
            OffsetDateTime now
    ) {
        this.preferredLocale = preferredLocale;
        this.defaultMarket = defaultMarket;
        this.riskTolerance = riskTolerance;
        this.timeHorizon = timeHorizon;
        this.reportStyle = reportStyle;
        this.preferredSectors = preferredSectors;
        this.excludedSectors = excludedSectors;
        this.preferredAssets = preferredAssets;
        this.notes = notes;
        this.enabled = enabled;
        this.memorySource = "USER_PROVIDED";
        this.confidence = BigDecimal.ONE.setScale(4);
        this.updatedAt = now;
    }

    public UUID getId() {
        return id;
    }

    public UUID getUserId() {
        return userId;
    }

    public String getPreferredLocale() {
        return preferredLocale;
    }

    public String getDefaultMarket() {
        return defaultMarket;
    }

    public String getRiskTolerance() {
        return riskTolerance;
    }

    public String getTimeHorizon() {
        return timeHorizon;
    }

    public String getReportStyle() {
        return reportStyle;
    }

    public String getPreferredSectors() {
        return preferredSectors;
    }

    public String getExcludedSectors() {
        return excludedSectors;
    }

    public String getPreferredAssets() {
        return preferredAssets;
    }

    public String getNotes() {
        return notes;
    }

    public String getMemorySource() {
        return memorySource;
    }

    public BigDecimal getConfidence() {
        return confidence;
    }

    public boolean isEnabled() {
        return enabled;
    }
}
