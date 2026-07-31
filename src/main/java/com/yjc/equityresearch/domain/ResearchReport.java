package com.yjc.equityresearch.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "research_reports")
public class ResearchReport {
    @Id
    private UUID id;

    @Column(nullable = false, unique = true)
    private UUID jobId;

    @Column(nullable = false)
    private String subjectName;

    @Column(nullable = false, length = 64)
    private String subjectType;

    @Column(length = 128)
    private String subjectIdentifier;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String subjectSummary;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String questionUnderstanding;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String keyFindings;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String opportunities;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String risks;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String evidenceSummary;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String uncertainty;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String citations;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String citationsJson;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String nonAdvisoryStatement;

    @Column(nullable = false, columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private String rawJson;

    @Column(nullable = false)
    private OffsetDateTime createdAt;

    protected ResearchReport() {
    }

    public ResearchReport(
            UUID id,
            UUID jobId,
            String subjectName,
            String subjectType,
            String subjectIdentifier,
            String title,
            String subjectSummary,
            String questionUnderstanding,
            String keyFindings,
            String opportunities,
            String risks,
            String evidenceSummary,
            String uncertainty,
            String citations,
            String citationsJson,
            String nonAdvisoryStatement,
            String rawJson,
            OffsetDateTime createdAt
    ) {
        this.id = id;
        this.jobId = jobId;
        this.subjectName = subjectName;
        this.subjectType = subjectType;
        this.subjectIdentifier = subjectIdentifier;
        this.title = title;
        this.subjectSummary = subjectSummary;
        this.questionUnderstanding = questionUnderstanding;
        this.keyFindings = keyFindings;
        this.opportunities = opportunities;
        this.risks = risks;
        this.evidenceSummary = evidenceSummary;
        this.uncertainty = uncertainty;
        this.citations = citations;
        this.citationsJson = citationsJson;
        this.nonAdvisoryStatement = nonAdvisoryStatement;
        this.rawJson = rawJson;
        this.createdAt = createdAt;
    }

    public UUID getId() {
        return id;
    }

    public UUID getJobId() {
        return jobId;
    }

    public String getSubjectName() {
        return subjectName;
    }

    public String getSubjectType() {
        return subjectType;
    }

    public String getSubjectIdentifier() {
        return subjectIdentifier;
    }

    public String getTitle() {
        return title;
    }

    public String getSubjectSummary() {
        return subjectSummary;
    }

    public String getQuestionUnderstanding() {
        return questionUnderstanding;
    }

    public String getKeyFindings() {
        return keyFindings;
    }

    public String getOpportunities() {
        return opportunities;
    }

    public String getRisks() {
        return risks;
    }

    public String getEvidenceSummary() {
        return evidenceSummary;
    }

    public String getUncertainty() {
        return uncertainty;
    }

    public String getCitations() {
        return citations;
    }

    public String getCitationsJson() {
        return citationsJson;
    }

    public String getNonAdvisoryStatement() {
        return nonAdvisoryStatement;
    }

    public String getRawJson() {
        return rawJson;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }
}
