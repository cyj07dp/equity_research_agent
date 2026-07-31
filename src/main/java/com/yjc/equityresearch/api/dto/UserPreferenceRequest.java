package com.yjc.equityresearch.api.dto;

import java.util.List;

public record UserPreferenceRequest(
        String preferredLocale,
        String defaultMarket,
        String riskTolerance,
        String timeHorizon,
        String reportStyle,
        List<String> preferredSectors,
        List<String> excludedSectors,
        List<String> preferredAssets,
        String notes,
        Boolean enabled
) {
}
