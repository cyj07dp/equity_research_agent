package com.yjc.equityresearch.application;

import com.yjc.equityresearch.domain.ResearchConversation;
import com.yjc.equityresearch.domain.ResearchConversationStatus;
import com.yjc.equityresearch.domain.ResearchJob;
import com.yjc.equityresearch.domain.ResearchJobStatus;
import com.yjc.equityresearch.domain.ResearchMessage;
import com.yjc.equityresearch.domain.ResearchMessageRole;
import com.yjc.equityresearch.domain.ResearchMessageType;
import com.yjc.equityresearch.config.IdGenerator;
import com.yjc.equityresearch.repository.ResearchConversationRepository;
import com.yjc.equityresearch.repository.ResearchJobRepository;
import com.yjc.equityresearch.repository.ResearchMessageRepository;
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
public class ResearchConversationService {
    private static final Logger log = LoggerFactory.getLogger(ResearchConversationService.class);

    private final ResearchConversationRepository conversationRepository;
    private final ResearchMessageRepository messageRepository;
    private final ResearchJobRepository jobRepository;
    private final ResearchJobService jobService;
    private final Executor researchTaskExecutor;
    private final IdGenerator idGenerator;

    public ResearchConversationService(
            ResearchConversationRepository conversationRepository,
            ResearchMessageRepository messageRepository,
            ResearchJobRepository jobRepository,
            ResearchJobService jobService,
            @Qualifier("researchTaskExecutor") Executor researchTaskExecutor,
            IdGenerator idGenerator
    ) {
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
        this.jobRepository = jobRepository;
        this.jobService = jobService;
        this.researchTaskExecutor = researchTaskExecutor;
        this.idGenerator = idGenerator;
    }

    public ResearchConversationResult createConversation(String query) {
        String normalized = normalizeMessage(query);
        OffsetDateTime now = OffsetDateTime.now();
        ResearchConversation conversation = conversationRepository.save(new ResearchConversation(
                idGenerator.newId(),
                titleFrom(normalized),
                ResearchConversationStatus.RUNNING,
                now,
                now
        ));
        ResearchMessage message = messageRepository.save(new ResearchMessage(
                idGenerator.newId(),
                conversation.getId(),
                ResearchMessageRole.USER,
                ResearchMessageType.QUERY,
                normalized,
                null,
                now
        ));
        ResearchJob job = createJobForMessage(conversation.getId(), message.getId(), normalized, now);
        message.attachJob(job.getId());
        messageRepository.save(message);
        log.info(
                "Created research conversation conversationId={} messageId={} jobId={} status={} queryLength={}",
                conversation.getId(),
                message.getId(),
                job.getId(),
                conversation.getStatus(),
                normalized.length()
        );
        researchTaskExecutor.execute(() -> jobService.processJob(job.getId()));
        return new ResearchConversationResult(conversation, message, job);
    }

    @Transactional(readOnly = true)
    public List<ResearchConversation> listRecentConversations() {
        List<ResearchConversation> conversations = conversationRepository.findTop30ByOrderByUpdatedAtDesc();
        log.info("Loaded recent research conversations count={}", conversations.size());
        return conversations;
    }

    public ResearchConversationResult appendUserMessage(UUID conversationId, String content) {
        String normalized = normalizeMessage(content);
        ResearchConversation conversation = conversationRepository.findById(conversationId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Research conversation not found"));
        OffsetDateTime now = OffsetDateTime.now();
        ResearchMessage message = messageRepository.save(new ResearchMessage(
                idGenerator.newId(),
                conversationId,
                ResearchMessageRole.USER,
                ResearchMessageType.CLARIFICATION_ANSWER,
                normalized,
                null,
                now
        ));
        ResearchJob job = createJobForMessage(conversationId, message.getId(), normalized, now);
        message.attachJob(job.getId());
        messageRepository.save(message);
        conversation.markRunning(now);
        ResearchConversation savedConversation = conversationRepository.save(conversation);
        log.info(
                "Appended research conversation message conversationId={} messageId={} jobId={} status={} contentLength={}",
                savedConversation.getId(),
                message.getId(),
                job.getId(),
                savedConversation.getStatus(),
                normalized.length()
        );
        researchTaskExecutor.execute(() -> jobService.processJob(job.getId()));
        return new ResearchConversationResult(savedConversation, message, job);
    }

    @Transactional(readOnly = true)
    public ResearchConversationDetail getConversation(UUID conversationId) {
        ResearchConversation conversation = conversationRepository.findById(conversationId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Research conversation not found"));
        List<ResearchMessage> messages = messageRepository.findByConversationIdOrderByCreatedAtAsc(conversationId);
        log.info(
                "Loaded research conversation conversationId={} status={} messageCount={}",
                conversation.getId(),
                conversation.getStatus(),
                messages.size()
        );
        return new ResearchConversationDetail(conversation, messages);
    }

    private ResearchJob createJobForMessage(UUID conversationId, UUID messageId, String query, OffsetDateTime now) {
        return jobRepository.save(new ResearchJob(
                idGenerator.newId(),
                query,
                ResearchJobStatus.PENDING,
                now,
                conversationId,
                messageId
        ));
    }

    private String normalizeMessage(String message) {
        if (message == null || message.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Message content is required");
        }
        String normalized = message.trim();
        if (normalized.length() > 2000) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Message content is too long");
        }
        return normalized;
    }

    private String titleFrom(String query) {
        if (query.length() <= 40) {
            return query;
        }
        return query.substring(0, 40);
    }
}
