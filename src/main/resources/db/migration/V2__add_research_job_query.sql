ALTER TABLE research_jobs
    ADD COLUMN query TEXT;

UPDATE research_jobs
    SET query = ticker
    WHERE query IS NULL;

ALTER TABLE research_jobs
    ALTER COLUMN query SET NOT NULL;
