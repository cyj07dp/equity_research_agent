package com.yjc.equityresearch.application;

import static org.assertj.core.api.Assertions.assertThat;

import com.yjc.equityresearch.agent.python.AgentUserPreferences;
import java.util.List;
import org.junit.jupiter.api.Test;

class MemorySuggestionServiceTest {
    private final MemorySuggestionService service = new MemorySuggestionService();

    @Test
    void suggestsCreatingPreferenceWhenCurrentValueIsEmpty() {
        AgentUserPreferences preferences = AgentUserPreferences.empty();

        List<MemorySuggestion> suggestions = service.suggestForQuery("以后默认帮我看美股，我比较保守", preferences);

        assertThat(suggestions)
                .extracting(MemorySuggestion::field)
                .contains("defaultMarket", "riskTolerance");
        assertThat(suggestions)
                .filteredOn(suggestion -> suggestion.field().equals("defaultMarket"))
                .first()
                .satisfies(suggestion -> {
                    assertThat(suggestion.action()).isEqualTo("CREATE");
                    assertThat(suggestion.currentValue()).isEmpty();
                    assertThat(suggestion.suggestedValue()).isEqualTo("US");
                });
    }

    @Test
    void suggestsUpdatingPreferenceWhenQueryConflictsWithCurrentValue() {
        AgentUserPreferences preferences = new AgentUserPreferences(
                "zh-CN",
                "US",
                "LOW",
                "",
                "",
                List.of(),
                List.of(),
                List.of(),
                "",
                true
        );

        List<MemorySuggestion> suggestions = service.suggestForQuery("这次帮我看港股，风格可以进取一点", preferences);

        assertThat(suggestions)
                .extracting(MemorySuggestion::field)
                .containsExactlyInAnyOrder("defaultMarket", "riskTolerance");
        assertThat(suggestions)
                .filteredOn(suggestion -> suggestion.field().equals("defaultMarket"))
                .first()
                .satisfies(suggestion -> {
                    assertThat(suggestion.action()).isEqualTo("UPDATE");
                    assertThat(suggestion.currentValue()).isEqualTo("US");
                    assertThat(suggestion.suggestedValue()).isEqualTo("HK");
                });
    }

    @Test
    void doesNotSuggestWhenQueryPreferenceMatchesCurrentValue() {
        AgentUserPreferences preferences = new AgentUserPreferences(
                "zh-CN",
                "US",
                "LOW",
                "LONG_TERM",
                "CONCISE",
                List.of(),
                List.of(),
                List.of(),
                "",
                true
        );

        List<MemorySuggestion> suggestions = service.suggestForQuery("继续按美股、保守、长期、简洁的方式分析苹果", preferences);

        assertThat(suggestions).isEmpty();
    }
}
