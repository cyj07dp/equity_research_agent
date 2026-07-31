package com.yjc.equityresearch.repository;

import com.yjc.equityresearch.domain.ResearchMessage;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ResearchMessageRepository extends JpaRepository<ResearchMessage, UUID> {
    List<ResearchMessage> findByConversationIdOrderByCreatedAtAsc(UUID conversationId);
}
