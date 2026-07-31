ALTER TABLE research_jobs
    DROP CONSTRAINT IF EXISTS fk_research_jobs_report;

TRUNCATE TABLE evidence_items, tool_call_records, research_jobs, research_reports CASCADE;

ALTER TABLE research_reports
    DROP COLUMN ticker,
    DROP COLUMN company_name,
    DROP COLUMN executive_summary,
    DROP COLUMN business_overview,
    DROP COLUMN market_snapshot,
    DROP COLUMN fundamental_highlights,
    DROP COLUMN recent_news,
    DROP COLUMN bullish_factors,
    DROP COLUMN bearish_factors,
    DROP COLUMN risk_factors,
    DROP COLUMN uncertainties,
    DROP COLUMN non_advisory_conclusion;

ALTER TABLE research_reports
    ADD COLUMN subject_name VARCHAR(255) NOT NULL,
    ADD COLUMN subject_type VARCHAR(64) NOT NULL,
    ADD COLUMN subject_identifier VARCHAR(128),
    ADD COLUMN title VARCHAR(255) NOT NULL,
    ADD COLUMN subject_summary TEXT NOT NULL,
    ADD COLUMN question_understanding TEXT NOT NULL,
    ADD COLUMN key_findings TEXT NOT NULL,
    ADD COLUMN opportunities TEXT NOT NULL,
    ADD COLUMN risks TEXT NOT NULL,
    ADD COLUMN evidence_summary TEXT NOT NULL,
    ADD COLUMN uncertainty TEXT NOT NULL,
    ADD COLUMN citations TEXT NOT NULL,
    ADD COLUMN non_advisory_statement TEXT NOT NULL;

CREATE INDEX idx_research_reports_subject_type ON research_reports(subject_type);
CREATE INDEX idx_research_reports_subject_identifier ON research_reports(subject_identifier);

ALTER TABLE research_jobs
    ADD CONSTRAINT fk_research_jobs_report
    FOREIGN KEY (report_id) REFERENCES research_reports(id);
