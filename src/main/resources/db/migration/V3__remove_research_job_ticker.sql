DROP INDEX IF EXISTS idx_research_jobs_ticker;

ALTER TABLE research_jobs
    DROP COLUMN ticker;
