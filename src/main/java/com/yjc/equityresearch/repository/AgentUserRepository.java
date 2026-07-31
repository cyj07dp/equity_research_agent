package com.yjc.equityresearch.repository;

import com.yjc.equityresearch.domain.AgentUser;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AgentUserRepository extends JpaRepository<AgentUser, UUID> {
    Optional<AgentUser> findByAuthProviderAndExternalSubject(String authProvider, String externalSubject);
}
