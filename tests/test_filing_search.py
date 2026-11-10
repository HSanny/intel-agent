"""filing_search end-to-end with fakes — no model, no database required."""

from datetime import date

from company_intel.retrieval.rerank import NoopReranker
from company_intel.tools.filing_search import filing_search

ROWS = [
    {
        "id": 1, "accession_no": "ACC1", "item": "1A", "chunk_idx": 0,
        "text": "Demand for hard drives may decline and competition is intense.",
        "ticker": "STX", "form": "10-K", "filed_date": date(2024, 8, 1),
    },
    {
        "id": 2, "accession_no": "ACC1", "item": "1", "chunk_idx": 0,
        "text": "We manufacture mass-capacity storage and data devices globally.",
        "ticker": "STX", "form": "10-K", "filed_date": date(2024, 8, 1),
    },
    {
        "id": 3, "accession_no": "ACC2", "item": "1A", "chunk_idx": 0,
        "text": "Currency fluctuations are a risk to our reported revenue.",
        "ticker": "MU", "form": "10-K", "filed_date": date(2024, 9, 1),
    },
]


class FakeProvider:
    name = "fake"
    dim = 4

    def embed(self, texts):
        return [[0.0, 0.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [0.0, 0.0, 0.0, 0.0]


class FakeDB:
    def vector_search(self, embedding, k=20, ticker=None):
        rows = [r for r in ROWS if ticker is None or r["ticker"] == ticker]
        return [dict(r, score=1.0 - 0.1 * i) for i, r in enumerate(rows)][:k]

    def fetch_chunks(self, ticker=None):
        return [r for r in ROWS if ticker is None or r["ticker"] == ticker]


def test_filing_search_returns_cited_results():
    results = filing_search(
        "risk factors for storage demand",
        ticker="STX",
        top_k=2,
        db=FakeDB(),
        provider=FakeProvider(),
        reranker=NoopReranker(),
    )

    assert 1 <= len(results) <= 2
    top = results[0]
    assert top.text
    assert top.citation.ticker == "STX"
    assert top.citation.item in {"1", "1A"}
    assert top.citation.form == "10-K"
    assert top.citation.filed_date == date(2024, 8, 1)
    # The ticker filter kept MU out.
    assert all(r.citation.ticker == "STX" for r in results)


def test_filing_search_ticker_filter_isolates_company():
    results = filing_search(
        "currency revenue risk",
        ticker="MU",
        top_k=5,
        db=FakeDB(),
        provider=FakeProvider(),
        reranker=NoopReranker(),
    )
    assert results
    assert all(r.citation.ticker == "MU" for r in results)
