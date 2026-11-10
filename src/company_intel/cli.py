"""Command-line interface: init-db, ingest, facts."""

from __future__ import annotations

from pathlib import Path

import typer

from .config import get_settings
from .embeddings.base import get_provider
from .ingest.chunk_embed import embed_and_store
from .ingest.filings import ingest_company
from .ingest.sec_client import SECClient
from .retrieval.rerank import get_reranker
from .store.db import DB
from .tools.filing_search import filing_search

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


@app.command()
def embed(
    tickers: list[str] = typer.Argument(
        ..., help="Ticker symbols whose filings to chunk + embed"
    ),
) -> None:
    """Chunk and embed stored filings into the chunks table."""
    settings = get_settings()
    db = _db()
    provider = get_provider()
    for ticker in tickers:
        accessions = db.accessions_for_ticker(ticker)
        if not accessions:
            typer.echo(f"{ticker}: no filings (run ingest first)")
            continue
        for accession in accessions:
            n = embed_and_store(
                db,
                provider,
                accession,
                target_words=settings.chunk_target_words,
                overlap=settings.chunk_overlap_words,
                batch_size=settings.embed_batch_size,
            )
            typer.echo(f"{ticker} {accession}: {n} chunks embedded")


@app.command()
def search(
    query: str,
    ticker: str = typer.Option(None, "--ticker", "-t", help="Limit to one ticker"),
    k: int = typer.Option(5, "--k", help="Number of passages"),
) -> None:
    """Search filings and print passages with citations."""
    settings = get_settings()
    db = _db()
    provider = get_provider()
    reranker = get_reranker(settings)

    results = filing_search(query, ticker, k, db=db, provider=provider, reranker=reranker)
    if not results:
        typer.echo("no results (did you run embed?)")
        raise typer.Exit(1)

    for result in results:
        c = result.citation
        typer.echo(
            f"[{c.ticker} {c.form} Item {c.item} · {c.filed_date} · "
            f"{c.accession_no}#{c.chunk_idx}]  score={result.score:.3f}"
        )
        typer.echo(_truncate(result.text, 320))
        typer.echo("")


def _truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + " …"


if __name__ == "__main__":
    app()
