package com.yjc.equityresearch.agent.python;

import java.util.UUID;
import java.util.List;

public interface AgentServiceClient {
    AgentServiceResult run(UUID runId, String query, String locale);

    default AgentServiceResult run(
            UUID runId,
            String query,
            String locale,
            List<AgentConversationMessage> conversationMessages
    ) {
        return run(runId, query, locale);
    }

    default AgentServiceResult run(
            UUID runId,
            String query,
            String locale,
            List<AgentConversationMessage> conversationMessages,
            AgentUserPreferences userPreferences
    ) {
        return run(runId, query, locale, conversationMessages);
    }

    default String summarizeConversation(
            List<AgentConversationMessage> conversationMessages,
            String existingSummary,
            String locale
    ) {
        return "";
    }
}
