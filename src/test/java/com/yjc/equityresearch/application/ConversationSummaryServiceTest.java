package com.yjc.equityresearch.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.yjc.equityresearch.agent.python.AgentServiceClient;
import com.yjc.equityresearch.domain.ResearchMessage;
import com.yjc.equityresearch.domain.ResearchMessageRole;
import com.yjc.equityresearch.domain.ResearchMessageType;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ConversationSummaryServiceTest {
    private final AgentServiceClient agentServiceClient = org.mockito.Mockito.mock(AgentServiceClient.class);
    private final ConversationSummaryService service = new ConversationSummaryService(agentServiceClient);

    @Test
    void doesNotSummarizeShortConversation() {
        List<ResearchMessage> messages = messages(4);

        assertThat(service.shouldSummarize(messages)).isFalse();
        assertThat(service.compressedMessages(messages, "")).hasSize(4);
    }

    @Test
    void compressesLongConversationIntoSummaryPlusRecentMessages() {
        List<ResearchMessage> messages = messages(14);
        when(agentServiceClient.summarizeConversation(anyList(), anyString(), anyString()))
                .thenReturn("{\"importantHistory\":[\"USER: message-0\"],\"notEvidence\":[\"不是市场证据\"]}");

        String summary = service.summarize(messages);

        assertThat(service.shouldSummarize(messages)).isTrue();
        assertThat(summary).contains("importantHistory").contains("USER: message-0");
        assertThat(service.compressedMessages(messages, summary))
                .hasSize(9)
                .first()
                .satisfies(message -> {
                    assertThat(message.role()).isEqualTo("SYSTEM");
                    assertThat(message.content()).contains("importantHistory");
                });
        assertThat(service.compressedMessages(messages, summary).get(1).content()).isEqualTo("message-6");
    }

    @Test
    void fallsBackToLocalJsonSummaryWhenPythonSummaryFails() {
        List<ResearchMessage> messages = messages(14);
        when(agentServiceClient.summarizeConversation(anyList(), anyString(), anyString()))
                .thenThrow(new IllegalStateException("python unavailable"));

        String summary = service.summarize(messages);

        assertThat(summary)
                .contains("importantHistory")
                .contains("notEvidence")
                .contains("USER: message-0");
    }

    private List<ResearchMessage> messages(int count) {
        List<ResearchMessage> messages = new ArrayList<>();
        UUID conversationId = UUID.randomUUID();
        OffsetDateTime baseTime = OffsetDateTime.now();
        for (int index = 0; index < count; index++) {
            messages.add(new ResearchMessage(
                    UUID.randomUUID(),
                    conversationId,
                    index % 2 == 0 ? ResearchMessageRole.USER : ResearchMessageRole.ASSISTANT,
                    ResearchMessageType.QUERY,
                    "message-" + index,
                    null,
                    baseTime.plusSeconds(index)
            ));
        }
        return messages;
    }
}
