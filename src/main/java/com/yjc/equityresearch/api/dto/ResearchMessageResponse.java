package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.domain.ResearchMessage;
import com.yjc.equityresearch.domain.ResearchMessageRole;
import com.yjc.equityresearch.domain.ResearchMessageType;
import java.time.OffsetDateTime;
import java.util.UUID;

public record ResearchMessageResponse(
        UUID messageId,
        UUID conversationId,
        ResearchMessageRole role,
        ResearchMessageType messageType,
        String content,
        UUID jobId,
        OffsetDateTime createdAt
) {
    public static ResearchMessageResponse from(ResearchMessage message) {
        return new ResearchMessageResponse(
                message.getId(),
                message.getConversationId(),
                message.getRole(),
                message.getMessageType(),
                message.getContent(),
                message.getJobId(),
                message.getCreatedAt()
        );
    }
}
