package com.yjc.equityresearch.repository;

import com.yjc.equityresearch.domain.AgentUserPreference;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AgentUserPreferenceRepository extends JpaRepository<AgentUserPreference, UUID> {
    Optional<AgentUserPreference> findByUserId(UUID userId);
}
