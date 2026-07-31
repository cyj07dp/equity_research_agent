package com.yjc.equityresearch.application;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
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
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UserPreferenceService {
    private static final String DEFAULT_AUTH_PROVIDER = "local";
    private static final String DEFAULT_EXTERNAL_SUBJECT = "default_user";

    private final AgentUserRepository userRepository;
    private final AgentUserPreferenceRepository preferenceRepository;
    private final IdGenerator idGenerator;
    private final ObjectMapper objectMapper;

    public UserPreferenceService(
            AgentUserRepository userRepository,
            AgentUserPreferenceRepository preferenceRepository,
            IdGenerator idGenerator,
            ObjectMapper objectMapper
    ) {
        this.userRepository = userRepository;
        this.preferenceRepository = preferenceRepository;
        this.idGenerator = idGenerator;
        this.objectMapper = objectMapper;
    }

    @Transactional(readOnly = true)
    public AgentUserPreferences getDefaultUserPreferences() {
        return userRepository.findByAuthProviderAndExternalSubject(DEFAULT_AUTH_PROVIDER, DEFAULT_EXTERNAL_SUBJECT)
                .flatMap(user -> preferenceRepository.findByUserId(user.getId()))
                .map(this::toAgentPreferences)
                .orElse(AgentUserPreferences.empty());
    }

    @Transactional
    public AgentUserPreferences updateDefaultUserPreferences(UserPreferenceRequest request) {
        AgentUser user = ensureDefaultUser();
        OffsetDateTime now = OffsetDateTime.now();
        AgentUserPreference preference = preferenceRepository.findByUserId(user.getId())
                .orElseGet(() -> new AgentUserPreference(
                        idGenerator.newId(),
                        user.getId(),
                        "zh-CN",
                        null,
                        null,
                        null,
                        null,
                        "[]",
                        "[]",
                        "[]",
                        null,
                        "USER_PROVIDED",
                        BigDecimal.ONE.setScale(4),
                        true,
                        now,
                        now
                ));
        preference.update(
                blankToDefault(request.preferredLocale(), "zh-CN"),
                blankToNull(request.defaultMarket()),
                blankToNull(request.riskTolerance()),
                blankToNull(request.timeHorizon()),
                blankToNull(request.reportStyle()),
                toJson(listOrEmpty(request.preferredSectors())),
                toJson(listOrEmpty(request.excludedSectors())),
                toJson(listOrEmpty(request.preferredAssets())),
                blankToNull(request.notes()),
                request.enabled() == null || request.enabled(),
                now
        );
        return toAgentPreferences(preferenceRepository.save(preference));
    }

    private AgentUser ensureDefaultUser() {
        return userRepository.findByAuthProviderAndExternalSubject(DEFAULT_AUTH_PROVIDER, DEFAULT_EXTERNAL_SUBJECT)
                .orElseGet(() -> {
                    OffsetDateTime now = OffsetDateTime.now();
                    return userRepository.save(new AgentUser(
                            idGenerator.newId(),
                            "默认用户",
                            DEFAULT_AUTH_PROVIDER,
                            DEFAULT_EXTERNAL_SUBJECT,
                            "ACTIVE",
                            now,
                            now
                    ));
                });
    }

    private AgentUserPreferences toAgentPreferences(AgentUserPreference preference) {
        return new AgentUserPreferences(
                preference.getPreferredLocale(),
                valueOrEmpty(preference.getDefaultMarket()),
                valueOrEmpty(preference.getRiskTolerance()),
                valueOrEmpty(preference.getTimeHorizon()),
                valueOrEmpty(preference.getReportStyle()),
                parseList(preference.getPreferredSectors()),
                parseList(preference.getExcludedSectors()),
                parseList(preference.getPreferredAssets()),
                valueOrEmpty(preference.getNotes()),
                preference.isEnabled()
        );
    }

    private List<String> parseList(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<>() {
            });
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private String toJson(List<String> values) {
        try {
            return objectMapper.writeValueAsString(values);
        } catch (JsonProcessingException exception) {
            return "[]";
        }
    }

    private List<String> listOrEmpty(List<String> values) {
        if (values == null) {
            return List.of();
        }
        return values.stream()
                .filter(value -> value != null && !value.isBlank())
                .map(String::trim)
                .limit(20)
                .toList();
    }

    private String blankToDefault(String value, String fallback) {
        String normalized = blankToNull(value);
        return normalized == null ? fallback : normalized;
    }

    private String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private String valueOrEmpty(String value) {
        return value == null ? "" : value;
    }
}
