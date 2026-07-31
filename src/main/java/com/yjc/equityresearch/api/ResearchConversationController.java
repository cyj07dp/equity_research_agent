package com.yjc.equityresearch.api;

import com.yjc.equityresearch.api.dto.AppendConversationMessageRequest;
import com.yjc.equityresearch.api.dto.CreateConversationRequest;
import com.yjc.equityresearch.api.dto.MemorySuggestionResponse;
import com.yjc.equityresearch.api.dto.ResearchConversationResponse;
import com.yjc.equityresearch.api.dto.ResearchConversationSummaryResponse;
import com.yjc.equityresearch.application.MemorySuggestionService;
import com.yjc.equityresearch.application.ResearchConversationService;
import com.yjc.equityresearch.application.UserPreferenceService;
import com.yjc.equityresearch.domain.ResearchMessageRole;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/conversations")
public class ResearchConversationController {
    private final ResearchConversationService conversationService;
    private final UserPreferenceService preferenceService;
    private final MemorySuggestionService memorySuggestionService;

    public ResearchConversationController(
            ResearchConversationService conversationService,
            UserPreferenceService preferenceService,
            MemorySuggestionService memorySuggestionService
    ) {
        this.conversationService = conversationService;
        this.preferenceService = preferenceService;
        this.memorySuggestionService = memorySuggestionService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public ResearchConversationResponse createConversation(@Valid @RequestBody CreateConversationRequest request) {
        return ResearchConversationResponse.from(
                conversationService.createConversation(request.query()),
                memorySuggestionsFor(request.query())
        );
    }

    @GetMapping
    public List<ResearchConversationSummaryResponse> listConversations() {
        return conversationService.listRecentConversations().stream()
                .map(ResearchConversationSummaryResponse::from)
                .toList();
    }

    @GetMapping("/{conversationId}")
    public ResearchConversationResponse getConversation(@PathVariable UUID conversationId) {
        var detail = conversationService.getConversation(conversationId);
        String latestUserMessage = detail.messages().stream()
                .filter(message -> message.getRole() == ResearchMessageRole.USER)
                .reduce((first, second) -> second)
                .map(message -> message.getContent())
                .orElse("");
        return ResearchConversationResponse.from(detail, memorySuggestionsFor(latestUserMessage));
    }

    @PostMapping("/{conversationId}/messages")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public ResearchConversationResponse appendMessage(
            @PathVariable UUID conversationId,
            @Valid @RequestBody AppendConversationMessageRequest request
    ) {
        return ResearchConversationResponse.from(
                conversationService.appendUserMessage(conversationId, request.content()),
                memorySuggestionsFor(request.content())
        );
    }

    private List<MemorySuggestionResponse> memorySuggestionsFor(String query) {
        return memorySuggestionService.suggestForQuery(query, preferenceService.getDefaultUserPreferences()).stream()
                .map(MemorySuggestionResponse::from)
                .toList();
    }
}
