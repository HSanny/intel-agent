"""A polite SEC EDGAR client: User-Agent, rate limiting, retries, disk cache."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

DEFAULT_FORMS = ("10-K", "20-F")


@dataclass
class Filing:
    """A single filing's identity and primary document location."""

    accession_no: str
    cik: str
    form: str
    filed_date: date | None
    period: str
    primary_doc_url: str


class _RateLimiter:
    """A simple thread-safe minimum-interval rate limiter."""

    def __init__(self, rate: float) -> None:
        self._min_interval = 1.0 / rate if rate and rate > 0 else 0.0
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self._min_interval:
                time.sleep(self._min_interval - delta)
            self._last = time.monotonic()


class SECClient:
    """Fetches SEC data with caching and polite rate limiting."""

    def __init__(
        self,
        user_agent: str,
        cache_dir: Path | str,
        rate_limit: float = 8.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._limiter = _RateLimiter(rate_limit)
        self._client = client or httpx.Client(
            headers={"User-Agent": user_agent}, timeout=30.0
        )
        self._tickers: dict[str, str] | None = None

    # ------------------------------------------------------------------ #
    # low-level fetch + cache
    # ------------------------------------------------------------------ #
    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        retry=retry_if_exception_type(
            (httpx.TransportError, httpx.HTTPStatusError)
        ),
    )
    def _get(self, url: str) -> httpx.Response:
        self._limiter.wait()
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp

    def _cache_path(self, url: str, suffix: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{key}{suffix}"

    def _cached_text(self, url: str, suffix: str) -> str:
        path = self._cache_path(url, suffix)
        if path.exists():
            return path.read_text(encoding="utf-8")
        text = self._get(url).text
        path.write_text(text, encoding="utf-8")
        return text

    def _cached_json(self, url: str) -> dict:
        return json.loads(self._cached_text(url, ".json"))

    @staticmethod
    def _pad_cik(cik: str | int) -> str:
        return str(int(cik)).zfill(10)

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def ticker_to_cik(self, ticker: str) -> str:
        """Return the zero-padded 10-digit CIK for a ticker symbol."""
        if self._tickers is None:
            data = self._cached_json(SEC_TICKERS_URL)
            self._tickers = {
                row["ticker"].upper(): self._pad_cik(row["cik_str"])
                for row in data.values()
            }
        try:
            return self._tickers[ticker.upper()]
        except KeyError as exc:
            raise KeyError(
                f"ticker not found in SEC company_tickers.json: {ticker}"
            ) from exc

    def get_submissions(self, cik: str) -> dict:
        """Return the EDGAR submissions document for a CIK."""
        return self._cached_json(SUBMISSIONS_URL.format(cik=self._pad_cik(cik)))

    def get_company_facts(self, cik: str) -> dict:
        """Return the XBRL companyfacts document for a CIK."""
        return self._cached_json(COMPANYFACTS_URL.format(cik=self._pad_cik(cik)))

    def download_filing(self, url: str) -> str:
        """Download (and cache) a filing's primary document HTML."""
        return self._cached_text(url, ".html")

    def latest_filing(
        self, cik: str, forms: tuple[str, ...] = DEFAULT_FORMS
    ) -> Filing | None:
        """Return the most recent filing matching one of ``forms``."""
        cik10 = self._pad_cik(cik)
        recent = self.get_submissions(cik10).get("filings", {}).get("recent", {})
        accession = recent.get("accessionNumber", [])
        form_list = recent.get("form", [])
        filed = recent.get("filingDate", [])
        report = recent.get("reportDate", [])
        primary = recent.get("primaryDocument", [])

        # Arrays are ordered newest-first; take the first matching form.
        for i, form in enumerate(form_list):
            if form in forms:
                accn = accession[i]
                accn_nodash = accn.replace("-", "")
                doc = primary[i] if i < len(primary) else ""
                url = (
                    "https://www.sec.gov/Archives/edgar/data/"
                    f"{int(cik10)}/{accn_nodash}/{doc}"
                )
                return Filing(
                    accession_no=accn,
                    cik=cik10,
                    form=form,
                    filed_date=_parse_date(filed[i]) if i < len(filed) else None,
                    period=report[i] if i < len(report) else "",
                    primary_doc_url=url,
                )
        return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()
