package com.yjc.equityresearch.agent;

import com.yjc.equityresearch.agent.python.AgentServiceClient;
import com.yjc.equityresearch.agent.python.AgentServiceResult;
import com.yjc.equityresearch.agent.python.AgentConversationMessage;
import com.yjc.equityresearch.agent.python.AgentUserPreferences;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class ResearchAgentOrchestrator {
    private final AgentServiceClient agentServiceClient;

    public ResearchAgentOrchestrator(AgentServiceClient agentServiceClient) {
        this.agentServiceClient = agentServiceClient;
    }

    public ResearchWorkflowResult run(UUID jobId, String query) {
        return run(jobId, query, List.of());
    }

    public ResearchWorkflowResult run(UUID jobId, String query, List<AgentConversationMessage> conversationMessages) {
        return run(jobId, query, conversationMessages, AgentUserPreferences.empty());
    }

    public ResearchWorkflowResult run(
            UUID jobId,
            String query,
            List<AgentConversationMessage> conversationMessages,
            AgentUserPreferences userPreferences
    ) {
        AgentServiceResult result = agentServiceClient.run(jobId, query, "zh-CN", conversationMessages, userPreferences);
        return new ResearchWorkflowResult(
                result.report(),
                result.evidenceItems(),
                result.toolCallRecords(),
                result.runStatus(),
                result.clarificationQuestions()
        );
    }
}
