package com.yjc.equityresearch.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.yjc.equityresearch.agent.ResearchAgentOrchestrator;
import com.yjc.equityresearch.agent.ResearchWorkflowResult;
import com.yjc.equityresearch.agent.python.AgentUserPreferences;
import com.yjc.equityresearch.config.IdGenerator;
import com.yjc.equityresearch.domain.ResearchReport;
import com.yjc.equityresearch.domain.ResearchJob;
import com.yjc.equityresearch.domain.ResearchJobStatus;
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
import org.mockito.ArgumentCaptor;

class ResearchJobServiceTest {
    @Test
    void processJobPersistsReportEvidenceToolCallsAndMarksJobSucceeded() {
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchReportRepository reportRepository = org.mockito.Mockito.mock(ResearchReportRepository.class);
        EvidenceItemRepository evidenceItemRepository = org.mockito.Mockito.mock(EvidenceItemRepository.class);
        ToolCallRecordRepository toolCallRecordRepository = org.mockito.Mockito.mock(ToolCallRecordRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        Executor directExecutor = Runnable::run;
        ResearchAgentOrchestrator orchestrator = org.mockito.Mockito.mock(ResearchAgentOrchestrator.class);
        UserPreferenceService userPreferenceService = org.mockito.Mockito.mock(UserPreferenceService.class);
        ResearchJobService service = new ResearchJobService(
                jobRepository,
                reportRepository,
                evidenceItemRepository,
                toolCallRecordRepository,
                messageRepository,
                conversationRepository,
                orchestrator,
                directExecutor,
                new IdGenerator(),
                userPreferenceService,
                new ConversationSummaryService(org.mockito.Mockito.mock(com.yjc.equityresearch.agent.python.AgentServiceClient.class))
        );
        UUID jobId = UUID.randomUUID();
        ResearchJob pendingJob = new ResearchJob(jobId, "NVDA", ResearchJobStatus.PENDING, OffsetDateTime.now());
        ResearchReport report = new ResearchReport(
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

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(pendingJob));
        when(userPreferenceService.getDefaultUserPreferences()).thenReturn(AgentUserPreferences.empty());
        when(orchestrator.run(jobId, "NVDA", List.of(), AgentUserPreferences.empty())).thenReturn(workflowResult);
        when(reportRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(jobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ResearchWorkflowResult result = service.processJob(jobId);

        ArgumentCaptor<ResearchJob> jobCaptor = ArgumentCaptor.forClass(ResearchJob.class);
        verify(reportRepository).save(result.report());
        verify(evidenceItemRepository).saveAll(result.evidenceItems());
        verify(toolCallRecordRepository).saveAll(result.toolCallRecords());
        verify(jobRepository, atLeastOnce()).save(jobCaptor.capture());
        assertThat(jobCaptor.getValue().getStatus()).isEqualTo(ResearchJobStatus.SUCCEEDED);
        assertThat(jobCaptor.getValue().getReportId()).isEqualTo(result.report().getId());
    }

    @Test
    void processJobMarksJobNeedsClarificationAndExposesQuestions() {
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchReportRepository reportRepository = org.mockito.Mockito.mock(ResearchReportRepository.class);
        EvidenceItemRepository evidenceItemRepository = org.mockito.Mockito.mock(EvidenceItemRepository.class);
        ToolCallRecordRepository toolCallRecordRepository = org.mockito.Mockito.mock(ToolCallRecordRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        ResearchAgentOrchestrator orchestrator = org.mockito.Mockito.mock(ResearchAgentOrchestrator.class);
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
        UUID jobId = UUID.randomUUID();
        ResearchJob pendingJob = new ResearchJob(jobId, "现在要不要买？", ResearchJobStatus.PENDING, OffsetDateTime.now());
        ResearchReport report = new ResearchReport(
                UUID.randomUUID(),
                jobId,
                "未明确研究对象",
                "ambiguous",
                null,
                "需要补充研究对象。",
                "本次 query 未识别到明确上市公司或 ticker。",
                "用户问题缺少具体研究对象。",
                "补充信息后可继续研究。",
                "缺少具体标的。",
                "缺少具体标的。",
                "缺少具体标的。",
                "",
                "",
                "[]",
                "本报告不构成投资建议。",
                "{}",
                OffsetDateTime.now()
        );
        ResearchWorkflowResult workflowResult = new ResearchWorkflowResult(
                report,
                List.of(),
                List.of(),
                "NEEDS_CLARIFICATION",
                List.of("你想研究哪家公司或股票代码？")
        );

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(pendingJob));
        when(userPreferenceService.getDefaultUserPreferences()).thenReturn(AgentUserPreferences.empty());
        when(orchestrator.run(jobId, "现在要不要买？", List.of(), AgentUserPreferences.empty())).thenReturn(workflowResult);
        when(reportRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(jobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        service.processJob(jobId);

        ArgumentCaptor<ResearchJob> jobCaptor = ArgumentCaptor.forClass(ResearchJob.class);
        verify(jobRepository, atLeastOnce()).save(jobCaptor.capture());
        assertThat(jobCaptor.getValue().getStatus()).isEqualTo(ResearchJobStatus.NEEDS_CLARIFICATION);
        assertThat(jobCaptor.getValue().getClarificationQuestions()).containsExactly("你想研究哪家公司或股票代码？");
    }
}
