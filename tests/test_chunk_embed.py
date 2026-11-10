from company_intel.ingest.chunk_embed import Chunk, chunk_sections, chunk_text
from company_intel.ingest.filings import Section


def test_chunk_text_windows_overlap():
    text = " ".join(f"w{i}" for i in range(1000))
    chunks = chunk_text(text, target_words=400, overlap=60)

    assert len(chunks) >= 3
    assert all(len(c.split()) <= 400 for c in chunks)
    # The last `overlap` words of a chunk repeat at the start of the next.
    first, second = chunks[0].split(), chunks[1].split()
    assert first[-60:] == second[:60]


def test_chunk_text_edge_cases():
    assert chunk_text("", 400, 60) == []
    assert chunk_text("hello world", 400, 60) == ["hello world"]


def test_chunk_sections_indexes_per_item():
    sections = [
        Section("ACC1", "1", "one two three"),
        Section("ACC1", "7", " ".join(["x"] * 900)),
    ]
    chunks = chunk_sections(sections, target_words=400, overlap=60)

    assert all(isinstance(c, Chunk) for c in chunks)
    item1 = [c for c in chunks if c.item == "1"]
    item7 = [c for c in chunks if c.item == "7"]

    assert len(item1) == 1 and item1[0].chunk_idx == 0
    assert len(item7) >= 2
    assert [c.chunk_idx for c in item7] == list(range(len(item7)))
    assert all(c.accession_no == "ACC1" for c in chunks)
