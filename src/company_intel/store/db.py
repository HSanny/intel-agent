"""Thin Postgres access layer for ingest and simple reads."""

from __future__ import annotations

from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from ..ingest.filings import Section
from ..ingest.sec_client import Filing
from ..ingest.xbrl import Fact


class DB:
    """A minimal data-access object. One connection per operation."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def init_schema(self, schema_path: Path | str) -> None:
        """Apply the schema file (idempotent)."""
        sql = Path(schema_path).read_text(encoding="utf-8")
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            conn.execute(sql)

    def upsert_company(self, cik: str, ticker: str, name: str) -> None:
        with psycopg.connect(self.dsn) as conn:
            conn.execute(
                """
                INSERT INTO companies (cik, ticker, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (cik)
                DO UPDATE SET ticker = EXCLUDED.ticker, name = EXCLUDED.name
                """,
                (cik, ticker, name),
            )

    def upsert_filing(self, filing: Filing) -> None:
        with psycopg.connect(self.dsn) as conn:
            conn.execute(
                """
                INSERT INTO filings (accession_no, cik, form, filed_date, period, url)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (accession_no)
                DO UPDATE SET
                    form = EXCLUDED.form,
                    filed_date = EXCLUDED.filed_date,
                    period = EXCLUDED.period,
                    url = EXCLUDED.url
                """,
                (
                    filing.accession_no,
                    filing.cik,
                    filing.form,
                    filing.filed_date,
                    filing.period,
                    filing.primary_doc_url,
                ),
            )

    def insert_sections(self, sections: list[Section]) -> None:
        if not sections:
            return
        accessions = {s.accession_no for s in sections}
        with psycopg.connect(self.dsn) as conn:
            for accession in accessions:
                conn.execute(
                    "DELETE FROM filing_sections WHERE accession_no = %s",
                    (accession,),
                )
            conn.cursor().executemany(
                "INSERT INTO filing_sections (accession_no, item, text) "
                "VALUES (%s, %s, %s)",
                [(s.accession_no, s.item, s.text) for s in sections],
            )

    def upsert_facts(self, facts: list[Fact]) -> None:
        if not facts:
            return
        with psycopg.connect(self.dsn) as conn:
            conn.cursor().executemany(
                """
                INSERT INTO financial_facts
                    (cik, concept, unit, value, period_end,
                     fiscal_year, fiscal_period, form, filed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cik, concept, period_end, form)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    unit = EXCLUDED.unit,
                    fiscal_year = EXCLUDED.fiscal_year,
                    fiscal_period = EXCLUDED.fiscal_period,
                    filed = EXCLUDED.filed
                """,
                [
                    (
                        f.cik,
                        f.concept,
                        f.unit,
                        f.value,
                        f.period_end,
                        f.fiscal_year,
                        f.fiscal_period,
                        f.form,
                        f.filed,
                    )
                    for f in facts
                ],
            )

    def revenue_rnd_table(self, ticker: str, years: int = 3) -> list[dict]:
        """Return the last ``years`` fiscal years of revenue and R&D."""
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT ff.fiscal_year, ff.concept, ff.value, ff.unit
                FROM financial_facts ff
                JOIN companies c ON c.cik = ff.cik
                WHERE c.ticker = %s
                  AND ff.concept IN ('Revenues', 'ResearchAndDevelopmentExpense')
                ORDER BY ff.fiscal_year DESC
                """,
                (ticker.upper(),),
            ).fetchall()

        by_year: dict[int, dict] = {}
        for row in rows:
            year = by_year.setdefault(
                row["fiscal_year"], {"fiscal_year": row["fiscal_year"]}
            )
            year[row["concept"]] = row["value"]
            year["unit"] = row["unit"]

        ordered = sorted(by_year.values(), key=lambda r: r["fiscal_year"], reverse=True)
        return ordered[:years]
