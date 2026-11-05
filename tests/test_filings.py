from company_intel.ingest.filings import extract_sections, html_to_text


def test_html_to_text_strips_markup(fixtures_dir):
    html = (fixtures_dir / "filing_sample.html").read_text()
    text = html_to_text(html)
    assert "hard drives" in text
    assert "<p>" not in text


def test_extract_sections_10k(fixtures_dir):
    html = (fixtures_dir / "filing_sample.html").read_text()
    sections = {s.item: s.text for s in extract_sections(html, "10-K")}

    assert set(sections) == {"1", "1A", "7"}
    assert "hard drives" in sections["1"]
    assert "Competition" in sections["1A"]
    assert "Revenue increased" in sections["7"]

    # Item 1 must stop before Item 1A, and 1A before Item 2.
    assert "Risk Factors" not in sections["1"]
    assert "Properties" not in sections["1A"]


def test_extract_sections_item_1_not_confused_with_1a(fixtures_dir):
    html = (fixtures_dir / "filing_sample.html").read_text()
    sections = {s.item: s.text for s in extract_sections(html, "10-K")}
    # "Business" belongs to Item 1, not leaked from the 1A boundary logic.
    assert "Business" in sections["1"]
