package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.application.ResearchConversationDetail;
import com.yjc.equityresearch.application.ResearchConversationResult;
import com.yjc.equityresearch.domain.ResearchConversation;
import com.yjc.equityresearch.domain.ResearchConversationStatus;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

public record ResearchConversationResponse(
        UUID conversationId,
        String title,
        ResearchConversationStatus status,
        UUID currentJobId,
        List<ResearchMessageResponse> messages,
        List<MemorySuggestionResponse> memorySuggestions,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
    public static ResearchConversationResponse from(ResearchConversationResult result) {
        return from(result, List.of());
    }

    public static ResearchConversationResponse from(
            ResearchConversationResult result,
            List<MemorySuggestionResponse> memorySuggestions
    ) {
        ResearchConversation conversation = result.conversation();
        return new ResearchConversationResponse(
                conversation.getId(),
                conversation.getTitle(),
                conversation.getStatus(),
                result.job().getId(),
                List.of(ResearchMessageResponse.from(result.message())),
                memorySuggestions,
                conversation.getCreatedAt(),
                conversation.getUpdatedAt()
        );
    }

    public static ResearchConversationResponse from(ResearchConversationDetail detail) {
        return from(detail, List.of());
    }

    public static ResearchConversationResponse from(
            ResearchConversationDetail detail,
            List<MemorySuggestionResponse> memorySuggestions
    ) {
        ResearchConversation conversation = detail.conversation();
        UUID currentJobId = detail.messages().stream()
                .filter(message -> message.getJobId() != null)
                .reduce((first, second) -> second)
                .map(message -> message.getJobId())
                .orElse(null);
        return new ResearchConversationResponse(
                conversation.getId(),
                conversation.getTitle(),
                conversation.getStatus(),
                currentJobId,
                detail.messages().stream().map(ResearchMessageResponse::from).toList(),
                memorySuggestions,
                conversation.getCreatedAt(),
                conversation.getUpdatedAt()
        );
    }
}
