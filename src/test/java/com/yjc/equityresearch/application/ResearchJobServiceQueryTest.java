package com.yjc.equityresearch.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import com.yjc.equityresearch.agent.python.AgentConversationMessage;
import com.yjc.equityresearch.agent.python.AgentUserPreferences;
import com.yjc.equityresearch.agent.ResearchAgentOrchestrator;
import com.yjc.equityresearch.agent.ResearchWorkflowResult;
import com.yjc.equityresearch.api.dto.ResearchJobResponse;
import com.yjc.equityresearch.config.IdGenerator;
import com.yjc.equityresearch.domain.ResearchJob;
import com.yjc.equityresearch.domain.ResearchJobStatus;
import com.yjc.equityresearch.domain.ResearchMessage;
import com.yjc.equityresearch.domain.ResearchMessageRole;
import com.yjc.equityresearch.domain.ResearchMessageType;
import com.yjc.equityresearch.repository.EvidenceItemRepository;
import com.yjc.equityresearch.repository.ResearchConversationRepository;
import com.yjc.equityresearch.repository.ResearchJobRepository;
import com.yjc.equityresearch.repository.ResearchMessageRepository;
import com.yjc.equityresearch.repository.ResearchReportRepository;
import com.yjc.equityresearch.repository.ToolCallRecordRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.Executor;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentMatchers;

class ResearchJobServiceQueryTest {
    @Test
    void createJobPersistsNaturalLanguageQuery() {
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchReportRepository reportRepository = org.mockito.Mockito.mock(ResearchReportRepository.class);
        EvidenceItemRepository evidenceItemRepository = org.mockito.Mockito.mock(EvidenceItemRepository.class);
        ToolCallRecordRepository toolCallRecordRepository = org.mockito.Mockito.mock(ToolCallRecordRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        ResearchAgentOrchestrator orchestrator = org.mockito.Mockito.mock(ResearchAgentOrchestrator.class);
        UserPreferenceService userPreferenceService = org.mockito.Mockito.mock(UserPreferenceService.class);
        Executor noOpExecutor = runnable -> {
        };
        ResearchJobService service = new ResearchJobService(
                jobRepository,
                reportRepository,
                evidenceItemRepository,
                toolCallRecordRepository,
                messageRepository,
                conversationRepository,
                orchestrator,
                noOpExecutor,
                new IdGenerator(),
                userPreferenceService,
                new ConversationSummaryService(org.mockito.Mockito.mock(com.yjc.equityresearch.agent.python.AgentServiceClient.class))
        );
        when(jobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ResearchJob job = service.createJob("帮我生成一份英伟达中文投研报告");

        assertThat(job.getQuery()).isEqualTo("帮我生成一份英伟达中文投研报告");
    }

    @Test
    void processJobPassesStoredQueryToOrchestrator() {
        UUID jobId = UUID.randomUUID();
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchReportRepository reportRepository = org.mockito.Mockito.mock(ResearchReportRepository.class);
        EvidenceItemRepository evidenceItemRepository = org.mockito.Mockito.mock(EvidenceItemRepository.class);
        ToolCallRecordRepository toolCallRecordRepository = org.mockito.Mockito.mock(ToolCallRecordRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        ResearchAgentOrchestrator orchestrator = org.mockito.Mockito.mock(ResearchAgentOrchestrator.class);
        com.yjc.equityresearch.domain.ResearchReport report = new com.yjc.equityresearch.domain.ResearchReport(
                UUID.randomUUID(),
                jobId,
                "NVIDIA Corporation",
                "company",
                "NVDA",
                "英伟达投研报告",
                "概览",
                "用户希望分析英伟达。",
                "摘要",
                "机会",
                "风险",
                "证据摘要",
                "不确定性",
                "",
                "[]",
                "不构成投资建议。",
                "{}",
                OffsetDateTime.now()
        );
        ResearchWorkflowResult workflowResult = new ResearchWorkflowResult(report, List.of(), List.of());
        UserPreferenceService userPreferenceService = org.mockito.Mockito.mock(UserPreferenceService.class);
        ResearchJobService service = new ResearchJobService(
                jobRepository,
                reportRepository,
                evidenceItemRepository,
                toolCallRecordRepository,
                messageRepository,
                conversationRepository,
                orchestrator,
                Runnable::run,
                new IdGenerator(),
                userPreferenceService,
                new ConversationSummaryService(org.mockito.Mockito.mock(com.yjc.equityresearch.agent.python.AgentServiceClient.class))
        );
        ResearchJob job = new ResearchJob(jobId, "帮我分析一下英伟达", ResearchJobStatus.PENDING, OffsetDateTime.now());
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(jobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(userPreferenceService.getDefaultUserPreferences()).thenReturn(AgentUserPreferences.empty());
        when(orchestrator.run(jobId, "帮我分析一下英伟达", List.of(), AgentUserPreferences.empty())).thenReturn(workflowResult);

        ResearchWorkflowResult result = service.processJob(jobId);

        assertThat(result).isSameAs(workflowResult);
    }

    @Test
    void processJobPassesUserPreferencesToOrchestrator() {
        UUID jobId = UUID.randomUUID();
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchReportRepository reportRepository = org.mockito.Mockito.mock(ResearchReportRepository.class);
        EvidenceItemRepository evidenceItemRepository = org.mockito.Mockito.mock(EvidenceItemRepository.class);
        ToolCallRecordRepository toolCallRecordRepository = org.mockito.Mockito.mock(ToolCallRecordRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        ResearchAgentOrchestrator orchestrator = org.mockito.Mockito.mock(ResearchAgentOrchestrator.class);
        com.yjc.equityresearch.domain.ResearchReport report = new com.yjc.equityresearch.domain.ResearchReport(
                UUID.randomUUID(),
                jobId,
                "Apple Inc.",
                "company",
                "AAPL",
                "苹果投研报告",
                "概览",
                "用户希望分析苹果。",
                "摘要",
                "机会",
                "风险",
                "证据摘要",
                "不确定性",
                "",
                "[]",
                "不构成投资建议。",
                "{}",
                OffsetDateTime.now()
        );
        ResearchWorkflowResult workflowResult = new ResearchWorkflowResult(report, List.of(), List.of());
        AgentUserPreferences preferences = new AgentUserPreferences(
                "zh-CN",
                "US",
                "LOW",
                "LONG_TERM",
                "CONCISE",
                List.of("AI"),
                List.of("Crypto"),
                List.of("ETF"),
                "更关注回撤控制",
                true
        );
        UserPreferenceService userPreferenceService = org.mockito.Mockito.mock(UserPreferenceService.class);
        ResearchJobService service = new ResearchJobService(
                jobRepository,
                reportRepository,
                evidenceItemRepository,
                toolCallRecordRepository,
                messageRepository,
                conversationRepository,
                orchestrator,
                Runnable::run,
                new IdGenerator(),
                userPreferenceService,
                new ConversationSummaryService(org.mockito.Mockito.mock(com.yjc.equityresearch.agent.python.AgentServiceClient.class))
        );
        ResearchJob job = new ResearchJob(jobId, "苹果最近怎么样", ResearchJobStatus.PENDING, OffsetDateTime.now());
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(jobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(userPreferenceService.getDefaultUserPreferences()).thenReturn(preferences);
        when(orchestrator.run(jobId, "苹果最近怎么样", List.of(), preferences)).thenReturn(workflowResult);

        ResearchWorkflowResult result = service.processJob(jobId);

        assertThat(result).isSameAs(workflowResult);
    }

    @Test
    void processJobPassesConversationMessagesToOrchestrator() {
        UUID jobId = UUID.randomUUID();
        UUID conversationId = UUID.randomUUID();
        UUID triggerMessageId = UUID.randomUUID();
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchReportRepository reportRepository = org.mockito.Mockito.mock(ResearchReportRepository.class);
        EvidenceItemRepository evidenceItemRepository = org.mockito.Mockito.mock(EvidenceItemRepository.class);
        ToolCallRecordRepository toolCallRecordRepository = org.mockito.Mockito.mock(ToolCallRecordRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        ResearchAgentOrchestrator orchestrator = org.mockito.Mockito.mock(ResearchAgentOrchestrator.class);
        com.yjc.equityresearch.domain.ResearchReport report = new com.yjc.equityresearch.domain.ResearchReport(
                UUID.randomUUID(),
                jobId,
                "Apple Inc.",
                "company",
                "AAPL",
                "苹果投研报告",
                "概览",
                "用户澄清指的是 Apple Inc.",
                "摘要",
                "机会",
                "风险",
                "证据摘要",
                "不确定性",
                "",
                "[]",
                "不构成投资建议。",
                "{}",
                OffsetDateTime.now()
        );
        ResearchWorkflowResult workflowResult = new ResearchWorkflowResult(report, List.of(), List.of());
        UserPreferenceService userPreferenceService = org.mockito.Mockito.mock(UserPreferenceService.class);
        ResearchJobService service = new ResearchJobService(
                jobRepository,
                reportRepository,
                evidenceItemRepository,
                toolCallRecordRepository,
                messageRepository,
                conversationRepository,
                orchestrator,
                Runnable::run,
                new IdGenerator(),
                userPreferenceService,
                new ConversationSummaryService(org.mockito.Mockito.mock(com.yjc.equityresearch.agent.python.AgentServiceClient.class))
        );
        ResearchJob job = new ResearchJob(
                jobId,
                "我指的是 Apple Inc.",
                ResearchJobStatus.PENDING,
                OffsetDateTime.now(),
                conversationId,
                triggerMessageId
        );
        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(jobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(userPreferenceService.getDefaultUserPreferences()).thenReturn(AgentUserPreferences.empty());
        when(messageRepository.findByConversationIdOrderByCreatedAtAsc(conversationId)).thenReturn(List.of(
                new ResearchMessage(UUID.randomUUID(), conversationId, ResearchMessageRole.USER, ResearchMessageType.QUERY, "现在要不要买苹果", null, OffsetDateTime.now()),
                new ResearchMessage(UUID.randomUUID(), conversationId, ResearchMessageRole.ASSISTANT, ResearchMessageType.CLARIFICATION_QUESTION, "你指的是 Apple Inc. 吗？", null, OffsetDateTime.now()),
                new ResearchMessage(triggerMessageId, conversationId, ResearchMessageRole.USER, ResearchMessageType.CLARIFICATION_ANSWER, "我指的是 Apple Inc.", jobId, OffsetDateTime.now())
        ));
        when(orchestrator.run(
                eq(jobId),
                eq("我指的是 Apple Inc."),
                argThat(messages -> messages.stream().map(AgentConversationMessage::content).toList().contains("现在要不要买苹果")),
                eq(AgentUserPreferences.empty())
        )).thenReturn(workflowResult);

        ResearchWorkflowResult result = service.processJob(jobId);

        assertThat(result).isSameAs(workflowResult);
    }

    @Test
    void researchJobResponseIncludesClarificationQuestions() {
        ResearchJob job = new ResearchJob(UUID.randomUUID(), "现在要不要买？", ResearchJobStatus.PENDING, OffsetDateTime.now());
        job.markNeedsClarification(List.of("你想研究哪家公司或股票代码？"), UUID.randomUUID(), OffsetDateTime.now());

        ResearchJobResponse response = ResearchJobResponse.from(job);

        assertThat(response.clarificationQuestions()).containsExactly("你想研究哪家公司或股票代码？");
    }
}
