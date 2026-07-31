package com.yjc.equityresearch.api.dto;

import com.yjc.equityresearch.agent.python.AgentUserPreferences;
import java.util.List;

public record UserPreferenceResponse(
        String preferredLocale,
        String defaultMarket,
        String riskTolerance,
        String timeHorizon,
        String reportStyle,
        List<String> preferredSectors,
        List<String> excludedSectors,
        List<String> preferredAssets,
        String notes,
        boolean enabled
) {
    public static UserPreferenceResponse from(AgentUserPreferences preferences) {
        return new UserPreferenceResponse(
                preferences.preferredLocale(),
                preferences.defaultMarket(),
                preferences.riskTolerance(),
                preferences.timeHorizon(),
                preferences.reportStyle(),
                preferences.preferredSectors(),
                preferences.excludedSectors(),
                preferences.preferredAssets(),
                preferences.notes(),
                preferences.enabled()
        );
    }
}
