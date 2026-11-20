"""Retrieval-augmented answers over a classroom's own notes, stored as pgvector embeddings."""
import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import ai
from .db import NoteChunk

CHUNK_WORDS = 120
OVERLAP_WORDS = 30
TOP_K = 4


def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    """Split into overlapping word windows so an idea cut at a boundary still appears whole once."""
    words = re.sub(r"\s+", " ", text).strip().split(" ")
    if not words or words == [""]:
        return []
    step = max(size - overlap, 1)
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
    return chunks


def index_notes(db: Session, classroom_id: int, text: str) -> int:
    chunks = chunk_text(text)
    db.execute(delete(NoteChunk).where(NoteChunk.classroom_id == classroom_id))
    if chunks:
        vectors = ai.embed(chunks, task="RETRIEVAL_DOCUMENT")
        db.add_all(NoteChunk(classroom_id=classroom_id, position=i, text=c, embedding=v)
                   for i, (c, v) in enumerate(zip(chunks, vectors)))
    db.commit()
    return len(chunks)


def search(db: Session, classroom_id: int, question: str, k: int = TOP_K) -> list[tuple[NoteChunk, float]]:
    qvec = ai.embed([question], task="RETRIEVAL_QUERY")[0]
    distance = NoteChunk.embedding.cosine_distance(qvec)
    rows = db.execute(select(NoteChunk, distance.label("d"))
                      .where(NoteChunk.classroom_id == classroom_id)
                      .order_by(distance).limit(k)).all()
    return [(chunk, round(1 - float(d), 3)) for chunk, d in rows]
