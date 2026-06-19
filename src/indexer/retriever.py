"""
Retriever hybride : dense (pgvector cosine) + sparse (tsvector French) fusionné par RRF.

Usage standalone :
    uv run python src/indexer/retriever.py "remboursement frais"
"""

from __future__ import annotations

import sys

import psycopg

from src.config import settings
from src.llm_factory import get_embeddings

# Reciprocal Rank Fusion constant (60 est la valeur standard de la littérature)
_RRF_K = 60
_CANDIDATE_POOL = 20

_HYBRID_SQL = f"""
WITH dense AS (
    SELECT id, content, source,
           RANK() OVER (ORDER BY embedding <=> %(vec)s::vector) AS rank
    FROM procedures
    ORDER BY embedding <=> %(vec)s::vector LIMIT {_CANDIDATE_POOL}
),
sparse AS (
    SELECT id, content, source,
           RANK() OVER (ORDER BY ts_rank(content_tsv, query) DESC) AS rank
    FROM procedures, plainto_tsquery('french', %(q)s) AS query
    WHERE content_tsv @@ query
    LIMIT {_CANDIDATE_POOL}
)
SELECT
    COALESCE(d.id,      s.id)      AS id,
    COALESCE(d.content, s.content) AS content,
    COALESCE(d.source,  s.source)  AS source,
    (
        COALESCE(1.0 / ({_RRF_K} + d.rank), 0.0) +
        COALESCE(1.0 / ({_RRF_K} + s.rank), 0.0)
    ) AS rrf_score
FROM dense d FULL JOIN sparse s ON d.id = s.id
ORDER BY rrf_score DESC
LIMIT %(k)s
"""


def _conn_string() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def _vec_str(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in v) + "]"


def retrieve(query: str, k: int = 5) -> list[dict]:
    embedder = get_embeddings()
    vec = embedder.embed_query(query)

    with psycopg.connect(_conn_string()) as conn:
        rows = conn.execute(
            _HYBRID_SQL, {"vec": _vec_str(vec), "q": query, "k": k}
        ).fetchall()

    return [
        {"id": r[0], "content": r[1], "source": r[2], "score": float(r[3])}
        for r in rows
    ]


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "remboursement frais"
    print(f'Recherche : "{query}"\n')
    results = retrieve(query)
    for i, r in enumerate(results, 1):
        print(f"─── #{i} [{r['source']}] score={r['score']:.4f} ───")
        print(r["content"][:400])
        print()
