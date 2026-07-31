package com.yjc.equityresearch.repository;

import com.yjc.equityresearch.domain.EvidenceItem;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EvidenceItemRepository extends JpaRepository<EvidenceItem, UUID> {
    List<EvidenceItem> findByJobId(UUID jobId);
}
