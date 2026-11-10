from datetime import date

from company_intel.retrieval.hybrid import reciprocal_rank_fusion
from company_intel.retrieval.types import Hit


def _hit(chunk_id: int) -> Hit:
    return Hit(
        chunk_id=chunk_id,
        accession_no="ACC1",
        item="1A",
        chunk_idx=0,
        text=f"text {chunk_id}",
        score=0.0,
        ticker="STX",
        form="10-K",
        filed_date=date(2024, 1, 1),
    )


def test_rrf_unions_and_ranks_by_both_lists():
    dense = [_hit(1), _hit(2), _hit(3)]
    lexical = [_hit(2), _hit(1), _hit(4)]

    fused = reciprocal_rank_fusion([dense, lexical])
    ids = [h.chunk_id for h in fused]

    # Union of both lists, no duplicates.
    assert set(ids) == {1, 2, 3, 4}
    assert len(ids) == 4
    # 1 and 2 rank high in both -> they come before 3 and 4.
    assert set(ids[:2]) == {1, 2}
    assert set(ids[2:]) == {3, 4}
    # Fused score replaces the raw score and is positive.
    assert all(h.score > 0 for h in fused)


def test_rrf_single_list_preserves_order():
    fused = reciprocal_rank_fusion([[_hit(5), _hit(6), _hit(7)]])
    assert [h.chunk_id for h in fused] == [5, 6, 7]
