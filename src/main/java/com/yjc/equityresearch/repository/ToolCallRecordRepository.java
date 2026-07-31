package com.yjc.equityresearch.repository;

import com.yjc.equityresearch.domain.ToolCallRecord;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ToolCallRecordRepository extends JpaRepository<ToolCallRecord, UUID> {
    List<ToolCallRecord> findByJobIdOrderByStartedAtAsc(UUID jobId);
}
