-- Company Intel schema (Milestone 1). Idempotent: safe to re-run.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS companies (
    cik     TEXT PRIMARY KEY,
    ticker  TEXT NOT NULL,
    name    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies (ticker);

CREATE TABLE IF NOT EXISTS filings (
    accession_no TEXT PRIMARY KEY,
    cik          TEXT NOT NULL REFERENCES companies (cik),
    form         TEXT NOT NULL,
    filed_date   DATE,
    period       TEXT,
    url          TEXT
);
CREATE INDEX IF NOT EXISTS idx_filings_cik ON filings (cik);

CREATE TABLE IF NOT EXISTS filing_sections (
    id           BIGSERIAL PRIMARY KEY,
    accession_no TEXT NOT NULL REFERENCES filings (accession_no),
    item         TEXT NOT NULL,
    text         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sections_accession ON filing_sections (accession_no);

CREATE TABLE IF NOT EXISTS financial_facts (
    cik           TEXT NOT NULL REFERENCES companies (cik),
    concept       TEXT NOT NULL,
    unit          TEXT NOT NULL,
    value         DOUBLE PRECISION NOT NULL,
    period_end    DATE NOT NULL,
    fiscal_year   INT,
    fiscal_period TEXT,
    form          TEXT NOT NULL,
    filed         DATE,
    PRIMARY KEY (cik, concept, period_end, form)
);
CREATE INDEX IF NOT EXISTS idx_facts_cik_concept ON financial_facts (cik, concept);

-- Read-only role for agents (used from Milestone 3). Login/password are granted
-- separately by the operator; this role only ever gets SELECT.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'intel_ro') THEN
        CREATE ROLE intel_ro NOLOGIN;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA public TO intel_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO intel_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO intel_ro;

-- Milestone 2 (blocked on Decision D3 — the embedding model sets the vector
-- dimension). Uncomment and set the dimension once D3 is decided:
--
-- CREATE TABLE IF NOT EXISTS chunks (
--     id           BIGSERIAL PRIMARY KEY,
--     accession_no TEXT REFERENCES filings (accession_no),
--     item         TEXT,
--     chunk_idx    INT,
--     text         TEXT,
--     embedding    vector(1536)
-- );
