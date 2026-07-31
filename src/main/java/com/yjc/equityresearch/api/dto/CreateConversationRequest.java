package com.yjc.equityresearch.api.dto;

import jakarta.validation.constraints.NotBlank;

public record CreateConversationRequest(
        @NotBlank
        String query
) {
}
