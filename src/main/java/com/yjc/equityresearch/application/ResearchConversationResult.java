package com.yjc.equityresearch.application;

import com.yjc.equityresearch.domain.ResearchConversation;
import com.yjc.equityresearch.domain.ResearchJob;
import com.yjc.equityresearch.domain.ResearchMessage;

public record ResearchConversationResult(
        ResearchConversation conversation,
        ResearchMessage message,
        ResearchJob job
) {
}
