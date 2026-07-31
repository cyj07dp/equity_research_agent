package com.yjc.equityresearch.agent.python;

import java.util.List;

public record AgentUserPreferences(
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
    public static AgentUserPreferences empty() {
        return new AgentUserPreferences("zh-CN", "", "", "", "", List.of(), List.of(), List.of(), "", false);
    }
}
