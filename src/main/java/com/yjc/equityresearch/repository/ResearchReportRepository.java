package com.yjc.equityresearch.repository;

import com.yjc.equityresearch.domain.ResearchReport;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ResearchReportRepository extends JpaRepository<ResearchReport, UUID> {
    Optional<ResearchReport> findByJobId(UUID jobId);
}
