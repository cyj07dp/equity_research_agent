package com.yjc.equityresearch.application;

import com.yjc.equityresearch.agent.python.AgentConversationMessage;
import com.yjc.equityresearch.agent.python.AgentServiceClient;
import com.yjc.equityresearch.domain.ResearchMessage;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class ConversationSummaryService {
    private static final Logger log = LoggerFactory.getLogger(ConversationSummaryService.class);
    private static final int SUMMARY_THRESHOLD = 12;
    private static final int RECENT_MESSAGE_LIMIT = 8;

    private final AgentServiceClient agentServiceClient;

    public ConversationSummaryService(AgentServiceClient agentServiceClient) {
        this.agentServiceClient = agentServiceClient;
    }

    public boolean shouldSummarize(List<ResearchMessage> messages) {
        return messages != null && messages.size() > SUMMARY_THRESHOLD;
    }

    public String summarize(List<ResearchMessage> messages) {
        return summarize(messages, "");
    }

    public String summarize(List<ResearchMessage> messages, String existingSummary) {
        if (messages == null || messages.isEmpty()) {
            return "";
        }
        try {
            String summary = agentServiceClient.summarizeConversation(
                    messages.stream().map(this::toAgentMessage).toList(),
                    existingSummary,
                    "zh-CN"
            );
            if (summary != null && !summary.isBlank()) {
                return summary;
            }
        } catch (RuntimeException exception) {
            log.warn("Python conversation-summary unavailable; using local fallback. error={}", exception.getMessage());
        }
        return fallbackSummary(messages);
    }

    private String fallbackSummary(List<ResearchMessage> messages) {
        if (messages == null || messages.isEmpty()) {
            return "";
        }
        List<ResearchMessage> olderMessages = messages.size() > RECENT_MESSAGE_LIMIT
                ? messages.subList(0, messages.size() - RECENT_MESSAGE_LIMIT)
                : messages;
        StringBuilder summary = new StringBuilder("{\"importantHistory\":[");
        olderMessages.stream()
                .limit(20)
                .forEach(message -> {
                    if (summary.charAt(summary.length() - 1) != '[') {
                        summary.append(',');
                    }
                    summary.append('"')
                            .append(escapeJson(message.getRole().name() + ": " + snippet(message.getContent(), 140)))
                            .append('"');
                });
        summary.append("],\"notEvidence\":[\"该摘要由历史对话压缩生成，只用于理解上下文，不是市场事实或投资证据。\"]}");
        return summary.toString();
    }

    public List<AgentConversationMessage> compressedMessages(List<ResearchMessage> messages, String summary) {
        if (messages == null || messages.isEmpty()) {
            return List.of();
        }
        if (!shouldSummarize(messages)) {
            return messages.stream().map(this::toAgentMessage).toList();
        }
        List<AgentConversationMessage> recentMessages = messages.subList(
                Math.max(0, messages.size() - RECENT_MESSAGE_LIMIT),
                messages.size()
        ).stream().map(this::toAgentMessage).toList();
        if (summary == null || summary.isBlank()) {
            return recentMessages;
        }
        return java.util.stream.Stream.concat(
                java.util.stream.Stream.of(new AgentConversationMessage("SYSTEM", summary)),
                recentMessages.stream()
        ).toList();
    }

    private AgentConversationMessage toAgentMessage(ResearchMessage message) {
        return new AgentConversationMessage(message.getRole().name(), message.getContent());
    }

    private String snippet(String value, int limit) {
        String normalized = value == null ? "" : value.replaceAll("\\s+", " ").trim();
        if (normalized.length() <= limit) {
            return normalized;
        }
        return normalized.substring(0, limit) + "...";
    }

    private String escapeJson(String value) {
        return value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r");
    }
}
