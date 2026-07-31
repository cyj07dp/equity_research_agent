package com.yjc.equityresearch.api;

import com.yjc.equityresearch.api.dto.ResearchReportResponse;
import com.yjc.equityresearch.application.ReportService;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/reports")
public class ReportController {
    private final ReportService reportService;

    public ReportController(ReportService reportService) {
        this.reportService = reportService;
    }

    @GetMapping("/{reportId}")
    public ResearchReportResponse getReport(@PathVariable UUID reportId) {
        return ResearchReportResponse.from(reportService.getReport(reportId));
    }
}
