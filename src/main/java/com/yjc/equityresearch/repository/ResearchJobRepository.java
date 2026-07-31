package com.yjc.equityresearch.repository;

import com.yjc.equityresearch.domain.ResearchJob;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ResearchJobRepository extends JpaRepository<ResearchJob, UUID> {
}
