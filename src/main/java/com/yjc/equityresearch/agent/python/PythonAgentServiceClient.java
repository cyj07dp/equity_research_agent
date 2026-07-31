package com.yjc.equityresearch.agent.python;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.yjc.equityresearch.config.IdGenerator;
import com.yjc.equityresearch.domain.EvidenceItem;
import com.yjc.equityresearch.domain.ResearchReport;
import com.yjc.equityresearch.domain.ToolCallRecord;
import com.yjc.equityresearch.domain.ToolCallStatus;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class PythonAgentServiceClient implements AgentServiceClient {
    private static final Logger log = LoggerFactory.getLogger(PythonAgentServiceClient.class);

    private final RestClient restClient;
    private final ObjectMapper objectMapper;
    private final String baseUrl;
    private final IdGenerator idGenerator;

    public PythonAgentServiceClient(
            RestClient.Builder restClientBuilder,
            ObjectMapper objectMapper,
            @Value("${agent.service.base-url:http://localhost:8000}") String baseUrl,
            @Value("${agent.service.connect-timeout:5s}") Duration connectTimeout,
            @Value("${agent.service.read-timeout:180s}") Duration readTimeout,
            IdGenerator idGenerator
    ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(connectTimeout);
        requestFactory.setReadTimeout(readTimeout);
        this.restClient = restClientBuilder
                .baseUrl(baseUrl)
                .requestFactory(requestFactory)
                .build();
        this.objectMapper = objectMapper;
        this.baseUrl = baseUrl;
        this.idGenerator = idGenerator;
    }

    @Override
    public AgentServiceResult run(UUID runId, String query, String locale) {
        return run(runId, query, locale, List.of());
    }

    @Override
    public AgentServiceResult run(
            UUID runId,
            String query,
            String locale,
            List<AgentConversationMessage> conversationMessages
    ) {
        return run(runId, query, locale, conversationMessages, AgentUserPreferences.empty());
    }

    @Override
    public AgentServiceResult run(
            UUID runId,
            String query,
            String locale,
            List<AgentConversationMessage> conversationMessages,
            AgentUserPreferences userPreferences
    ) {
        log.info("Calling Python agent-service runId={} baseUrl={} queryLength={}", runId, baseUrl, query.length());
        byte[] responseBody = restClient.post()
                .uri("/agent-runs")
                .accept(MediaType.APPLICATION_JSON)
                .body(new AgentRunRequest(
                        runId,
                        query,
                        locale,
                        conversationMessages == null ? List.of() : conversationMessages,
                        userPreferences == null ? AgentUserPreferences.empty() : userPreferences
                ))
                .exchange((request, response) -> {
                    byte[] body = response.getBody().readAllBytes();
                    if (response.getStatusCode().isError()) {
                        throw new IllegalStateException("Python agent-service returned HTTP "
                                + response.getStatusCode() + ": " + snippet(new String(body, StandardCharsets.UTF_8)));
                    }
                    return body;
                });
        AgentRunResponse response = parseResponse(responseBody);
        if (response == null) {
            throw new IllegalStateException("Python agent-service returned an empty response");
        }
        log.info(
                "Python agent-service returned runId={} evidenceCount={} toolCallCount={}",
                response.runId(),
                listOrEmpty(response.evidence()).size(),
                listOrEmpty(response.toolCalls()).size()
        );
        return mapResponse(response);
    }

    @Override
    public String summarizeConversation(
            List<AgentConversationMessage> conversationMessages,
            String existingSummary,
            String locale
    ) {
        log.info(
                "Calling Python conversation-summary baseUrl={} messageCount={} existingSummaryLength={}",
                baseUrl,
                conversationMessages == null ? 0 : conversationMessages.size(),
                existingSummary == null ? 0 : existingSummary.length()
        );
        byte[] responseBody = restClient.post()
                .uri("/conversation-summary")
                .accept(MediaType.APPLICATION_JSON)
                .body(new ConversationSummaryRequest(
                        conversationMessages == null ? List.of() : conversationMessages,
                        parseJsonObjectOrEmpty(existingSummary),
                        locale == null || locale.isBlank() ? "zh-CN" : locale
                ))
                .exchange((request, response) -> {
                    byte[] body = response.getBody().readAllBytes();
                    if (response.getStatusCode().isError()) {
                        throw new IllegalStateException("Python conversation-summary returned HTTP "
                                + response.getStatusCode() + ": " + snippet(new String(body, StandardCharsets.UTF_8)));
                    }
                    return body;
                });
        ConversationSummaryResponse response = parseSummaryResponse(responseBody);
        return toJson(response.summary());
    }

    private AgentRunResponse parseResponse(byte[] responseBody) {
        if (responseBody == null || responseBody.length == 0) {
            throw new IllegalStateException("Python agent-service returned an empty response");
        }
        String responseText = new String(responseBody, StandardCharsets.UTF_8);
        try {
            return objectMapper.readValue(responseText, AgentRunResponse.class);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Failed to parse Python agent-service response: "
                    + snippet(responseText), exception);
        }
    }

    private ConversationSummaryResponse parseSummaryResponse(byte[] responseBody) {
        if (responseBody == null || responseBody.length == 0) {
            throw new IllegalStateException("Python conversation-summary returned an empty response");
        }
        String responseText = new String(responseBody, StandardCharsets.UTF_8);
        try {
            return objectMapper.readValue(responseText, ConversationSummaryResponse.class);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Failed to parse Python conversation-summary response: "
                    + snippet(responseText), exception);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseJsonObjectOrEmpty(String value) {
        if (value == null || value.isBlank()) {
            return Map.of();
        }
        try {
            Object parsed = objectMapper.readValue(value, Object.class);
            if (parsed instanceof Map<?, ?> map) {
                return (Map<String, Object>) map;
            }
            return Map.of();
        } catch (JsonProcessingException exception) {
            return Map.of();
        }
    }

    private AgentServiceResult mapResponse(AgentRunResponse response) {
        SubjectPayload subject = resolveSubject(response);
        ResearchReportPayload finalReport = response.finalReport() == null
                ? clarificationReport(response)
                : response.finalReport();
        String rawJson = toJson(response);
        List<Map<String, Object>> citations = normalizedCitations(finalReport.citations(), response.evidence());
        ResearchReport report = new ResearchReport(
                idGenerator.newId(),
                response.runId(),
                subject.name(),
                subject.type(),
                subject.identifier(),
                textOrFallback(finalReport.title(), "研究报告"),
                textOrFallback(finalReport.companySummary(), subject.name()),
                textOrFallback(finalReport.questionUnderstanding(), "用户问题：" + response.query()),
                textOrFallback(sectionsText(finalReport.sections()), joinOrFallback(finalReport.keyFindings(), finalReport.title())),
                joinOrFallback(finalReport.opportunities(), ""),
                joinOrFallback(finalReport.risks(), ""),
                textOrFallback(finalReport.evidenceSummary(), evidenceSummary(response.evidence())),
                textOrFallback(finalReport.uncertainty(), "当前证据不足，结论需要保持谨慎。"),
                legacyCitationsText(citations),
                toJson(citations),
                textOrFallback(finalReport.nonAdvisoryStatement(), "本报告不构成投资建议。"),
                rawJson,
                OffsetDateTime.now()
        );

        List<EvidenceItem> evidenceItems = listOrEmpty(response.evidence()).stream()
                .map(item -> new EvidenceItem(
                        idGenerator.newId(),
                        response.runId(),
                        item.sourceType(),
                        item.sourceName(),
                        item.sourceUrl(),
                        item.title(),
                        item.summary(),
                        item.rawContent(),
                        parseTimeOrNow(item.observedAt()),
                        BigDecimal.valueOf(item.confidence())
                ))
                .toList();
        List<ToolCallRecord> toolCallRecords = listOrEmpty(response.toolCalls()).stream()
                .map(call -> new ToolCallRecord(
                        idGenerator.newId(),
                        response.runId(),
                        call.toolName(),
                        toJson(call.input()),
                        toJson(call.output()),
                        "SUCCEEDED".equalsIgnoreCase(call.status()) ? ToolCallStatus.SUCCEEDED : ToolCallStatus.FAILED,
                        "SUCCEEDED".equalsIgnoreCase(call.status()) ? null : toJson(call.output()),
                        OffsetDateTime.now(),
                        OffsetDateTime.now(),
                        call.latencyMs()
                ))
                .toList();
        return new AgentServiceResult(
                report,
                evidenceItems,
                toolCallRecords,
                runStatusOrCompleted(response.runStatus()),
                response.clarificationQuestions() == null ? List.of() : response.clarificationQuestions()
        );
    }

    private SubjectPayload resolveSubject(AgentRunResponse response) {
        if (response.understanding() != null && response.understanding().entities() != null) {
            if ("NEEDS_CLARIFICATION".equalsIgnoreCase(response.runStatus())
                    && response.understanding().entities().stream()
                    .anyMatch(entity -> "AMBIGUOUS".equalsIgnoreCase(entity.resolutionStatus())
                            || "UNRESOLVED".equalsIgnoreCase(entity.resolutionStatus()))) {
                String name = response.understanding().entities().stream()
                        .map(ResearchEntityPayload::mention)
                        .filter(value -> value != null && !value.isBlank())
                        .reduce((left, right) -> left + " / " + right)
                        .orElse("未明确研究对象");
                return new SubjectPayload(name, "ambiguous", null);
            }
            for (ResearchEntityPayload entity : response.understanding().entities()) {
                SubjectPayload subject = subjectFromEntity(entity);
                if (subject != null) {
                    return subject;
                }
            }
        }
        if (response.understanding() != null && response.understanding().companies() != null) {
            return response.understanding().companies().stream()
                    .findFirst()
                    .map(company -> new SubjectPayload(
                            textOrFallback(company.canonicalName(), "未明确研究对象"),
                            "company",
                            company.candidates() == null || company.candidates().isEmpty()
                                    ? null
                                    : company.candidates().getFirst().ticker()
                    ))
                    .orElseGet(() -> fallbackSubject(response));
        }
        return fallbackSubject(response);
    }

    private SubjectPayload subjectFromEntity(ResearchEntityPayload entity) {
        EntityCandidatePayload bestGuess = entity.bestGuess();
        if (bestGuess != null) {
            return new SubjectPayload(
                    textOrFallback(bestGuess.name(), textOrFallback(entity.mention(), "未明确研究对象")),
                    textOrFallback(bestGuess.typeHint(), typeFromResolution(entity.resolutionStatus())),
                    blankToNull(bestGuess.identifier())
            );
        }
        if (entity.candidates() != null && entity.candidates().size() == 1) {
            EntityCandidatePayload candidate = entity.candidates().getFirst();
            return new SubjectPayload(
                    textOrFallback(candidate.name(), textOrFallback(entity.mention(), "未明确研究对象")),
                    textOrFallback(candidate.typeHint(), typeFromResolution(entity.resolutionStatus())),
                    blankToNull(candidate.identifier())
            );
        }
        if (entity.mention() != null && !entity.mention().isBlank()) {
            return new SubjectPayload(entity.mention(), typeFromResolution(entity.resolutionStatus()), null);
        }
        return null;
    }

    private SubjectPayload fallbackSubject(AgentRunResponse response) {
        return new SubjectPayload(
                response.runStatus() != null && response.runStatus().equalsIgnoreCase("NEEDS_CLARIFICATION")
                        ? "未明确研究对象"
                        : "综合研究问题",
                response.runStatus() != null && response.runStatus().equalsIgnoreCase("NEEDS_CLARIFICATION")
                        ? "ambiguous"
                        : "research_topic",
                null
        );
    }

    private String typeFromResolution(String resolutionStatus) {
        if ("AMBIGUOUS".equalsIgnoreCase(resolutionStatus)) {
            return "ambiguous";
        }
        if ("UNRESOLVED".equalsIgnoreCase(resolutionStatus)) {
            return "unresolved";
        }
        return "research_subject";
    }

    private ResearchReportPayload clarificationReport(AgentRunResponse response) {
        String questions = joinOrFallback(response.clarificationQuestions(), "需要用户补充信息。");
        return new ResearchReportPayload(
                "需要补充信息后继续研究",
                "当前问题缺少关键对象或约束，暂时不能生成完整投研结论。请补充信息后继续研究。",
                "当前问题存在需要澄清的研究对象或约束。",
                "用户问题需要先澄清：" + response.query(),
                List.of("需要补充信息：" + questions),
                List.of("澄清后可以继续生成结构化研究计划。"),
                List.of("在关键对象或约束不明确时直接生成投研结论可能误导用户。"),
                "本次未调用工具，因为 agent 判断需要先澄清。",
                "当前不确定性来自用户问题中的歧义或缺失信息。",
                List.of(),
                "本内容仅用于澄清研究问题，不构成投资建议。",
                List.of(
                        new ReportSectionPayload("需要补充的信息", questions, List.of()),
                        new ReportSectionPayload("为什么需要澄清", "在关键对象或约束不明确时直接生成投研结论可能误导用户。", List.of())
                )
        );
    }

    private String sectionsText(List<ReportSectionPayload> sections) {
        if (sections == null || sections.isEmpty()) {
            return "";
        }
        return sections.stream()
                .map(section -> {
                    String title = textOrFallback(section.title(), "");
                    String content = textOrFallback(section.content(), "");
                    if (title.isBlank()) {
                        return content;
                    }
                    if (content.isBlank()) {
                        return title;
                    }
                    return title + "：" + content;
                })
                .filter(value -> !value.isBlank())
                .reduce((left, right) -> left + "\n\n" + right)
                .orElse("");
    }

    private String evidenceSummary(List<EvidencePayload> evidence) {
        if (evidence == null || evidence.isEmpty()) {
            return "本次没有获得可用于支撑结论的 evidence。";
        }
        return evidence.stream()
                .map(EvidencePayload::summary)
                .filter(value -> value != null && !value.isBlank())
                .reduce((left, right) -> left + " " + right)
                .orElse("工具已执行，但没有产出可用 evidence 摘要。");
    }

    private List<Map<String, Object>> normalizedCitations(List<Object> citationValues, List<EvidencePayload> evidence) {
        List<Object> values = listOrEmpty(citationValues);
        if (!values.isEmpty()) {
            return normalizeCitationValues(values);
        }
        return fallbackCitationsFromEvidence(evidence);
    }

    private List<Map<String, Object>> normalizeCitationValues(List<Object> values) {
        List<Map<String, Object>> citations = new java.util.ArrayList<>();
        for (int index = 0; index < values.size(); index++) {
            Object value = values.get(index);
            if (value instanceof Map<?, ?> map) {
                citations.add(normalizeCitationMap(map, index + 1));
            } else {
                citations.add(Map.of(
                        "id", index + 1,
                        "title", String.valueOf(value),
                        "sourceName", "",
                        "url", "",
                        "supports", ""
                ));
            }
        }
        return citations;
    }

    private Map<String, Object> normalizeCitationMap(Map<?, ?> map, int fallbackId) {
        return Map.of(
                "id", intValue(map.get("id"), fallbackId),
                "title", stringValue(map.get("title")),
                "sourceName", stringValue(map.get("sourceName")),
                "url", firstNonBlank(map.get("url"), map.get("sourceUrl")),
                "supports", stringValue(map.get("supports"))
        );
    }

    private List<Map<String, Object>> fallbackCitationsFromEvidence(List<EvidencePayload> evidence) {
        return listOrEmpty(evidence).stream()
                .filter(item -> !stringValue(item.title()).isBlank() || !stringValue(item.sourceUrl()).isBlank())
                .limit(6)
                .map(item -> Map.<String, Object>of(
                        "id", listOrEmpty(evidence).indexOf(item) + 1,
                        "title", stringValue(item.title()),
                        "sourceName", stringValue(item.sourceName()),
                        "url", stringValue(item.sourceUrl()),
                        "supports", stringValue(item.summary())
                ))
                .toList();
    }

    private String legacyCitationsText(List<Map<String, Object>> citations) {
        return citations.stream()
                .map(item -> joinParts(
                        stringValue(item.get("sourceName")),
                        stringValue(item.get("title")),
                        stringValue(item.get("url"))
                ))
                .filter(value -> !value.isBlank())
                .collect(java.util.stream.Collectors.joining("\n"));
    }

    private String joinParts(String... parts) {
        return List.of(parts).stream()
                .filter(value -> value != null && !value.isBlank())
                .collect(java.util.stream.Collectors.joining(" - "));
    }

    private String firstNonBlank(Object first, Object second) {
        String firstValue = stringValue(first);
        if (!firstValue.isBlank()) {
            return firstValue;
        }
        return stringValue(second);
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private String joinOrFallback(List<String> values, String fallback) {
        if (values == null || values.isEmpty()) {
            return fallback;
        }
        return String.join(" ", values);
    }

    private String textOrFallback(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    private <T> List<T> listOrEmpty(List<T> values) {
        return values == null ? List.of() : values;
    }

    private OffsetDateTime parseTimeOrNow(String value) {
        if (value == null || value.isBlank()) {
            return OffsetDateTime.now();
        }
        return OffsetDateTime.parse(value);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Failed to serialize Python agent response", exception);
        }
    }

    private String snippet(String value) {
        String normalized = value.replaceAll("\\s+", " ").trim();
        if (normalized.length() <= 300) {
            return normalized;
        }
        return normalized.substring(0, 300) + "...";
    }

    private String runStatusOrCompleted(String runStatus) {
        if (runStatus == null || runStatus.isBlank()) {
            return "COMPLETED";
        }
        return runStatus;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record AgentRunRequest(
            UUID runId,
            String query,
            String locale,
            List<AgentConversationMessage> conversationMessages,
            AgentUserPreferences userPreferences
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record ConversationSummaryRequest(
            List<AgentConversationMessage> messages,
            Map<String, Object> existingSummary,
            String locale
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record ConversationSummaryResponse(Map<String, Object> summary) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record AgentRunResponse(
            UUID runId,
            String query,
            String runStatus,
            List<String> runtimeWarnings,
            List<String> clarificationQuestions,
            QueryUnderstandingPayload understanding,
            Map<String, Object> planningDecision,
            Map<String, Object> plan,
            List<ToolCallPayload> toolCalls,
            List<EvidencePayload> evidence,
            Map<String, Object> replanningDecision,
            Map<String, Object> dataSufficiency,
            Map<String, Object> evidenceReasoning,
            Map<String, Object> reasoning,
            ResearchReportPayload draftReport,
            Map<String, Object> reflection,
            ResearchReportPayload finalReport
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record QueryUnderstandingPayload(
            List<ResearchEntityPayload> entities,
            List<CompanyMentionPayload> companies
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record ResearchEntityPayload(
            String mention,
            String resolutionStatus,
            EntityCandidatePayload bestGuess,
            List<EntityCandidatePayload> candidates
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record EntityCandidatePayload(String name, String identifier, String typeHint) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record CompanyMentionPayload(String canonicalName, List<CompanyCandidatePayload> candidates) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record CompanyCandidatePayload(String ticker) {
    }

    private record SubjectPayload(String name, String type, String identifier) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record ToolCallPayload(
            String toolName,
            Map<String, Object> input,
            Map<String, Object> output,
            String status,
            long latencyMs
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record EvidencePayload(
            String sourceType,
            String sourceName,
            String sourceUrl,
            String title,
            String summary,
            String rawContent,
            String observedAt,
            double confidence
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record ResearchReportPayload(
            String title,
            String answerSummary,
            String companySummary,
            String questionUnderstanding,
            List<String> keyFindings,
            List<String> opportunities,
            List<String> risks,
            String evidenceSummary,
            String uncertainty,
            List<Object> citations,
            String nonAdvisoryStatement,
            List<ReportSectionPayload> sections
    ) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record ReportSectionPayload(
            String title,
            String content,
            List<Object> citations
    ) {
    }
}
