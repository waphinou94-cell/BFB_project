# BforBank Agent — IA Copilote Conseiller

Agent conversationnel **Agentic RAG** combinant recherche documentaire (procédures internes) et analyse de données transactionnelles (Text-to-SQL) pour assister les conseillers BforBank.

Le projet tourne sur **Vertex AI (Gemini)** et est conçu autour d'une factory de modèles (`src/llm_factory.py`) qui isole toute dépendance au provider derrière l'interface `BaseChatModel` de LangChain — brancher un autre provider ne demande aucune modification au code métier.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Conseiller (CLI)                  │
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  LangGraph Agent │  ← src/agent/agent.py
              └────────┬────────┘
          ┌────────────┴────────────┐
          │                         │
   ┌──────▼──────┐          ┌───────▼──────┐
   │  RAG Tool   │          │  SQL Tool    │
   │ (procédures)│          │ (transactions│
   │             │          │ + self-corr.)│
   └──────┬──────┘          └───────┬──────┘
          │                         │
   ┌──────▼──────┐          ┌───────▼──────┐
   │  pgvector   │          │  PostgreSQL  │
   │ (embeddings)│          │  (clients,   │
   │             │          │  transactions│
   └─────────────┘          └─────────────┘
          │                         │
          └────────────┬────────────┘
                ┌──────▼──────┐
                │ LLM Factory │  ← src/llm_factory.py
                │  Vertex AI  │
                │  (Gemini)   │
                └─────────────┘
```

---

## Prérequis

| Outil | Version | Vérification |
|-------|---------|--------------|
| Docker + Docker Compose | 24+ | `docker --version` |
| Python | 3.11+ | `python --version` |
| uv | latest | `uv --version` |
| gcloud CLI | latest | `gcloud --version` |

---

## Installation

### 1. Authentification Google Cloud

```bash
gcloud auth application-default login
```

> L'agent utilise les **Application Default Credentials (ADC)** — aucune clé API à gérer.

### 2. Configurer l'environnement

```bash
cp .env.example .env
```

Éditer `.env` et renseigner votre `VERTEX_PROJECT` (votre GCP project ID) :

```bash
VERTEX_PROJECT=your-gcp-project-id
```

Les autres valeurs par défaut (`gemini-3.1-flash-lite`, `global`) peuvent être conservées.

### 3. Démarrer la base de données

```bash
docker-compose up -d
docker-compose ps   # attendre STATUS: healthy
```

La base PostgreSQL est automatiquement initialisée avec le schéma (`data/sql/schema.sql`) et les données de test (`data/sql/seed.sql`).

### 4. Installer les dépendances Python

```bash
uv sync
```

### 5. Indexer les procédures

```bash
uv run python src/indexer/indexer.py
```

Génère les embeddings des fichiers `data/procedures/*.md` et les stocke dans pgvector (recherche hybride dense + tsvector). Opération **idempotente**.

### 6. Tester le retriever

```bash
# Recherche hybride directe (passe la requête en argument)
uv run python src/indexer/retriever.py "remboursement frais bancaires"
uv run python src/indexer/retriever.py "opposition carte bancaire"
```

Affiche les top-5 chunks les plus pertinents avec leur score RRF et le fichier source.

### 7. Lancer l'agent

```bash
uv run python src/agent/agent.py
```

---

## Structure du projet

```
bforbank-agent/
├── docker-compose.yaml          # PostgreSQL avec pgvector
├── pyproject.toml               # Dépendances Python (uv)
├── .env.example                 # Template de configuration
├── data/
│   ├── procedures/              # Procédures BforBank en Markdown
│   └── sql/
│       ├── schema.sql           # Schéma : clients, transactions
│       └── seed.sql             # Données de test (4 clients)
└── src/
    ├── config.py                # Configuration via pydantic-settings
    ├── llm_factory.py           # Factory LLM/Embeddings (pattern provider)
    ├── agent/
    │   └── agent.py             # Graph LangGraph + CLI interactif
    ├── tools/
    │   ├── rag_tool.py          # Recherche dans les procédures
    │   └── sql_tool.py          # Text-to-SQL avec boucle de self-correction
    └── indexer/
        ├── indexer.py           # Indexation des procédures dans pgvector
        └── retriever.py         # Recherche vectorielle (dense + hybride BM25)
```

---

## Configuration LLM

Le provider est sélectionné via `LLM_PROVIDER` dans `.env`. Le code métier ne connaît que l'interface `BaseChatModel` — changer de provider ne touche pas à l'agent ni aux tools.

| `LLM_PROVIDER` | Authentification | Modèle par défaut |
|----------------|-----------------|-------------------|
| `vertexai` *(défaut)* | ADC (`gcloud auth application-default login`) | `gemini-3.1-flash-lite` |
| `openai` | `LLM_API_KEY=sk-...` | `gpt-4o-mini` |

---

## Visualiser la base de données

Connexion interactive avec psql (autocomplétion, historique) :

```bash
docker exec -it bforbank_db psql -U bforbank -d bforbank
```

Quelques requêtes utiles une fois connecté :

```sql
-- Tables disponibles
\dt

-- Clients et soldes
SELECT id, nom, prenom, solde, decouvert_autorise FROM clients;

-- Dernières transactions par client
SELECT c.nom, t.date_transaction, t.montant, t.libelle, t.statut
FROM transactions t JOIN clients c ON c.id = t.client_id
ORDER BY t.date_transaction DESC LIMIT 20;

-- Procédures indexées (chunks)
SELECT source, COUNT(*) AS nb_chunks FROM procedures GROUP BY source ORDER BY source;

-- Vérifier qu'un embedding est bien stocké
SELECT id, source, LEFT(content, 80) AS extrait FROM procedures LIMIT 5;
```

---

## Réinitialisation complète

```bash
docker compose down -v
docker compose up -d
uv run python src/indexer/indexer.py
```
