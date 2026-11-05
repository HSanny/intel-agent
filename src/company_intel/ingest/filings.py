"""Extract filing item sections (10-K / 20-F) from HTML into plain text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from selectolax.lexbor import LexborHTMLParser

from .xbrl import extract_facts

if TYPE_CHECKING:  # avoid runtime import cycles
    from ..store.db import DB
    from .sec_client import SECClient

# Items we extract per form.
TENK_ITEMS = ("1", "1A", "7")
TWENTYF_ITEMS = ("4", "3D", "5")

# Ordered item sequences, used to find section boundaries.
_TENK_SEQUENCE = ["1", "1A", "1B", "2", "3", "4", "5", "6", "7", "7A", "8", "9"]
_TWENTYF_SEQUENCE = [
    "1", "2", "3", "3A", "3B", "3C", "3D", "4", "4A", "5", "6", "7", "8",
]


@dataclass
class Section:
    """One extracted filing item section."""

    accession_no: str
    item: str
    text: str


def html_to_text(html: str) -> str:
    """Convert filing HTML to whitespace-normalized plain text."""
    tree = LexborHTMLParser(html)
    for node in tree.css("script, style"):
        node.decompose()
    root = tree.body or tree.root
    text = root.text(separator="\n") if root else ""
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _item_pattern(item: str) -> re.Pattern[str]:
    # Matches "Item 1A", "ITEM 1A.", etc. Word boundaries keep "1" from
    # matching inside "1A".
    return re.compile(rf"\bitem\s+{re.escape(item)}\b\.?", re.IGNORECASE)


def extract_sections(html: str, form: str) -> list[Section]:
    """Split filing text into the item sections we care about.

    Uses the last occurrence of each item heading (filings begin with a table
    of contents that repeats the item names) and slices each target item up to
    the next heading that follows it.
    """
    text = html_to_text(html)
    items = TENK_ITEMS if form.startswith("10-K") else TWENTYF_ITEMS
    sequence = _TENK_SEQUENCE if form.startswith("10-K") else _TWENTYF_SEQUENCE

    positions: dict[str, int] = {}
    for item in sequence:
        matches = list(_item_pattern(item).finditer(text))
        if matches:
            positions[item] = matches[-1].start()

    sections: list[Section] = []
    for item in items:
        if item not in positions:
            continue
        start = positions[item]
        later = [pos for pos in positions.values() if pos > start]
        end = min(later) if later else len(text)
        body = text[start:end].strip()
        if body:
            sections.append(Section(accession_no="", item=item, text=body))
    return sections


def ingest_company(client: SECClient, db: DB, ticker: str) -> None:
    """End-to-end ingest for a single ticker: company, facts, filing, sections."""
    cik = client.ticker_to_cik(ticker)
    submissions = client.get_submissions(cik)
    name = submissions.get("name") or ticker.upper()
    db.upsert_company(cik, ticker.upper(), name)

    facts = extract_facts(client.get_company_facts(cik), cik)
    db.upsert_facts(facts)

    filing = client.latest_filing(cik)
    if filing is None:
        return
    db.upsert_filing(filing)

    html = client.download_filing(filing.primary_doc_url)
    sections = extract_sections(html, filing.form)
    for section in sections:
        section.accession_no = filing.accession_no
    db.insert_sections(sections)
