package com.yjc.equityresearch.api.dto;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.yjc.equityresearch.domain.ResearchReport;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public record ResearchReportResponse(
        UUID reportId,
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
        List<ResearchCitationResponse> structuredCitations,
        String nonAdvisoryStatement,
        String rawJson,
        OffsetDateTime createdAt
) {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    public static ResearchReportResponse from(ResearchReport report) {
        return new ResearchReportResponse(
                report.getId(),
                report.getJobId(),
                report.getSubjectName(),
                report.getSubjectType(),
                report.getSubjectIdentifier(),
                report.getTitle(),
                report.getSubjectSummary(),
                report.getQuestionUnderstanding(),
                report.getKeyFindings(),
                report.getOpportunities(),
                report.getRisks(),
                report.getEvidenceSummary(),
                report.getUncertainty(),
                report.getCitations(),
                structuredCitations(report.getCitationsJson()),
                report.getNonAdvisoryStatement(),
                report.getRawJson(),
                report.getCreatedAt()
        );
    }

    private static List<ResearchCitationResponse> structuredCitations(String citationsJson) {
        if (citationsJson == null || citationsJson.isBlank()) {
            return List.of();
        }
        try {
            List<Map<String, Object>> items = OBJECT_MAPPER.readValue(
                    citationsJson,
                    new TypeReference<>() {
                    }
            );
            return items.stream()
                    .map(ResearchReportResponse::citationResponse)
                    .toList();
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private static ResearchCitationResponse citationResponse(Map<String, Object> item) {
        return new ResearchCitationResponse(
                intValue(item.get("id")),
                stringValue(item.get("title")),
                stringValue(item.get("sourceName")),
                stringValue(item.get("url")),
                stringValue(item.get("supports"))
        );
    }

    private static int intValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (Exception ignored) {
            return 0;
        }
    }

    private static String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }
}
