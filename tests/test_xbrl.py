import json

from company_intel.ingest.xbrl import extract_facts


def test_extract_facts_annual_only_and_dedup(fixtures_dir):
    data = json.loads((fixtures_dir / "companyfacts_sample.json").read_text())
    facts = extract_facts(data, "0000723125")

    # Only full-year facts are kept (the 10-Q Q3 entry is filtered out).
    assert facts and all(f.fiscal_period == "FY" for f in facts)
    assert all(f.form == "10-K" for f in facts)

    labels = {f.concept for f in facts}
    assert "Revenues" in labels
    assert "ResearchAndDevelopmentExpense" in labels

    revenues = {f.fiscal_year: f for f in facts if f.concept == "Revenues"}
    assert set(revenues) == {2023, 2022}

    # For the duplicated 2023 revenue, the most recently filed value wins.
    assert revenues[2023].value == 15540000000.0
    assert revenues[2023].cik == "0000723125"
    assert revenues[2023].unit == "USD"


def test_extract_facts_empty_when_no_facts():
    assert extract_facts({"facts": {}}, "0000723125") == []
