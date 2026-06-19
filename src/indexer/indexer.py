"""
Indexeur des procédures BforBank dans pgvector.

Pipeline : Markdown → chunks → embeddings Vertex AI → table `procedures`
           avec colonne dense (vector) + colonne sparse (tsvector) pour la recherche hybride.

Idempotent : vide et réindexe à chaque exécution.
Usage : uv run python src/indexer/indexer.py
"""

from pathlib import Path

import psycopg
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import settings
from src.llm_factory import get_embeddings

PROCEDURES_DIR = Path(__file__).parent.parent.parent / "data" / "procedures"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
EMBEDDING_DIM = 768


def _conn_string() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def _ensure_table(conn: psycopg.Connection) -> None:
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS procedures (
            id          SERIAL PRIMARY KEY,
            source      VARCHAR(255) NOT NULL,
            chunk_index INTEGER      NOT NULL,
            content     TEXT         NOT NULL,
            embedding   vector({EMBEDDING_DIM}),
            content_tsv TSVECTOR GENERATED ALWAYS AS (
                to_tsvector('french', content)
            ) STORED
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_procedures_tsv
        ON procedures USING GIN (content_tsv)
    """)
    conn.commit()


def _load_chunks() -> list[tuple[str, int, str]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks: list[tuple[str, int, str]] = []
    for md_file in sorted(PROCEDURES_DIR.glob("*.md")):
        parts = splitter.split_text(md_file.read_text(encoding="utf-8"))
        for i, part in enumerate(parts):
            chunks.append((md_file.name, i, part))
    return chunks


def _vec_str(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in v) + "]"


def run() -> None:
    chunks = _load_chunks()
    if not chunks:
        print(f"Aucun fichier .md trouvé dans {PROCEDURES_DIR}")
        return

    print(f"Génération des embeddings pour {len(chunks)} chunks...")
    embedder = get_embeddings()
    embeddings = embedder.embed_documents([c[2] for c in chunks])

    with psycopg.connect(_conn_string()) as conn:
        _ensure_table(conn)
        conn.execute("DELETE FROM procedures")
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO procedures (source, chunk_index, content, embedding)
                VALUES (%s, %s, %s, %s::vector)
                """,
                [
                    (source, idx, content, _vec_str(emb))
                    for (source, idx, content), emb in zip(chunks, embeddings)
                ],
            )
        conn.commit()

    print(f"✓ {len(chunks)} chunks indexés depuis {len(set(c[0] for c in chunks))} fichiers.")


if __name__ == "__main__":
    run()
