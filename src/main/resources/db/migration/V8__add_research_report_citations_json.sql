ALTER TABLE research_reports
    ADD COLUMN citations_json TEXT NOT NULL DEFAULT '[]';
