package com.yjc.equityresearch.api;

import com.yjc.equityresearch.api.dto.CreateResearchJobRequest;
import com.yjc.equityresearch.api.dto.CreateResearchJobResponse;
import com.yjc.equityresearch.api.dto.ResearchJobResponse;
import com.yjc.equityresearch.api.dto.ResearchTraceResponse;
import com.yjc.equityresearch.api.dto.ToolCallRecordResponse;
import com.yjc.equityresearch.application.ResearchJobService;
import com.yjc.equityresearch.application.ResearchTraceService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/research-jobs")
public class ResearchJobController {
    private final ResearchJobService researchJobService;
    private final ResearchTraceService researchTraceService;

    public ResearchJobController(ResearchJobService researchJobService, ResearchTraceService researchTraceService) {
        this.researchJobService = researchJobService;
        this.researchTraceService = researchTraceService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public CreateResearchJobResponse createJob(@Valid @RequestBody CreateResearchJobRequest request) {
        return CreateResearchJobResponse.from(researchJobService.createJob(request.query()));
    }

    @GetMapping("/{jobId}")
    public ResearchJobResponse getJob(@PathVariable UUID jobId) {
        return ResearchJobResponse.from(researchJobService.getJob(jobId));
    }

    @GetMapping("/{jobId}/tool-calls")
    public List<ToolCallRecordResponse> getToolCalls(@PathVariable UUID jobId) {
        return researchJobService.getToolCalls(jobId).stream()
                .map(ToolCallRecordResponse::from)
                .toList();
    }

    @GetMapping("/{jobId}/trace")
    public ResearchTraceResponse getTrace(@PathVariable UUID jobId) {
        return researchTraceService.getTrace(jobId);
    }
}
