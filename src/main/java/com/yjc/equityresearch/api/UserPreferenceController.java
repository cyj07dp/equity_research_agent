package com.yjc.equityresearch.api;

import com.yjc.equityresearch.api.dto.UserPreferenceRequest;
import com.yjc.equityresearch.api.dto.UserPreferenceResponse;
import com.yjc.equityresearch.application.UserPreferenceService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/me/preferences")
public class UserPreferenceController {
    private final UserPreferenceService preferenceService;

    public UserPreferenceController(UserPreferenceService preferenceService) {
        this.preferenceService = preferenceService;
    }

    @GetMapping
    public UserPreferenceResponse getPreferences() {
        return UserPreferenceResponse.from(preferenceService.getDefaultUserPreferences());
    }

    @PutMapping
    public UserPreferenceResponse updatePreferences(@RequestBody UserPreferenceRequest request) {
        return UserPreferenceResponse.from(preferenceService.updateDefaultUserPreferences(request));
    }
}
