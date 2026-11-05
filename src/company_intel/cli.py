"""Command-line interface: init-db, ingest, facts."""

from __future__ import annotations

from pathlib import Path

import typer

from .config import get_settings
from .ingest.filings import ingest_company
from .ingest.sec_client import SECClient
from .store.db import DB

app = typer.Typer(add_completion=False, help="Company Intel — SEC ingest CLI")

SCHEMA_PATH = Path(__file__).parent / "store" / "schema.sql"


def _client() -> SECClient:
    settings = get_settings()
    return SECClient(
        settings.sec_user_agent, settings.sec_cache_dir, settings.sec_rate_limit
    )


def _db() -> DB:
    return DB(get_settings().database_url)


@app.command("init-db")
def init_db() -> None:
    """Create tables and the read-only role."""
    _db().init_schema(SCHEMA_PATH)
    typer.echo("schema applied")


@app.command()
def ingest(
    tickers: list[str] = typer.Argument(
        ..., help="Ticker symbols, e.g. STX MU GRAB SE"
    ),
) -> None:
    """Ingest filings, sections and financial facts for each ticker."""
    client = _client()
    db = _db()
    for ticker in tickers:
        typer.echo(f"ingesting {ticker} ...")
        try:
            ingest_company(client, db, ticker)
            typer.echo(f"  done {ticker}")
        except Exception as exc:  # noqa: BLE001 - report and continue
            typer.echo(f"  error {ticker}: {exc}")


@app.command()
def facts(
    ticker: str,
    years: int = typer.Option(3, "--years", "-y", help="Number of fiscal years"),
) -> None:
    """Print the last N fiscal years of revenue and R&D."""
    rows = _db().revenue_rnd_table(ticker, years)
    if not rows:
        typer.echo(f"no facts for {ticker}")
        raise typer.Exit(1)

    header = f"{'FY':<6}{'Revenue':>20}{'R&D':>20}  unit"
    typer.echo(header)
    typer.echo("-" * len(header))
    for row in rows:
        typer.echo(
            f"{row['fiscal_year']:<6}"
            f"{_fmt(row.get('Revenues')):>20}"
            f"{_fmt(row.get('ResearchAndDevelopmentExpense')):>20}"
            f"  {row.get('unit', '')}"
        )


def _fmt(value: float | None) -> str:
    return f"{value:,.0f}" if value is not None else "—"


if __name__ == "__main__":
    app()
