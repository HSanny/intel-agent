"""Parse SEC XBRL ``companyfacts`` into a small set of normalized financial facts.

Handles both ``us-gaap`` (10-K filers) and ``ifrs-full`` (20-F filers such as
Grab and Sea), mapping each source concept to a shared normalized label.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

# Source concept -> normalized label.
US_GAAP_CONCEPTS: dict[str, str] = {
    "Revenues": "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "Revenues",
    "ResearchAndDevelopmentExpense": "ResearchAndDevelopmentExpense",
    "GrossProfit": "GrossProfit",
    "OperatingIncomeLoss": "OperatingIncomeLoss",
    "NetIncomeLoss": "NetIncomeLoss",
}

IFRS_CONCEPTS: dict[str, str] = {
    "Revenue": "Revenues",
    "RevenueFromContractsWithCustomers": "Revenues",
    "ResearchAndDevelopmentExpense": "ResearchAndDevelopmentExpense",
    "GrossProfit": "GrossProfit",
    "ProfitLossFromOperatingActivities": "OperatingIncomeLoss",
    "ProfitLoss": "NetIncomeLoss",
}

TAXONOMIES: dict[str, dict[str, str]] = {
    "us-gaap": US_GAAP_CONCEPTS,
    "ifrs-full": IFRS_CONCEPTS,
}

# Annual filing forms whose full-year figures we keep.
ANNUAL_FORMS = {"10-K", "20-F", "10-K/A", "20-F/A"}


@dataclass
class Fact:
    """One normalized annual financial figure."""

    cik: str
    concept: str
    unit: str
    value: float
    period_end: date | None
    fiscal_year: int
    fiscal_period: str
    form: str
    filed: date | None


def extract_facts(company_facts: dict, cik: str) -> list[Fact]:
    """Extract the concept shortlist as annual (``fp == "FY"``) facts.

    When the same (concept, period_end, form) appears in several filings, the
    most recently filed value wins.
    """
    cik10 = str(int(cik)).zfill(10)
    facts_root = company_facts.get("facts", {})
    best: dict[tuple, Fact] = {}

    for taxonomy, concept_map in TAXONOMIES.items():
        tax = facts_root.get(taxonomy, {})
        for source_concept, label in concept_map.items():
            node = tax.get(source_concept)
            if not node:
                continue
            for unit, entries in node.get("units", {}).items():
                for entry in entries:
                    fact = _entry_to_fact(entry, label, unit, cik10)
                    if fact is None:
                        continue
                    key = (fact.concept, fact.period_end, fact.form)
                    prev = best.get(key)
                    if prev is None or _is_newer(fact, prev):
                        best[key] = fact

    return list(best.values())


def _entry_to_fact(entry: dict, label: str, unit: str, cik10: str) -> Fact | None:
    if entry.get("fp") != "FY":
        return None
    if entry.get("form") not in ANNUAL_FORMS:
        return None
    value = entry.get("val")
    end = entry.get("end")
    fiscal_year = entry.get("fy")
    if value is None or end is None or fiscal_year is None:
        return None
    return Fact(
        cik=cik10,
        concept=label,
        unit=unit,
        value=float(value),
        period_end=_parse_date(end),
        fiscal_year=int(fiscal_year),
        fiscal_period="FY",
        form=entry["form"],
        filed=_parse_date(entry.get("filed")),
    )


def _is_newer(candidate: Fact, current: Fact) -> bool:
    if candidate.filed is None:
        return False
    if current.filed is None:
        return True
    return candidate.filed > current.filed


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()
