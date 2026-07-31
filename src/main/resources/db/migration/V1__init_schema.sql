CREATE TABLE research_jobs (
    id UUID PRIMARY KEY,
    ticker VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    report_id UUID
);

CREATE TABLE research_reports (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL UNIQUE REFERENCES research_jobs(id),
    ticker VARCHAR(16) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    executive_summary TEXT NOT NULL,
    business_overview TEXT NOT NULL,
    market_snapshot TEXT NOT NULL,
    fundamental_highlights TEXT NOT NULL,
    recent_news TEXT NOT NULL,
    bullish_factors TEXT NOT NULL,
    bearish_factors TEXT NOT NULL,
    risk_factors TEXT NOT NULL,
    uncertainties TEXT NOT NULL,
    non_advisory_conclusion TEXT NOT NULL,
    raw_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE research_jobs
    ADD CONSTRAINT fk_research_jobs_report
    FOREIGN KEY (report_id) REFERENCES research_reports(id);

CREATE TABLE tool_call_records (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES research_jobs(id),
    tool_name VARCHAR(128) NOT NULL,
    input_json JSONB NOT NULL,
    output_json JSONB,
    status VARCHAR(32) NOT NULL,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    latency_ms BIGINT NOT NULL
);

CREATE TABLE evidence_items (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES research_jobs(id),
    source_type VARCHAR(64) NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    source_url TEXT,
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL
);

CREATE INDEX idx_research_jobs_ticker ON research_jobs(ticker);
CREATE INDEX idx_research_jobs_status ON research_jobs(status);
CREATE INDEX idx_tool_call_records_job_id ON tool_call_records(job_id);
CREATE INDEX idx_evidence_items_job_id ON evidence_items(job_id);
