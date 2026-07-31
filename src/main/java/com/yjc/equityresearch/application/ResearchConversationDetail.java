package com.yjc.equityresearch.application;

import com.yjc.equityresearch.domain.ResearchConversation;
import com.yjc.equityresearch.domain.ResearchMessage;
import java.util.List;

public record ResearchConversationDetail(
        ResearchConversation conversation,
        List<ResearchMessage> messages
) {
}
