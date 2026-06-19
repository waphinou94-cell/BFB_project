# BforBank Agent — IA Copilote Conseiller

Agent conversationnel **Agentic RAG** combinant recherche documentaire (procédures internes) et analyse de données transactionnelles (Text-to-SQL) pour assister les conseillers BforBank.

Le projet tourne sur **Vertex AI (Gemini)** et est conçu autour d'une factory de modèles (`src/llm_factory.py`) qui isole toute dépendance au provider derrière l'interface `BaseChatModel` de LangChain — brancher un autre provider ne demande aucune modification au code métier.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Conseiller (CLI)                  │
│           src/agent/cli.py --mode react|langgraph   │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┴──────────────┐
         │                            │
┌────────▼────────┐        ┌──────────▼──────────┐
│  ReAct Agent    │        │  LangGraph Agent     │
│ (prebuilt,      │        │  (StateGraph custom, │
│  mode défaut)   │        │   flux explicite)    │
└────────┬────────┘        └──────────┬───────────┘
         └─────────────┬──────────────┘
                       │ tools partagés
          ┌────────────┴────────────┐
          │                         │
   ┌──────▼──────┐          ┌───────▼──────────┐
   │  RAG Tool   │          │  SQL Tool        │
   │ retrieve_   │          │  query_client_   │
   │ procedures()│          │  data()          │
   │             │          │  + self-corr. ×3 │
   └──────┬──────┘          └───────┬──────────┘
          │                         │
   ┌──────▼──────┐          ┌───────▼──────┐
   │  pgvector   │          │  PostgreSQL  │
   │  hybride    │          │  (clients,   │
   │ dense+BM25  │          │  transactions│
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

Ouvrir `.env` et renseigner au minimum :

```bash
# GCP project ID (obligatoire)
VERTEX_PROJECT=your-gcp-project-id

# Langfuse — remplir après l'étape 3b ci-dessous (optionnel)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

Les autres valeurs par défaut (`gemini-3.1-flash-lite`, `global`) peuvent être conservées.

### 3. Démarrer les services

```bash
docker compose up -d
docker compose ps   # attendre STATUS: healthy pour postgres et langfuse
```

Lance deux services :
- **PostgreSQL** (`localhost:5432`) — base transactionnelle, schéma et données de test injectés automatiquement
- **Langfuse** (`http://localhost:3000`) — UI d'observabilité

#### 3b. Configurer Langfuse (première fois)

1. Ouvrir `http://localhost:3000`
2. Cliquer **Sign Up** → créer un compte local (email/mot de passe arbitraires, rien n'est envoyé)
3. Créer une **organisation** puis un **projet** (ex: `bforbank`)
4. Dans le projet → **Settings** → **API Keys** → **Create new API key**
5. Copier la **Public Key** (`pk-lf-...`) et la **Secret Key** (`sk-lf-...`) dans `.env`

> **Sur une VM distante** : Langfuse n'est pas accessible depuis `localhost` de votre machine. Forwarder le port avant d'ouvrir le navigateur :
> ```bash
> # Sur votre machine locale
> ssh -L 3000:localhost:3000 <user>@<ip-vm>
> ```
> Puis ouvrir `http://localhost:3000` dans votre navigateur.

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
uv run python src/indexer/retriever.py "remboursement frais bancaires"
uv run python src/indexer/retriever.py "opposition carte bancaire"
```

Affiche les top-5 chunks les plus pertinents avec leur score RRF et le fichier source.

### 7. Lancer l'agent

```bash
# Mode ReAct (défaut) — create_react_agent prebuilt
uv run python src/agent/cli.py

# Mode LangGraph — StateGraph custom avec nœuds explicites
uv run python src/agent/cli.py --mode langgraph
```

Les traces apparaissent dans Langfuse à `http://localhost:3000` dès que les clés sont renseignées dans `.env`.

---

## Configuration `.env` complète

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `VERTEX_PROJECT` | **oui** | GCP project ID |
| `VERTEX_LOCATION` | non | Région Vertex AI (défaut : `global`) |
| `LLM_MODEL` | non | Modèle Gemini (défaut : `gemini-3.1-flash-lite`) |
| `EMBEDDING_MODEL` | non | Modèle d'embedding (défaut : `text-multilingual-embedding-002`) |
| `DATABASE_URL` | non | URL PostgreSQL (défaut : `postgresql+psycopg://bforbank:bforbank@localhost:5432/bforbank`) |
| `LANGFUSE_PUBLIC_KEY` | non | Clé publique Langfuse (`pk-lf-...`) |
| `LANGFUSE_SECRET_KEY` | non | Clé secrète Langfuse (`sk-lf-...`) |
| `LANGFUSE_HOST` | non | URL Langfuse (défaut : `http://localhost:3000`) |

> Pour utiliser **OpenAI** à la place de Vertex AI : `LLM_PROVIDER=openai`, `LLM_API_KEY=sk-...`

---

## Structure du projet

```
bforbank-agent/
├── docker-compose.yaml          # PostgreSQL + pgvector + Langfuse
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
    │   ├── cli.py               # Entrypoint CLI (--mode react|langgraph)
    │   ├── agent_react.py       # Agent ReAct (create_react_agent prebuilt)
    │   └── agent_langgraph.py   # Agent LangGraph (StateGraph custom)
    ├── tools/
    │   ├── rag_tool.py          # @tool retrieve_procedures — recherche hybride
    │   ├── sql_tool.py          # @tool query_client_data — Text-to-SQL + self-correction ×3
    │   └── schema_inspector.py  # DDL du schéma pour la génération SQL
    └── indexer/
        ├── indexer.py           # Indexation des procédures dans pgvector
        └── retriever.py         # Recherche hybride dense + tsvector (RRF)
```

---

## Configuration LLM

Le provider est sélectionné via `LLM_PROVIDER` dans `.env`. Le code métier ne connaît que l'interface `BaseChatModel` — changer de provider ne touche pas à l'agent ni aux tools.

| `LLM_PROVIDER` | Authentification | Modèle par défaut |
|----------------|-----------------|-------------------|
| `vertexai` *(défaut)* | ADC (`gcloud auth application-default login`) | `gemini-3.1-flash-lite` |
| `openai` | `LLM_API_KEY=sk-...` | `gpt-4o-mini` |

---

## Observabilité

Langfuse trace automatiquement chaque tour de conversation dès que `LANGFUSE_PUBLIC_KEY` et `LANGFUSE_SECRET_KEY` sont renseignés dans `.env`.

En mode `langgraph`, chaque nœud du graph (`call_model`, `tools`) apparaît comme un span enfant dans la trace — ce qui permet de voir exactement par quelles étapes l'agent est passé pour construire sa réponse.

```
Trace : bforbank-langgraph
├── Span : call_model      ← LLM décide d'appeler un tool
├── Span : tools           ← RAG ou SQL exécuté
└── Span : call_model      ← synthèse finale
```

UI disponible sur `http://localhost:3000` (ou via SSH port-forward depuis une VM).

L'observabilité est **optionnelle** — si les clés sont absentes du `.env`, l'agent fonctionne normalement sans envoyer de traces.

---

## Visualiser la base de données

```bash
docker exec -it bforbank_db psql -U bforbank -d bforbank
```

```sql
-- Clients et soldes
SELECT id, nom, prenom, solde, decouvert_autorise FROM clients;

-- Dernières transactions par client
SELECT c.nom, t.date_transaction, t.montant, t.libelle, t.statut
FROM transactions t JOIN clients c ON c.id = t.client_id
ORDER BY t.date_transaction DESC LIMIT 20;

-- Procédures indexées
SELECT source, COUNT(*) AS nb_chunks FROM procedures GROUP BY source ORDER BY source;
```

---

## Réinitialisation complète

```bash
docker compose down -v
docker compose up -d
uv run python src/indexer/indexer.py
```
