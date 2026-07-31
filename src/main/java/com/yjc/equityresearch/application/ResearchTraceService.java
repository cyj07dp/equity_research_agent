package com.yjc.equityresearch.application;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.yjc.equityresearch.api.dto.EvidenceGroupResponse;
import com.yjc.equityresearch.api.dto.EvidenceItemResponse;
import com.yjc.equityresearch.api.dto.ResearchReportResponse;
import com.yjc.equityresearch.api.dto.ResearchTraceResponse;
import com.yjc.equityresearch.api.dto.ResearchTraceStageResponse;
import com.yjc.equityresearch.api.dto.ResearchTraceSummaryResponse;
import com.yjc.equityresearch.api.dto.ResearchTraceToolStepResponse;
import com.yjc.equityresearch.domain.EvidenceItem;
import com.yjc.equityresearch.domain.ResearchJob;
import com.yjc.equityresearch.domain.ResearchReport;
import com.yjc.equityresearch.domain.ToolCallRecord;
import com.yjc.equityresearch.domain.ToolCallStatus;
import com.yjc.equityresearch.repository.EvidenceItemRepository;
import com.yjc.equityresearch.repository.ResearchJobRepository;
import com.yjc.equityresearch.repository.ResearchReportRepository;
import com.yjc.equityresearch.repository.ToolCallRecordRepository;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class ResearchTraceService {
    private static final Map<String, String> TOOL_EVIDENCE_TYPES = Map.ofEntries(
            Map.entry("company_search", "COMPANY_PROFILE"),
            Map.entry("market_data", "MARKET_DATA"),
            Map.entry("fundamentals", "FUNDAMENTALS"),
            Map.entry("news_search", "NEWS"),
            Map.entry("filings_search", "SEC_FILINGS"),
            Map.entry("sec_company_facts", "SEC_COMPANY_FACTS"),
            Map.entry("sec_filing_retriever", "SEC_RAG"),
            Map.entry("market_overview", "MARKET_DATA"),
            Map.entry("etf_discovery", "MARKET_DATA"),
            Map.entry("stock_screener", "MARKET_DATA"),
            Map.entry("web_article_reader", "WEB_ARTICLE")
    );

    private final ResearchJobRepository jobRepository;
    private final ResearchReportRepository reportRepository;
    private final EvidenceItemRepository evidenceItemRepository;
    private final ToolCallRecordRepository toolCallRecordRepository;
    private final ObjectMapper objectMapper;

    public ResearchTraceService(
            ResearchJobRepository jobRepository,
            ResearchReportRepository reportRepository,
            EvidenceItemRepository evidenceItemRepository,
            ToolCallRecordRepository toolCallRecordRepository,
            ObjectMapper objectMapper
    ) {
        this.jobRepository = jobRepository;
        this.reportRepository = reportRepository;
        this.evidenceItemRepository = evidenceItemRepository;
        this.toolCallRecordRepository = toolCallRecordRepository;
        this.objectMapper = objectMapper;
    }

    private record ToolEvidenceRequirement(String toolName, String evidenceType) {
    }

    @Transactional(readOnly = true)
    public ResearchTraceResponse getTrace(UUID jobId) {
        ResearchJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Research job not found"));
        ResearchReport report = reportRepository.findByJobId(jobId).orElse(null);
        List<ToolCallRecord> toolCalls = toolCallRecordRepository.findByJobIdOrderByStartedAtAsc(jobId);
        List<EvidenceItem> evidence = evidenceItemRepository.findByJobId(jobId);
        Map<String, Object> rawAgentTrace = report == null ? Map.of() : parseAgentTrace(report);
        List<String> warnings = warningsFor(job, rawAgentTrace, toolCalls, evidence);
        return new ResearchTraceResponse(
                summaryFor(job, report, rawAgentTrace, toolCalls, evidence, warnings),
                report == null ? null : ResearchReportResponse.from(report),
                stagesFor(job, report, rawAgentTrace, toolCalls, evidence, warnings),
                evidenceGroupsFor(evidence),
                rawAgentTrace
        );
    }

    private ResearchTraceSummaryResponse summaryFor(
            ResearchJob job,
            ResearchReport report,
            Map<String, Object> rawAgentTrace,
            List<ToolCallRecord> toolCalls,
            List<EvidenceItem> evidence,
            List<String> warnings
    ) {
        int successCount = (int) toolCalls.stream()
                .filter(call -> call.getStatus() == ToolCallStatus.SUCCEEDED)
                .count();
        int failureCount = toolCalls.size() - successCount;
        return new ResearchTraceSummaryResponse(
                job.getId(),
                job.getQuery(),
                job.getStatus(),
                report == null ? null : report.getSubjectName(),
                report == null ? null : report.getSubjectType(),
                report == null ? null : report.getSubjectIdentifier(),
                successCount,
                failureCount,
                evidence.size(),
                warnings,
                clarificationQuestionsFor(job, rawAgentTrace)
        );
    }

    private List<ResearchTraceStageResponse> stagesFor(
            ResearchJob job,
            ResearchReport report,
            Map<String, Object> rawAgentTrace,
            List<ToolCallRecord> toolCalls,
            List<EvidenceItem> evidence,
            List<String> warnings
    ) {
        List<ResearchTraceStageResponse> stages = new ArrayList<>();
        stages.add(new ResearchTraceStageResponse(
                "query_understanding",
                warnings.stream().anyMatch(warning -> warning.contains("标的解析")) ? "warning" : "success",
                understandingSummary(rawAgentTrace),
                mapOfPresent("understanding", rawAgentTrace.get("understanding")),
                List.of()
        ));
        if (rawAgentTrace.containsKey("planningDecision")) {
            Map<String, Object> planningDecision = objectMap(rawAgentTrace.get("planningDecision"));
            stages.add(new ResearchTraceStageResponse(
                    "planning_decision",
                    Boolean.TRUE.equals(planningDecision.get("needsClarification")) ? "warning" : "success",
                    planningDecisionSummary(planningDecision),
                    mapOfPresent("planningDecision", rawAgentTrace.get("planningDecision")),
                    List.of()
            ));
        }
        if (rawAgentTrace.containsKey("plan")) {
            boolean needsClarification = isNeedsClarification(job, rawAgentTrace);
            stages.add(new ResearchTraceStageResponse(
                    "planning",
                    needsClarification ? "waiting_clarification" : "success",
                    needsClarification ? "Agent 已暂停执行，等待用户澄清。" : "Agent 已生成研究计划。",
                    mapOfPresent("plan", rawAgentTrace.get("plan")),
                    List.of()
            ));
        }
        boolean needsClarification = isNeedsClarification(job, rawAgentTrace);
        stages.add(new ResearchTraceStageResponse(
                "tool_execution",
                needsClarification ? "skipped" : toolCalls.stream().anyMatch(call -> call.getStatus() == ToolCallStatus.FAILED) ? "warning" : "success",
                needsClarification
                        ? "等待用户澄清，未执行工具。"
                        : "执行 " + toolCalls.size() + " 个工具，其中 "
                                + toolCalls.stream().filter(call -> call.getStatus() == ToolCallStatus.SUCCEEDED).count()
                                + " 个成功。",
                Map.of("warningCount", warnings.size()),
                toolCalls.stream().map(this::toolStepFor).toList()
        ));
        stages.add(new ResearchTraceStageResponse(
                "evidence",
                needsClarification ? "skipped" : evidence.isEmpty() ? "warning" : "success",
                needsClarification
                        ? "等待用户澄清，未收集 evidence。"
                        : "收集到 " + evidence.size() + " 条 evidence，分布在 "
                                + evidence.stream().map(EvidenceItem::getSourceType).distinct().count() + " 类来源。",
                Map.of("groups", evidenceGroupsFor(evidence)),
                List.of()
        ));
        if (rawAgentTrace.containsKey("evidenceReasoning") || rawAgentTrace.containsKey("dataSufficiency") || rawAgentTrace.containsKey("reasoning")) {
            Map<String, Object> evidenceReasoning = objectMap(rawAgentTrace.get("evidenceReasoning"));
            Map<String, Object> dataSufficiency = objectMap(
                    evidenceReasoning.isEmpty() ? rawAgentTrace.get("dataSufficiency") : evidenceReasoning.get("dataSufficiency")
            );
            String status = stringValue(dataSufficiency.get("status"));
            stages.add(new ResearchTraceStageResponse(
                    "evidence_reasoning",
                    "SUFFICIENT".equals(status) ? "success" : "warning",
                    evidenceReasoningSummary(evidenceReasoning, dataSufficiency, rawAgentTrace),
                    mapOfPresent(
                            "evidenceReasoning", rawAgentTrace.get("evidenceReasoning"),
                            "dataSufficiency", rawAgentTrace.get("dataSufficiency"),
                            "reasoning", rawAgentTrace.get("reasoning")
                    ),
                    List.of()
            ));
        }
        if (rawAgentTrace.containsKey("replanningDecision")) {
            Map<String, Object> replanningDecision = objectMap(rawAgentTrace.get("replanningDecision"));
            stages.add(new ResearchTraceStageResponse(
                    "replanning",
                    "ASK_CLARIFICATION".equals(stringValue(replanningDecision.get("action"))) ? "warning" : "success",
                    replanningDecisionSummary(replanningDecision),
                    mapOfPresent("replanningDecision", rawAgentTrace.get("replanningDecision")),
                    List.of()
            ));
        }
        if (rawAgentTrace.containsKey("reflection")) {
            stages.add(new ResearchTraceStageResponse(
                    "reflection",
                    reflectionPassed(rawAgentTrace) ? "success" : "warning",
                    reflectionPassed(rawAgentTrace) ? "Reflection 通过。" : "Reflection 发现需要关注的问题。",
                    mapOfPresent("reflection", rawAgentTrace.get("reflection")),
                    List.of()
            ));
        }
        stages.add(new ResearchTraceStageResponse(
                "final_report",
                needsClarification ? "waiting_clarification" : report == null ? "pending" : "success",
                needsClarification ? "等待用户澄清，尚未生成最终投研报告。" : report == null ? "报告尚未生成。" : "报告已生成并保存。",
                report == null ? Map.of("jobStatus", job.getStatus()) : Map.of("reportId", report.getId()),
                List.of()
        ));
        return stages;
    }

    private ResearchTraceToolStepResponse toolStepFor(ToolCallRecord call) {
        Map<String, Object> input = parseJsonObject(call.getInputJson());
        Map<String, Object> output = parseJsonObject(call.getOutputJson());
        String error = call.getStatus() == ToolCallStatus.FAILED ? failureReason(call, output) : null;
        return new ResearchTraceToolStepResponse(
                call.getToolName(),
                call.getStatus(),
                call.getLatencyMs(),
                toolSummary(call, output),
                error,
                input,
                output
        );
    }

    private List<EvidenceGroupResponse> evidenceGroupsFor(List<EvidenceItem> evidence) {
        return evidence.stream()
                .collect(Collectors.groupingBy(EvidenceItem::getSourceType, LinkedHashMap::new, Collectors.toList()))
                .entrySet()
                .stream()
                .map(entry -> new EvidenceGroupResponse(
                        entry.getKey(),
                        entry.getValue().size(),
                        entry.getValue().stream()
                                .sorted(Comparator.comparing(EvidenceItem::getObservedAt))
                                .map(EvidenceItemResponse::from)
                                .toList()
                ))
                .toList();
    }

    private List<String> warningsFor(
            ResearchJob job,
            Map<String, Object> rawAgentTrace,
            List<ToolCallRecord> toolCalls,
            List<EvidenceItem> evidence
    ) {
        List<String> warnings = new ArrayList<>();
        if (job.getErrorMessage() != null && !job.getErrorMessage().isBlank()) {
            warnings.add("任务失败：" + job.getErrorMessage());
        }
        stringList(rawAgentTrace.get("runtimeWarnings")).stream()
                .map(warning -> "运行降级：" + warning)
                .forEach(warnings::add);
        toolCalls.stream()
                .filter(call -> call.getStatus() == ToolCallStatus.FAILED)
                .forEach(call -> warnings.add("工具失败：" + call.getToolName() + " - "
                        + failureReason(call, parseJsonObject(call.getOutputJson()))));
        evidence.stream()
                .filter(item -> "COMPANY_PROFILE".equals(item.getSourceType()) && item.getConfidence().doubleValue() < 0.9)
                .forEach(item -> warnings.add("标的解析置信度偏低：" + item.getSummary()));
        evidence.stream()
                .filter(item -> "SEC_FILINGS".equals(item.getSourceType()) && item.getSummary().contains("2014"))
                .forEach(item -> warnings.add("SEC filings 证据较旧，可能不适合当前投资判断：" + item.getSummary()));
        if (!isNeedsClarification(job, rawAgentTrace)) {
            addMissingPlannedEvidenceWarnings(warnings, plannedEvidenceRequirements(rawAgentTrace, toolCalls), evidence);
        }
        return warnings;
    }

    private void addMissingPlannedEvidenceWarnings(
            List<String> warnings,
            List<ToolEvidenceRequirement> requirements,
            List<EvidenceItem> evidence
    ) {
        Set<String> sourceTypes = evidence.stream()
                .map(EvidenceItem::getSourceType)
                .filter(value -> value != null && !value.isBlank())
                .collect(Collectors.toSet());
        requirements.stream()
                .filter(requirement -> !sourceTypes.contains(requirement.evidenceType()))
                .forEach(requirement -> warnings.add("计划调用 " + requirement.toolName()
                        + "，但未获得 " + requirement.evidenceType() + " evidence。"));
    }

    private List<ToolEvidenceRequirement> plannedEvidenceRequirements(
            Map<String, Object> rawAgentTrace,
            List<ToolCallRecord> toolCalls
    ) {
        Set<ToolEvidenceRequirement> requirements = new LinkedHashSet<>();
        Map<String, Object> plan = objectMap(rawAgentTrace.get("plan"));
        listOfMaps(plan.get("steps")).forEach(step -> {
            String toolName = toolNameFromStep(step);
            if (toolName.isBlank()) {
                return;
            }
            List<String> evidenceTypes = expectedEvidenceTypesFromStep(step);
            if (evidenceTypes.isEmpty()) {
                evidenceTypes = fallbackEvidenceTypes(toolName);
            }
            evidenceTypes.forEach(evidenceType -> requirements.add(new ToolEvidenceRequirement(toolName, evidenceType)));
        });
        if (!requirements.isEmpty()) {
            return List.copyOf(requirements);
        }
        plannedToolNames(rawAgentTrace, toolCalls).stream()
                .flatMap(toolName -> fallbackEvidenceTypes(toolName).stream()
                        .map(evidenceType -> new ToolEvidenceRequirement(toolName, evidenceType)))
                .forEach(requirements::add);
        return List.copyOf(requirements);
    }

    private List<String> expectedEvidenceTypesFromStep(Map<String, Object> step) {
        List<String> values = new ArrayList<>();
        String outputEvidenceType = stringValue(step.get("outputEvidenceType"));
        if (!outputEvidenceType.isBlank()) {
            values.add(outputEvidenceType);
        }
        stringList(step.get("expectedEvidenceTypes")).forEach(values::add);
        return values.stream()
                .filter(value -> !value.isBlank())
                .distinct()
                .toList();
    }

    private List<String> fallbackEvidenceTypes(String toolName) {
        String evidenceType = TOOL_EVIDENCE_TYPES.get(toolName);
        if (evidenceType == null || evidenceType.isBlank()) {
            return List.of();
        }
        return List.of(evidenceType);
    }

    private List<String> plannedToolNames(Map<String, Object> rawAgentTrace, List<ToolCallRecord> toolCalls) {
        Set<String> planned = new LinkedHashSet<>();
        Map<String, Object> plan = objectMap(rawAgentTrace.get("plan"));
        listOfMaps(plan.get("steps")).stream()
                .map(this::toolNameFromStep)
                .filter(value -> !value.isBlank())
                .forEach(planned::add);
        if (!planned.isEmpty()) {
            return List.copyOf(planned);
        }
        toolCalls.stream()
                .map(ToolCallRecord::getToolName)
                .filter(value -> value != null && !value.isBlank())
                .forEach(planned::add);
        return List.copyOf(planned);
    }

    private String toolNameFromStep(Map<String, Object> step) {
        String directToolName = stringValue(step.get("toolName"));
        if (!directToolName.isBlank()) {
            return directToolName;
        }
        String snakeCaseToolName = stringValue(step.get("tool_name"));
        if (!snakeCaseToolName.isBlank()) {
            return snakeCaseToolName;
        }
        Object tool = step.get("tool");
        if (tool instanceof String toolName) {
            return toolName;
        }
        return stringValue(objectMap(tool).get("name"));
    }

    private Map<String, Object> parseAgentTrace(ResearchReport report) {
        try {
            return objectMapper.readValue(report.getRawJson(), new TypeReference<>() {
            });
        } catch (Exception exception) {
            return Map.of("rawJsonParseError", exception.getMessage());
        }
    }

    private Map<String, Object> parseJsonObject(String value) {
        if (value == null || value.isBlank()) {
            return Map.of();
        }
        try {
            return objectMapper.readValue(value, new TypeReference<>() {
            });
        } catch (Exception exception) {
            return Map.of("rawJson", value, "parseError", exception.getMessage());
        }
    }

    private String failureReason(ToolCallRecord call, Map<String, Object> output) {
        if (call.getErrorMessage() != null && !call.getErrorMessage().isBlank()) {
            return call.getErrorMessage();
        }
        Object error = output.get("error");
        if (error != null) {
            return String.valueOf(error);
        }
        Object information = output.get("Information");
        if (information != null) {
            return String.valueOf(information);
        }
        if (output.isEmpty()) {
            return "工具返回空输出。";
        }
        return "工具执行失败。";
    }

    private String toolSummary(ToolCallRecord call, Map<String, Object> output) {
        if (call.getStatus() == ToolCallStatus.FAILED) {
            return "失败：" + failureReason(call, output);
        }
        Object summary = output.get("summary");
        if (summary != null) {
            return String.valueOf(summary);
        }
        String structuredSummary = structuredToolSummary(call.getToolName(), output);
        if (!structuredSummary.isBlank()) {
            return structuredSummary;
        }
        Object ticker = output.get("ticker");
        if (ticker != null && output.get("price") != null) {
            return ticker + " price=" + output.get("price") + ", change=" + output.get("changePercent");
        }
        if (ticker != null) {
            return call.getToolName() + " succeeded for " + ticker;
        }
        return call.getToolName() + " succeeded.";
    }

    private String structuredToolSummary(String toolName, Map<String, Object> output) {
        if ("market_overview".equals(toolName)) {
            List<String> symbols = listOfMaps(output.get("indexProxies")).stream()
                    .map(item -> stringValue(item.get("symbol")))
                    .filter(value -> !value.isBlank())
                    .toList();
            List<String> dimensions = stringList(output.get("explorationDimensions"));
            return joinParts(
                    symbols.isEmpty() ? "" : "指数代理：" + String.join(", ", symbols),
                    dimensions.isEmpty() ? "" : "观察维度：" + String.join("、", dimensions)
            );
        }
        if ("etf_discovery".equals(toolName)) {
            List<String> categories = listOfMaps(output.get("categories")).stream()
                    .map(item -> stringValue(item.get("category")))
                    .filter(value -> !value.isBlank())
                    .toList();
            return categories.isEmpty() ? "" : "ETF 研究类别：" + String.join("、", categories);
        }
        if ("stock_screener".equals(toolName)) {
            List<String> symbols = listOfMaps(output.get("candidates")).stream()
                    .map(item -> stringValue(item.get("symbol")))
                    .filter(value -> !value.isBlank())
                    .toList();
            List<String> criteria = stringList(output.get("screeningCriteria"));
            return joinParts(
                    symbols.isEmpty() ? "" : "学习型股票池：" + String.join(", ", symbols),
                    criteria.isEmpty() ? "" : "筛选标准：" + String.join("、", criteria)
            );
        }
        return "";
    }

    private String planningDecisionSummary(Map<String, Object> planningDecision) {
        String answerability = stringValue(planningDecision.get("answerability"));
        boolean needsTools = Boolean.TRUE.equals(planningDecision.get("needsTools"));
        boolean needsClarification = Boolean.TRUE.equals(planningDecision.get("needsClarification"));
        List<String> allowedTools = stringList(planningDecision.get("allowedTools"));
        List<String> evidenceNeeds = stringList(planningDecision.get("evidenceNeeds"));
        return joinParts(
                answerability.isBlank() ? "" : "answerability=" + answerability,
                "needsTools=" + needsTools,
                "needsClarification=" + needsClarification,
                allowedTools.isEmpty() ? "" : "allowedTools=" + String.join(", ", allowedTools),
                evidenceNeeds.isEmpty() ? "" : "evidenceNeeds=" + String.join(", ", evidenceNeeds)
        );
    }

    private String replanningDecisionSummary(Map<String, Object> replanningDecision) {
        String action = stringValue(replanningDecision.get("action"));
        String rationale = stringValue(replanningDecision.get("rationale"));
        String capabilityGap = stringValue(replanningDecision.get("capabilityGap"));
        return joinParts(
                action.isBlank() ? "" : "action=" + action,
                rationale,
                capabilityGap.isBlank() ? "" : "capabilityGap=" + capabilityGap
        );
    }

    private String evidenceReasoningSummary(
            Map<String, Object> evidenceReasoning,
            Map<String, Object> dataSufficiency,
            Map<String, Object> rawAgentTrace
    ) {
        Map<String, Object> evidenceAssessment = objectMap(evidenceReasoning.get("evidenceAssessment"));
        Map<String, Object> reasoning = objectMap(
                evidenceReasoning.isEmpty() ? rawAgentTrace.get("reasoning") : evidenceReasoning.get("reasoning")
        );
        return joinParts(
                stringValue(dataSufficiency.get("summary")),
                stringValue(evidenceAssessment.get("summary")),
                stringValue(reasoning.get("thesis"))
        );
    }

    private List<String> clarificationQuestionsFor(ResearchJob job, Map<String, Object> rawAgentTrace) {
        if (!job.getClarificationQuestions().isEmpty()) {
            return job.getClarificationQuestions();
        }
        List<String> topLevelQuestions = stringList(rawAgentTrace.get("clarificationQuestions"));
        if (!topLevelQuestions.isEmpty()) {
            return topLevelQuestions;
        }
        Map<String, Object> planningDecision = objectMap(rawAgentTrace.get("planningDecision"));
        return stringList(planningDecision.get("clarificationQuestions"));
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> objectMap(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> listOfMaps(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream()
                .filter(Map.class::isInstance)
                .map(item -> (Map<String, Object>) item)
                .toList();
    }

    private List<String> stringList(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream()
                .map(this::stringValue)
                .filter(item -> !item.isBlank())
                .toList();
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String joinParts(String... values) {
        return List.of(values).stream()
                .filter(value -> value != null && !value.isBlank())
                .collect(Collectors.joining("；"));
    }

    private String understandingSummary(Map<String, Object> rawAgentTrace) {
        Object understanding = rawAgentTrace.get("understanding");
        if (understanding == null) {
            return "暂无 query understanding。";
        }
        return "Agent 已完成用户问题理解。";
    }

    private boolean reflectionPassed(Map<String, Object> rawAgentTrace) {
        Object reflection = rawAgentTrace.get("reflection");
        if (!(reflection instanceof Map<?, ?> reflectionMap)) {
            return true;
        }
        Object passed = reflectionMap.get("passed");
        return !(passed instanceof Boolean value) || value;
    }

    private boolean isNeedsClarification(ResearchJob job, Map<String, Object> rawAgentTrace) {
        if ("NEEDS_CLARIFICATION".equals(String.valueOf(job.getStatus()))) {
            return true;
        }
        if ("NEEDS_CLARIFICATION".equalsIgnoreCase(stringValue(rawAgentTrace.get("runStatus")))) {
            return true;
        }
        Map<String, Object> planningDecision = objectMap(rawAgentTrace.get("planningDecision"));
        return Boolean.TRUE.equals(planningDecision.get("needsClarification"))
                && !Boolean.TRUE.equals(planningDecision.get("needsTools"));
    }

    private Map<String, Object> mapOfPresent(String key, Object value) {
        if (value == null) {
            return Map.of();
        }
        return Map.of(key, value);
    }

    private Map<String, Object> mapOfPresent(String key1, Object value1, String key2, Object value2, String key3, Object value3) {
        Map<String, Object> values = new LinkedHashMap<>();
        if (value1 != null) {
            values.put(key1, value1);
        }
        if (value2 != null) {
            values.put(key2, value2);
        }
        if (value3 != null) {
            values.put(key3, value3);
        }
        return values;
    }
}
