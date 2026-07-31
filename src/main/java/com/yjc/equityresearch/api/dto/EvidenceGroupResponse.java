package com.yjc.equityresearch.api.dto;

import java.util.List;

public record EvidenceGroupResponse(
        String sourceType,
        int count,
        List<EvidenceItemResponse> items
) {
}
