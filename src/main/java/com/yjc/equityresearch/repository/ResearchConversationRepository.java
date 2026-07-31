package com.yjc.equityresearch.repository;

import com.yjc.equityresearch.domain.ResearchConversation;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ResearchConversationRepository extends JpaRepository<ResearchConversation, UUID> {
    List<ResearchConversation> findTop30ByOrderByUpdatedAtDesc();
}
