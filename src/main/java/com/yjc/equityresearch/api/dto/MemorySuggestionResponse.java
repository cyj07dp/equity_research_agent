package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.application.MemorySuggestion;

public record MemorySuggestionResponse(
        String field,
        String label,
        String currentValue,
        String suggestedValue,
        String suggestedLabel,
        String action,
        String reason,
        double confidence
) {
    public static MemorySuggestionResponse from(MemorySuggestion suggestion) {
        return new MemorySuggestionResponse(
                suggestion.field(),
                suggestion.label(),
                suggestion.currentValue(),
                suggestion.suggestedValue(),
                suggestion.suggestedLabel(),
                suggestion.action(),
                suggestion.reason(),
                suggestion.confidence()
        );
    }
}
