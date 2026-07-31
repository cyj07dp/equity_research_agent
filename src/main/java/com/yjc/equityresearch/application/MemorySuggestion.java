package com.yjc.equityresearch.application;

public record MemorySuggestion(
        String field,
        String label,
        String currentValue,
        String suggestedValue,
        String suggestedLabel,
        String action,
        String reason,
        double confidence
) {
}
