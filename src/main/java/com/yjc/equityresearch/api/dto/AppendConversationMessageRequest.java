package com.yjc.equityresearch.api.dto;

import jakarta.validation.constraints.NotBlank;

public record AppendConversationMessageRequest(
        @NotBlank
        String content
) {
}
