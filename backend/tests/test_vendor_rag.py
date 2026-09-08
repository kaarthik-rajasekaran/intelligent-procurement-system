import pytest
import uuid
from app.core.database import SessionLocal, Base, engine
from app.models.entities import Vendor, Item, VendorReview, VendorReviewEmbedding
from app.intelligence.vendor_rag import (
    get_vendor_recommendations_rag,
    prepare_quantitative_evidence,
    _classify_evidence_confidence,
    _validate_llm_output
)
from app.intelligence import recommendation_cache
from app.ai.provider import MockLocalLLMProvider

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_evidence_confidence_classification():
    """Test deterministic confidence classification rules."""
    assert _classify_evidence_confidence(0, False, None) == "LOW"
    assert _classify_evidence_confidence(1, False, "Q4-2024") == "LOW"
    assert _classify_evidence_confidence(2, False, "Q1-2026") == "MEDIUM"
    assert _classify_evidence_confidence(1, True, "Q1-2026") == "MEDIUM"
    assert _classify_evidence_confidence(4, True, "Q2-2026") == "HIGH"

def test_anti_hallucination_filter():
    """Test that hallucinated vendor IDs from LLM output are stripped."""
    valid_id_1 = str(uuid.uuid4())
    valid_id_2 = str(uuid.uuid4())
    fake_id = str(uuid.uuid4())

    llm_output = {
        "recommendations": [
            {
                "vendor_id": valid_id_1,
                "vendor_name": "Real Vendor 1",
                "rank": 1,
                "recommendation_status": "RECOMMENDED",
                "reasoning_summary": "Great track record.",
                "key_strengths": ["Fast delivery"],
                "potential_risks": []
            },
            {
                "vendor_id": fake_id,
                "vendor_name": "Hallucinated Vendor",
                "rank": 2,
                "recommendation_status": "RECOMMENDED",
                "reasoning_summary": "Invented by LLM.",
                "key_strengths": [],
                "potential_risks": []
            },
            {
                "vendor_id": valid_id_2,
                "vendor_name": "Real Vendor 2",
                "rank": 3,
                "recommendation_status": "ACCEPTABLE",
                "reasoning_summary": "Solid option.",
                "key_strengths": [],
                "potential_risks": []
            }
        ]
    }

    validated = _validate_llm_output(llm_output, [valid_id_1, valid_id_2])
    assert len(validated) == 2
    assert all(r["vendor_id"] in [valid_id_1, valid_id_2] for r in validated)
    assert not any(r["vendor_id"] == fake_id for r in validated)

def test_recommendation_cache():
    """Test recommendation caching and invalidation."""
    item_id = uuid.uuid4()
    recommendation_cache.clear_all()
    assert recommendation_cache.get_cached(item_id, 10) is None

    # Set mock cache
    recommendation_cache.set_cached(item_id, 10, [])
    assert recommendation_cache.get_cached(item_id, 10) == []
    # Similar quantity within bracket should hit
    assert recommendation_cache.get_cached(item_id, 12) == []

    # Invalidate
    recommendation_cache.invalidate(item_id)
    assert recommendation_cache.get_cached(item_id, 10) is None

def test_rag_recommendation_with_mock_llm(db):
    """Test full RAG pipeline with mock local LLM (fallback mode)."""
    item = db.query(Item).first()
    assert item is not None

    mock_llm = MockLocalLLMProvider()
    recs = get_vendor_recommendations_rag(
        db=db,
        item_id=item.id,
        quantity=5.0,
        llm_provider=mock_llm
    )
    assert len(recs) > 0
    for r in recs:
        assert r.rank >= 1
        assert r.vendor_id is not None
        assert r.vendor_name is not None
        assert r.recommendation_status in ["RECOMMENDED", "ACCEPTABLE", "CAUTION"]
        assert r.evidence_confidence in ["HIGH", "MEDIUM", "LOW"]
        assert r.analytical_score > 0
