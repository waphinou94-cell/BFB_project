# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

This is a BforBank technical interview project: an **Agentic RAG** conversational agent for bank advisors, combining procedure search (RAG on Markdown docs) and transactional data analysis (Text-to-SQL on PostgreSQL). The agent is built with LangGraph and uses an OpenAI-compatible API so any LLM provider can be plugged in.

## Commands

```bash
# Install dependencies
uv sync

# Start PostgreSQL (auto-seeds schema + data on first run)
docker compose up -d
docker compose ps   # wait for STATUS: healthy

# Run the agent (interactive CLI)
uv run python src/agent/agent.py

# Index procedures into pgvector (idempotent)
uv run python src/indexer/indexer.py

# Full reset (drops all data)
docker compose down -v && docker compose up -d && uv run python src/indexer/indexer.py
```

## Architecture

The agent is a **LangGraph `StateGraph`** using `MessagesState` (conversation history as messages list). The graph currently has a single `model` node; tools (RAG, SQL) will be bound to the LLM node and auto-dispatched by LangGraph.

**Data flow per request:**
1. User question → `call_model` node (LLM with system prompt)
2. LLM decides whether to call tools (once implemented): `rag_tool` or `sql_tool`
3. Tool results feed back into the graph → LLM synthesizes final answer

**Key modules (planned full structure):**
- `src/config.py` — Pydantic Settings loaded from `.env`; single `settings` singleton used everywhere
- `src/agent/agent.py` — LangGraph graph definition + interactive CLI entrypoint
- `src/tools/rag_tool.py` — `@tool` wrapping `retriever.py` for procedure search
- `src/tools/sql_tool.py` — `@tool` for Text-to-SQL with self-correction loop (max 3 retries on SQL error)
- `src/indexer/indexer.py` — Chunks `data/procedures/*.md`, generates embeddings, stores in pgvector
- `src/indexer/retriever.py` — `retrieve(query, k=5)` function for vector similarity search

**PostgreSQL schema** (all in the same DB as pgvector):
- `clients` — bank customers (id, nom, prenom, solde, decouvert_autorise…)
- `transactions` — transaction history (montant, libelle, type: CB/VIREMENT/PRELEVEMENT/FRAIS, statut: OK/LITIGE/SUSPICIEUX/REJETE)
- pgvector table (created by indexer) — procedure chunks with embeddings

## LLM configuration

All LLM and embedding settings come from `.env` via `src/config.py`. Provider selection is centralized in `src/llm_factory.py` — the agent and tools only depend on `BaseChatModel` / `Embeddings` interfaces, never on a specific provider.

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` / `EMBEDDING_PROVIDER` | `vertexai` (default) or `openai` |
| `LLM_MODEL` / `EMBEDDING_MODEL` | Model names |
| `VERTEX_PROJECT` / `VERTEX_LOCATION` | Vertex AI config (used when provider=vertexai) |
| `LLM_BASE_URL` / `LLM_API_KEY` | OpenAI config (used when provider=openai) |
| `DATABASE_URL` | PostgreSQL connection (psycopg3 format) |

Vertex AI uses **Application Default Credentials** — no API key needed, just `gcloud auth application-default login`. Adding a new provider means adding one `elif` in `get_llm()` and `get_embeddings()` in `llm_factory.py`.

## Current implementation state

Phase 2 is complete (base agent skeleton) plus the LLM factory abstraction. Phases 3–5 (indexer, tools, PII protection, observability) are planned in `PLAN.md`. The `src/` directory structure in the README shows the intended final layout; currently only `src/agent/agent.py`, `src/config.py`, and `src/llm_factory.py` exist.
