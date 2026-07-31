package com.yjc.equityresearch.application;

import com.yjc.equityresearch.agent.python.AgentUserPreferences;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class MemorySuggestionService {
    public List<MemorySuggestion> suggestForQuery(String query, AgentUserPreferences preferences) {
        if (query == null || query.isBlank()) {
            return List.of();
        }
        AgentUserPreferences current = preferences == null ? AgentUserPreferences.empty() : preferences;
        String normalized = query.toLowerCase();
        List<MemorySuggestion> suggestions = new ArrayList<>();
        addSuggestion(suggestions, "defaultMarket", "默认市场", current.defaultMarket(), detectMarket(normalized), query);
        addSuggestion(suggestions, "riskTolerance", "风险偏好", current.riskTolerance(), detectRisk(normalized), query);
        addSuggestion(suggestions, "timeHorizon", "投资期限", current.timeHorizon(), detectHorizon(normalized), query);
        addSuggestion(suggestions, "reportStyle", "报告风格", current.reportStyle(), detectReportStyle(normalized), query);
        return suggestions;
    }

    private void addSuggestion(
            List<MemorySuggestion> suggestions,
            String field,
            String label,
            String currentValue,
            String suggestedValue,
            String originalQuery
    ) {
        if (suggestedValue == null || suggestedValue.isBlank()) {
            return;
        }
        String current = currentValue == null ? "" : currentValue;
        if (suggestedValue.equals(current)) {
            return;
        }
        String action = current.isBlank() ? "CREATE" : "UPDATE";
        String reason = "用户本轮问题中表达了“" + label + "”偏好：" + snippet(originalQuery);
        suggestions.add(new MemorySuggestion(
                field,
                label,
                current,
                suggestedValue,
                displayValue(field, suggestedValue),
                action,
                reason,
                0.78
        ));
    }

    private String detectMarket(String text) {
        if (containsAny(text, "美股", "美国股票", "美国市场", "us stocks", "u.s. stocks")) {
            return "US";
        }
        if (containsAny(text, "港股", "香港股票", "香港市场")) {
            return "HK";
        }
        if (containsAny(text, "a股", "a 股", "a-share", "中国股票", "沪深")) {
            return "CN";
        }
        return "";
    }

    private String detectRisk(String text) {
        if (containsAny(text, "保守", "稳健", "低风险", "回撤小", "控制回撤")) {
            return "LOW";
        }
        if (containsAny(text, "平衡", "均衡", "中等风险")) {
            return "MEDIUM";
        }
        if (containsAny(text, "进取", "激进", "高风险", "高弹性", "成长弹性")) {
            return "HIGH";
        }
        return "";
    }

    private String detectHorizon(String text) {
        if (containsAny(text, "短期", "短线", "最近几天", "一周内", "这周")) {
            return "SHORT_TERM";
        }
        if (containsAny(text, "中期", "几个月", "半年")) {
            return "MEDIUM_TERM";
        }
        if (containsAny(text, "长期", "长线", "长期配置", "三年以上", "五年以上")) {
            return "LONG_TERM";
        }
        return "";
    }

    private String detectReportStyle(String text) {
        if (containsAny(text, "简洁", "简单说", "一句话", "结论优先")) {
            return "CONCISE";
        }
        if (containsAny(text, "详细", "完整备忘录", "深度", "展开讲")) {
            return "DETAILED_MEMO";
        }
        if (containsAny(text, "新手", "小白", "看不懂财报", "通俗")) {
            return "BEGINNER_FRIENDLY";
        }
        return "";
    }

    private boolean containsAny(String text, String... candidates) {
        for (String candidate : candidates) {
            if (text.contains(candidate.toLowerCase())) {
                return true;
            }
        }
        return false;
    }

    private String displayValue(String field, String value) {
        return switch (field) {
            case "defaultMarket" -> switch (value) {
                case "US" -> "美股";
                case "HK" -> "港股";
                case "CN" -> "A 股";
                default -> value;
            };
            case "riskTolerance" -> switch (value) {
                case "LOW" -> "保守";
                case "MEDIUM" -> "平衡";
                case "HIGH" -> "进取";
                default -> value;
            };
            case "timeHorizon" -> switch (value) {
                case "SHORT_TERM" -> "短期";
                case "MEDIUM_TERM" -> "中期";
                case "LONG_TERM" -> "长期";
                default -> value;
            };
            case "reportStyle" -> switch (value) {
                case "CONCISE" -> "简洁结论";
                case "DETAILED_MEMO" -> "详细备忘录";
                case "BEGINNER_FRIENDLY" -> "新手友好";
                default -> value;
            };
            default -> value;
        };
    }

    private String snippet(String value) {
        String normalized = value.replaceAll("\\s+", " ").trim();
        if (normalized.length() <= 80) {
            return normalized;
        }
        return normalized.substring(0, 80) + "...";
    }
}
