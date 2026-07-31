package com.yjc.equityresearch.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.yjc.equityresearch.agent.python.AgentUserPreferences;
import com.yjc.equityresearch.api.dto.UserPreferenceRequest;
import com.yjc.equityresearch.config.IdGenerator;
import com.yjc.equityresearch.domain.AgentUser;
import com.yjc.equityresearch.domain.AgentUserPreference;
import com.yjc.equityresearch.repository.AgentUserPreferenceRepository;
import com.yjc.equityresearch.repository.AgentUserRepository;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class UserPreferenceServiceTest {
    @Test
    void returnsEmptyPreferencesWhenDefaultUserDoesNotExist() {
        AgentUserRepository userRepository = org.mockito.Mockito.mock(AgentUserRepository.class);
        AgentUserPreferenceRepository preferenceRepository = org.mockito.Mockito.mock(AgentUserPreferenceRepository.class);
        UserPreferenceService service = new UserPreferenceService(
                userRepository,
                preferenceRepository,
                new IdGenerator(),
                new ObjectMapper()
        );
        when(userRepository.findByAuthProviderAndExternalSubject("local", "default_user")).thenReturn(Optional.empty());

        AgentUserPreferences preferences = service.getDefaultUserPreferences();

        assertThat(preferences).isEqualTo(AgentUserPreferences.empty());
    }

    @Test
    void updatesDefaultPreferencesAndNormalizesListFields() {
        UUID userId = UUID.randomUUID();
        AgentUser user = new AgentUser(
                userId,
                "默认用户",
                "local",
                "default_user",
                "ACTIVE",
                OffsetDateTime.now(),
                OffsetDateTime.now()
        );
        AgentUserRepository userRepository = org.mockito.Mockito.mock(AgentUserRepository.class);
        AgentUserPreferenceRepository preferenceRepository = org.mockito.Mockito.mock(AgentUserPreferenceRepository.class);
        UserPreferenceService service = new UserPreferenceService(
                userRepository,
                preferenceRepository,
                new IdGenerator(),
                new ObjectMapper()
        );
        when(userRepository.findByAuthProviderAndExternalSubject("local", "default_user")).thenReturn(Optional.of(user));
        when(preferenceRepository.findByUserId(userId)).thenReturn(Optional.empty());
        when(preferenceRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        AgentUserPreferences preferences = service.updateDefaultUserPreferences(new UserPreferenceRequest(
                " zh-CN ",
                " US ",
                " LOW ",
                " LONG_TERM ",
                " CONCISE ",
                List.of(" AI ", "", "Semiconductor", " "),
                Arrays.asList("Crypto", null),
                List.of(" ETF "),
                " 更关注回撤控制 ",
                true
        ));

        assertThat(preferences.preferredLocale()).isEqualTo("zh-CN");
        assertThat(preferences.defaultMarket()).isEqualTo("US");
        assertThat(preferences.riskTolerance()).isEqualTo("LOW");
        assertThat(preferences.timeHorizon()).isEqualTo("LONG_TERM");
        assertThat(preferences.reportStyle()).isEqualTo("CONCISE");
        assertThat(preferences.preferredSectors()).containsExactly("AI", "Semiconductor");
        assertThat(preferences.excludedSectors()).containsExactly("Crypto");
        assertThat(preferences.preferredAssets()).containsExactly("ETF");
        assertThat(preferences.notes()).isEqualTo("更关注回撤控制");
        assertThat(preferences.enabled()).isTrue();
    }

    @Test
    void readsExistingDisabledPreferencesWithoutLosingEnabledFlag() {
        UUID userId = UUID.randomUUID();
        OffsetDateTime now = OffsetDateTime.now();
        AgentUser user = new AgentUser(userId, "默认用户", "local", "default_user", "ACTIVE", now, now);
        AgentUserPreference preference = new AgentUserPreference(
                UUID.randomUUID(),
                userId,
                "zh-CN",
                "US",
                "LOW",
                "LONG_TERM",
                "CONCISE",
                "[\"AI\"]",
                "[\"Crypto\"]",
                "[\"ETF\"]",
                "暂时关闭偏好注入",
                "USER_PROVIDED",
                BigDecimal.ONE.setScale(4),
                false,
                now,
                now
        );
        AgentUserRepository userRepository = org.mockito.Mockito.mock(AgentUserRepository.class);
        AgentUserPreferenceRepository preferenceRepository = org.mockito.Mockito.mock(AgentUserPreferenceRepository.class);
        UserPreferenceService service = new UserPreferenceService(
                userRepository,
                preferenceRepository,
                new IdGenerator(),
                new ObjectMapper()
        );
        when(userRepository.findByAuthProviderAndExternalSubject("local", "default_user")).thenReturn(Optional.of(user));
        when(preferenceRepository.findByUserId(userId)).thenReturn(Optional.of(preference));

        AgentUserPreferences preferences = service.getDefaultUserPreferences();

        assertThat(preferences.defaultMarket()).isEqualTo("US");
        assertThat(preferences.preferredSectors()).containsExactly("AI");
        assertThat(preferences.enabled()).isFalse();
    }
}
