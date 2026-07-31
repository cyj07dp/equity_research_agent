package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.domain.ResearchConversation;
import com.yjc.equityresearch.domain.ResearchConversationStatus;
import java.time.OffsetDateTime;
import java.util.UUID;

public record ResearchConversationSummaryResponse(
        UUID conversationId,
        String title,
        ResearchConversationStatus status,
        OffsetDateTime updatedAt
) {
    public static ResearchConversationSummaryResponse from(ResearchConversation conversation) {
        return new ResearchConversationSummaryResponse(
                conversation.getId(),
                conversation.getTitle(),
                conversation.getStatus(),
                conversation.getUpdatedAt()
        );
    }
}
