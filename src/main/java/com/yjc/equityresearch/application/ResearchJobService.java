package com.yjc.equityresearch.application;

import com.yjc.equityresearch.agent.ResearchAgentOrchestrator;
import com.yjc.equityresearch.agent.ResearchWorkflowResult;
import com.yjc.equityresearch.agent.python.AgentConversationMessage;
import com.yjc.equityresearch.agent.python.AgentUserPreferences;
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
import java.util.UUID;
import java.util.concurrent.Executor;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class ResearchJobService {
    private static final Logger log = LoggerFactory.getLogger(ResearchJobService.class);

    private final ResearchJobRepository jobRepository;
    private final ResearchReportRepository reportRepository;
    private final EvidenceItemRepository evidenceItemRepository;
    private final ToolCallRecordRepository toolCallRecordRepository;
    private final ResearchMessageRepository messageRepository;
    private final ResearchConversationRepository conversationRepository;
    private final ResearchAgentOrchestrator orchestrator;
    private final Executor researchTaskExecutor;
    private final IdGenerator idGenerator;
    private final UserPreferenceService userPreferenceService;
    private final ConversationSummaryService conversationSummaryService;

    public ResearchJobService(
            ResearchJobRepository jobRepository,
            ResearchReportRepository reportRepository,
            EvidenceItemRepository evidenceItemRepository,
            ToolCallRecordRepository toolCallRecordRepository,
            ResearchMessageRepository messageRepository,
            ResearchConversationRepository conversationRepository,
            ResearchAgentOrchestrator orchestrator,
            @Qualifier("researchTaskExecutor") Executor researchTaskExecutor,
            IdGenerator idGenerator,
            UserPreferenceService userPreferenceService,
            ConversationSummaryService conversationSummaryService
    ) {
        this.jobRepository = jobRepository;
        this.reportRepository = reportRepository;
        this.evidenceItemRepository = evidenceItemRepository;
        this.toolCallRecordRepository = toolCallRecordRepository;
        this.messageRepository = messageRepository;
        this.conversationRepository = conversationRepository;
        this.orchestrator = orchestrator;
        this.researchTaskExecutor = researchTaskExecutor;
        this.idGenerator = idGenerator;
        this.userPreferenceService = userPreferenceService;
        this.conversationSummaryService = conversationSummaryService;
    }

    public ResearchJob createJob(String query) {
        String normalizedQuery = normalizeQuery(query);
        ResearchJob job = new ResearchJob(
                idGenerator.newId(),
                normalizedQuery,
                ResearchJobStatus.PENDING,
                OffsetDateTime.now()
        );
        ResearchJob savedJob = jobRepository.save(job);
        log.info("Created research job jobId={} queryLength={}", savedJob.getId(), normalizedQuery.length());
        researchTaskExecutor.execute(() -> processJob(savedJob.getId()));
        return savedJob;
    }

    @Transactional(readOnly = true)
    public ResearchJob getJob(UUID jobId) {
        return jobRepository.findById(jobId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Research job not found"));
    }

    @Transactional(readOnly = true)
    public List<com.yjc.equityresearch.domain.ToolCallRecord> getToolCalls(UUID jobId) {
        if (!jobRepository.existsById(jobId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Research job not found");
        }
        return toolCallRecordRepository.findByJobIdOrderByStartedAtAsc(jobId);
    }

    @Transactional
    public ResearchWorkflowResult processJob(UUID jobId) {
        ResearchJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Research job not found"));
        job.markRunning(OffsetDateTime.now());
        jobRepository.save(job);
        log.info(
                "Started research job jobId={} conversationId={} triggerMessageId={} queryLength={}",
                job.getId(),
                job.getConversationId(),
                job.getTriggerMessageId(),
                job.getQuery().length()
        );

        try {
            List<AgentConversationMessage> conversationMessages = conversationMessagesFor(job);
            AgentUserPreferences userPreferences = userPreferenceService.getDefaultUserPreferences();
            ResearchWorkflowResult result = orchestrator.run(
                    job.getId(),
                    job.getQuery(),
                    conversationMessages,
                    userPreferences
            );
            reportRepository.save(result.report());
            evidenceItemRepository.saveAll(result.evidenceItems());
            toolCallRecordRepository.saveAll(result.toolCallRecords());
            if ("NEEDS_CLARIFICATION".equalsIgnoreCase(result.runStatus())) {
                job.markNeedsClarification(result.clarificationQuestions(), result.report().getId(), OffsetDateTime.now());
                updateConversationWaitingForUser(job, result);
            } else {
                job.markSucceeded(result.report().getId(), OffsetDateTime.now());
                updateConversationActive(job, result);
            }
            jobRepository.save(job);
            log.info(
                    "Completed research job jobId={} conversationId={} reportId={} status={}",
                    job.getId(),
                    job.getConversationId(),
                    result.report().getId(),
                    job.getStatus()
            );
            return result;
        } catch (RuntimeException exception) {
            job.markFailed(exception.getMessage(), OffsetDateTime.now());
            updateConversationFailed(job, exception.getMessage());
            jobRepository.save(job);
            log.error(
                    "Failed research job jobId={} conversationId={} error={}",
                    job.getId(),
                    job.getConversationId(),
                    exception.getMessage(),
                    exception
            );
            throw exception;
        }
    }

    private String normalizeQuery(String query) {
        if (query == null || query.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Query is required");
        }
        String normalizedQuery = query.trim();
        if (normalizedQuery.length() > 1000) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Query is too long");
        }
        return normalizedQuery;
    }

    private List<AgentConversationMessage> conversationMessagesFor(ResearchJob job) {
        if (job.getConversationId() == null) {
            return List.of();
        }
        List<ResearchMessage> messages = messageRepository.findByConversationIdOrderByCreatedAtAsc(job.getConversationId());
        String summary = conversationRepository.findById(job.getConversationId())
                .map(conversation -> {
                    if (!conversationSummaryService.shouldSummarize(messages)) {
                        return conversation.getConversationSummary();
                    }
                    String updatedSummary = conversationSummaryService.summarize(messages, conversation.getConversationSummary());
                    conversation.updateConversationSummary(updatedSummary, OffsetDateTime.now());
                    conversationRepository.save(conversation);
                    return updatedSummary;
                })
                .orElse("");
        return conversationSummaryService.compressedMessages(messages, summary);
    }

    private void updateConversationWaitingForUser(ResearchJob job, ResearchWorkflowResult result) {
        if (job.getConversationId() == null) {
            return;
        }
        OffsetDateTime now = OffsetDateTime.now();
        List<String> questions = result.clarificationQuestions().isEmpty()
                ? List.of("请补充信息后继续研究。")
                : result.clarificationQuestions();
        questions.forEach(question -> messageRepository.save(new ResearchMessage(
                idGenerator.newId(),
                job.getConversationId(),
                ResearchMessageRole.ASSISTANT,
                ResearchMessageType.CLARIFICATION_QUESTION,
                question,
                job.getId(),
                now
        )));
        log.info(
                "Saved clarification messages conversationId={} jobId={} questionCount={}",
                job.getConversationId(),
                job.getId(),
                questions.size()
        );
        conversationRepository.findById(job.getConversationId()).ifPresent(conversation -> {
            conversation.markWaitingUser(now);
            conversationRepository.save(conversation);
            log.info(
                    "Research conversation waiting for user conversationId={} jobId={} status={}",
                    conversation.getId(),
                    job.getId(),
                    conversation.getStatus()
            );
        });
    }

    private void updateConversationActive(ResearchJob job, ResearchWorkflowResult result) {
        if (job.getConversationId() == null) {
            return;
        }
        OffsetDateTime now = OffsetDateTime.now();
        messageRepository.save(new ResearchMessage(
                idGenerator.newId(),
                job.getConversationId(),
                ResearchMessageRole.ASSISTANT,
                ResearchMessageType.REPORT_SUMMARY,
                result.report().getTitle(),
                job.getId(),
                now
        ));
        log.info(
                "Saved report summary message conversationId={} jobId={} reportId={}",
                job.getConversationId(),
                job.getId(),
                result.report().getId()
        );
        conversationRepository.findById(job.getConversationId()).ifPresent(conversation -> {
            conversation.markActive(now);
            conversationRepository.save(conversation);
            log.info(
                    "Research conversation active conversationId={} jobId={} status={}",
                    conversation.getId(),
                    job.getId(),
                    conversation.getStatus()
            );
        });
    }

    private void updateConversationFailed(ResearchJob job, String errorMessage) {
        if (job.getConversationId() == null) {
            return;
        }
        OffsetDateTime now = OffsetDateTime.now();
        messageRepository.save(new ResearchMessage(
                idGenerator.newId(),
                job.getConversationId(),
                ResearchMessageRole.ASSISTANT,
                ResearchMessageType.ERROR,
                errorMessage == null || errorMessage.isBlank() ? "Agent 执行失败。" : errorMessage,
                job.getId(),
                now
        ));
        log.info(
                "Saved error message conversationId={} jobId={}",
                job.getConversationId(),
                job.getId()
        );
        conversationRepository.findById(job.getConversationId()).ifPresent(conversation -> {
            conversation.markFailed(now);
            conversationRepository.save(conversation);
            log.info(
                    "Research conversation failed conversationId={} jobId={} status={}",
                    conversation.getId(),
                    job.getId(),
                    conversation.getStatus()
            );
        });
    }
}
