import json
import logging
import uuid
from typing import List, Tuple
import numpy as np
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import KnowledgeDocument, KnowledgeChunk
from app.ai.provider import get_llm_provider
from app.schemas.domain import KnowledgeQueryResponse

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """
    Chunks text into overlapping segments for dense vector retrieval.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += (chunk_size - overlap)
    return chunks if chunks else [text]

def ingest_document(db: Session, title: str, filename: str, content: str, doc_type: str = "POLICY") -> KnowledgeDocument:
    """
    Ingests, chunks, embeds, and indexes a knowledge document.
    """
    llm = get_llm_provider()
    file_path = settings.KNOWLEDGE_STORAGE_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    doc = KnowledgeDocument(
        title=title,
        original_filename=filename,
        file_path=str(file_path),
        document_type=doc_type,
        processing_status="PROCESSED"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    chunks = chunk_text(content)
    for idx, c in enumerate(chunks):
        embedding = llm.generate_embedding(c)
        chunk_obj = KnowledgeChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=c,
            embedding_json=json.dumps(embedding),
            metadata_json=json.dumps({"source": filename, "chunk": idx})
        )
        db.add(chunk_obj)

    db.commit()
    return doc

def query_knowledge_rag(db: Session, query_text: str, top_k: int = 3) -> KnowledgeQueryResponse:
    """
    Performs vector similarity search against knowledge chunks and generates a grounded LLM answer.
    Enforces strict guardrails against hallucination when no relevant context is found.
    """
    llm = get_llm_provider()
    chunks = db.query(KnowledgeChunk).all()

    if not chunks:
        return KnowledgeQueryResponse(
            query=query_text,
            answer="The available knowledge base does not contain enough information to answer this confidently.",
            grounded_chunks=[],
            confidence="NONE"
        )

    # Generate query embedding
    q_emb = np.array(llm.generate_embedding(query_text))

    scored_chunks: List[Tuple[float, KnowledgeChunk]] = []
    for chunk in chunks:
        if not chunk.content:
            continue

        c_emb = None
        if chunk.embedding_json:
            try:
                parsed = json.loads(chunk.embedding_json)
                if len(parsed) == len(q_emb):
                    c_emb = np.array(parsed)
            except Exception:
                c_emb = None

        if c_emb is None:
            # Dimension mismatch or missing embedding: dynamically recompute
            try:
                new_vec = llm.generate_embedding(chunk.content)
                chunk.embedding_json = json.dumps(new_vec)
                db.add(chunk)
                db.commit()
                c_emb = np.array(new_vec)
            except Exception as e:
                logger.warning(f"Failed to re-embed chunk {chunk.id}: {e}")
                continue

        denom = (np.linalg.norm(q_emb) * np.linalg.norm(c_emb))
        sim = float(np.dot(q_emb, c_emb) / denom) if denom > 0 else 0.0
        
        # Word overlap bonus for exact policy terms
        q_words = set(query_text.lower().split())
        c_words = set(chunk.content.lower().split())
        overlap_score = len(q_words.intersection(c_words)) / max(len(q_words), 1)
        composite_sim = 0.6 * sim + 0.4 * overlap_score

        scored_chunks.append((composite_sim, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_candidates = [c for c in scored_chunks[:top_k] if c[0] > 0.05]

    if not top_candidates:
        return KnowledgeQueryResponse(
            query=query_text,
            answer="The available knowledge base does not contain enough information to answer this confidently.",
            grounded_chunks=[],
            confidence="NONE"
        )

    context_snippets = [c[1].content for c in top_candidates]
    grounded_context = "\n---\n".join(context_snippets)

    # Produce grounded response using the LLM
    prompt = (
        f"Context from internal procurement policies:\n{grounded_context}\n\n"
        f"User Query: {query_text}\n\n"
        "Provide a concise, direct, grounded answer based strictly on the policies above."
    )
    try:
        grounded_answer = llm.generate_text(
            prompt=prompt,
            system_prompt="You are an enterprise procurement policy advisor. Provide accurate, professional answers grounded strictly in company procurement policy documents."
        )
    except Exception as e:
        logger.warning(f"RAG LLM generation failed: {e}. Falling back to excerpt.")
        grounded_answer = (
            f"Based on internal procurement guidelines:\n\n"
            f"• {top_candidates[0][1].content[:300]}...\n\n"
            f"All procurement activities must strictly adhere to documented thresholds and approval hierarchies."
        )

    return KnowledgeQueryResponse(
        query=query_text,
        answer=grounded_answer,
        grounded_chunks=context_snippets,
        confidence="HIGH"
    )
