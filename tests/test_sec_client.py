import httpx
import respx

from company_intel.ingest.sec_client import SEC_TICKERS_URL, SECClient


@respx.mock
def test_ticker_to_cik_pads_to_ten_digits(tmp_path, fixtures_dir):
    data = (fixtures_dir / "company_tickers.json").read_text()
    respx.get(SEC_TICKERS_URL).mock(return_value=httpx.Response(200, text=data))

    client = SECClient("Tester test@example.com", tmp_path)

    assert client.ticker_to_cik("mu") == "0000723125"
    cik = client.ticker_to_cik("STX")
    assert len(cik) == 10 and cik.isdigit()


@respx.mock
def test_download_filing_uses_disk_cache(tmp_path):
    url = "https://www.sec.gov/Archives/edgar/data/1/2/x.htm"
    route = respx.get(url).mock(
        return_value=httpx.Response(200, text="<html>hi</html>")
    )

    client = SECClient("Tester test@example.com", tmp_path)

    assert client.download_filing(url) == "<html>hi</html>"
    assert client.download_filing(url) == "<html>hi</html>"  # second hit cached
    assert route.call_count == 1


@respx.mock
def test_latest_filing_picks_newest_matching_form(tmp_path):
    cik = "0000723125"
    submissions = {
        "name": "Micron Technology Inc",
        "filings": {
            "recent": {
                "accessionNumber": ["0000723125-24-000080", "0000723125-24-000050"],
                "form": ["8-K", "10-K"],
                "filingDate": ["2024-10-01", "2024-09-20"],
                "reportDate": ["2024-08-29", "2024-08-29"],
                "primaryDocument": ["a8k.htm", "mu-20240829.htm"],
            }
        },
    }
    respx.get(f"https://data.sec.gov/submissions/CIK{cik}.json").mock(
        return_value=httpx.Response(200, json=submissions)
    )

    client = SECClient("Tester test@example.com", tmp_path)
    filing = client.latest_filing(cik)

    assert filing is not None
    assert filing.form == "10-K"
    assert filing.accession_no == "0000723125-24-000050"
    assert "723125/000072312524000050/mu-20240829.htm" in filing.primary_doc_url
    assert filing.filed_date is not None and filing.filed_date.year == 2024
