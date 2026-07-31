package com.yjc.equityresearch.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.atLeastOnce;

import com.yjc.equityresearch.config.IdGenerator;
import com.yjc.equityresearch.domain.ResearchConversation;
import com.yjc.equityresearch.domain.ResearchConversationStatus;
import com.yjc.equityresearch.domain.ResearchJob;
import com.yjc.equityresearch.domain.ResearchMessage;
import com.yjc.equityresearch.domain.ResearchMessageRole;
import com.yjc.equityresearch.domain.ResearchMessageType;
import com.yjc.equityresearch.repository.ResearchConversationRepository;
import com.yjc.equityresearch.repository.ResearchJobRepository;
import com.yjc.equityresearch.repository.ResearchMessageRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.Executor;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class ResearchConversationServiceTest {
    @Test
    void createConversationPersistsUserMessageAndCreatesTriggeredJob() {
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchJobService jobService = org.mockito.Mockito.mock(ResearchJobService.class);
        Executor noOpExecutor = runnable -> {
        };
        ResearchConversationService service = new ResearchConversationService(
                conversationRepository,
                messageRepository,
                jobRepository,
                jobService,
                noOpExecutor,
                new IdGenerator()
        );
        when(conversationRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(messageRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(jobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ResearchConversationResult result = service.createConversation("现在要不要买苹果");

        ArgumentCaptor<ResearchMessage> messageCaptor = ArgumentCaptor.forClass(ResearchMessage.class);
        ArgumentCaptor<ResearchJob> jobCaptor = ArgumentCaptor.forClass(ResearchJob.class);
        verify(messageRepository, atLeastOnce()).save(messageCaptor.capture());
        verify(jobRepository).save(jobCaptor.capture());
        ResearchMessage firstSavedMessage = messageCaptor.getAllValues().getFirst();
        assertThat(result.conversation().getStatus()).isEqualTo(ResearchConversationStatus.RUNNING);
        assertThat(firstSavedMessage.getRole()).isEqualTo(ResearchMessageRole.USER);
        assertThat(firstSavedMessage.getMessageType()).isEqualTo(ResearchMessageType.QUERY);
        assertThat(jobCaptor.getValue().getConversationId()).isEqualTo(result.conversation().getId());
        assertThat(jobCaptor.getValue().getTriggerMessageId()).isEqualTo(firstSavedMessage.getId());
    }

    @Test
    void appendUserMessageCreatesNewJobInSameConversation() {
        UUID conversationId = UUID.randomUUID();
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchJobService jobService = org.mockito.Mockito.mock(ResearchJobService.class);
        ResearchConversationService service = new ResearchConversationService(
                conversationRepository,
                messageRepository,
                jobRepository,
                jobService,
                Runnable::run,
                new IdGenerator()
        );
        ResearchConversation conversation = new ResearchConversation(
                conversationId,
                "现在要不要买苹果",
                ResearchConversationStatus.WAITING_USER,
                OffsetDateTime.now(),
                OffsetDateTime.now()
        );
        when(conversationRepository.findById(conversationId)).thenReturn(Optional.of(conversation));
        when(conversationRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(messageRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(jobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ResearchConversationResult result = service.appendUserMessage(conversationId, "我指的是 Apple Inc.");

        ArgumentCaptor<ResearchJob> jobCaptor = ArgumentCaptor.forClass(ResearchJob.class);
        verify(jobRepository).save(jobCaptor.capture());
        verify(jobService).processJob(jobCaptor.getValue().getId());
        assertThat(result.conversation().getId()).isEqualTo(conversationId);
        assertThat(result.conversation().getStatus()).isEqualTo(ResearchConversationStatus.RUNNING);
        assertThat(result.message().getMessageType()).isEqualTo(ResearchMessageType.CLARIFICATION_ANSWER);
        assertThat(jobCaptor.getValue().getConversationId()).isEqualTo(conversationId);
    }

    @Test
    void getConversationReturnsMessagesInCreatedOrder() {
        UUID conversationId = UUID.randomUUID();
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchJobService jobService = org.mockito.Mockito.mock(ResearchJobService.class);
        ResearchConversationService service = new ResearchConversationService(
                conversationRepository,
                messageRepository,
                jobRepository,
                jobService,
                Runnable::run,
                new IdGenerator()
        );
        ResearchConversation conversation = new ResearchConversation(
                conversationId,
                "苹果研究",
                ResearchConversationStatus.ACTIVE,
                OffsetDateTime.now(),
                OffsetDateTime.now()
        );
        ResearchMessage message = new ResearchMessage(
                UUID.randomUUID(),
                conversationId,
                ResearchMessageRole.USER,
                ResearchMessageType.QUERY,
                "现在要不要买苹果",
                null,
                OffsetDateTime.now()
        );
        when(conversationRepository.findById(conversationId)).thenReturn(Optional.of(conversation));
        when(messageRepository.findByConversationIdOrderByCreatedAtAsc(conversationId)).thenReturn(List.of(message));

        ResearchConversationDetail detail = service.getConversation(conversationId);

        assertThat(detail.conversation()).isSameAs(conversation);
        assertThat(detail.messages()).containsExactly(message);
    }

    @Test
    void listRecentConversationsReturnsRepositoryOrder() {
        ResearchConversationRepository conversationRepository = org.mockito.Mockito.mock(ResearchConversationRepository.class);
        ResearchMessageRepository messageRepository = org.mockito.Mockito.mock(ResearchMessageRepository.class);
        ResearchJobRepository jobRepository = org.mockito.Mockito.mock(ResearchJobRepository.class);
        ResearchJobService jobService = org.mockito.Mockito.mock(ResearchJobService.class);
        ResearchConversationService service = new ResearchConversationService(
                conversationRepository,
                messageRepository,
                jobRepository,
                jobService,
                Runnable::run,
                new IdGenerator()
        );
        ResearchConversation latest = new ResearchConversation(
                UUID.randomUUID(),
                "英伟达研究",
                ResearchConversationStatus.ACTIVE,
                OffsetDateTime.now().minusDays(1),
                OffsetDateTime.now()
        );
        ResearchConversation older = new ResearchConversation(
                UUID.randomUUID(),
                "苹果研究",
                ResearchConversationStatus.RUNNING,
                OffsetDateTime.now().minusDays(2),
                OffsetDateTime.now().minusHours(2)
        );
        when(conversationRepository.findTop30ByOrderByUpdatedAtDesc()).thenReturn(List.of(latest, older));

        List<ResearchConversation> conversations = service.listRecentConversations();

        assertThat(conversations).containsExactly(latest, older);
    }
}
