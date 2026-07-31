package com.yjc.equityresearch.api.dto;

public record ResearchCitationResponse(
        int id,
        String title,
        String sourceName,
        String url,
        String supports
) {
}
