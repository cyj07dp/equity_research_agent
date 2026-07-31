package com.yjc.equityresearch.application;

import com.yjc.equityresearch.domain.ResearchReport;
import com.yjc.equityresearch.repository.ResearchReportRepository;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class ReportService {
    private final ResearchReportRepository reportRepository;

    public ReportService(ResearchReportRepository reportRepository) {
        this.reportRepository = reportRepository;
    }

    @Transactional(readOnly = true)
    public ResearchReport getReport(UUID reportId) {
        return reportRepository.findById(reportId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Research report not found"));
    }
}
