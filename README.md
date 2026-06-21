# BforBank Agent — IA Copilote Conseiller

Agent conversationnel **Agentic RAG** combinant recherche documentaire (procédures internes) et analyse de données transactionnelles (Text-to-SQL) pour assister les conseillers BforBank.

Le projet tourne sur **Vertex AI (Gemini)** et est conçu autour d'une factory de modèles (`src/llm_factory.py`) qui isole toute dépendance au provider derrière l'interface `BaseChatModel` de LangChain — brancher un autre provider ne demande aucune modification au code métier.

---

## Architecture

```mermaid
graph TD
    A[Conseiller CLI<br/>cli.py --mode react|langgraph] --> B{Mode}

    B -->|react| C[ReAct Agent<br/>create_react_agent prebuilt]
    B -->|langgraph| D[LangGraph Agent<br/>StateGraph custom]

    C --> E[Tools partagés]
    D --> E

    E --> F[RAG Tool<br/>retrieve_procedures]
    E --> G[SQL Tool<br/>query_client_data<br/>self-correction ×3]

    F --> H[(pgvector<br/>dense + BM25<br/>RRF)]
    G --> I[(PostgreSQL<br/>clients · transactions)]

    I -->|strip PII columns| G

    F --> J[LLM Factory<br/>Vertex AI · Gemini]
    G --> J

    J --> K[Langfuse<br/>Traces · Spans]
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

Renseigner au minimum :

```bash
VERTEX_PROJECT=your-gcp-project-id

# Langfuse (optionnel — remplir après l'étape 3b)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

### 3. Démarrer les services

```bash
docker compose up -d
docker compose ps   # attendre STATUS: healthy
```

Lance deux services :
- **PostgreSQL** (`localhost:5432`) — schéma et données de test injectés automatiquement
- **Langfuse** (`http://localhost:3000`) — UI d'observabilité

#### 3b. Configurer Langfuse (première fois)

1. Ouvrir `http://localhost:3000`
2. **Sign Up** → créer un compte local (rien n'est envoyé en dehors)
3. Créer une organisation puis un projet (ex: `bforbank`)
4. **Settings** → **API Keys** → **Create new API key**
5. Copier `pk-lf-...` et `sk-lf-...` dans `.env`

> **Sur une VM distante** : forwarder le port avant d'ouvrir le navigateur :
> ```bash
> ssh -L 3000:localhost:3000 <user>@<ip-vm>
> ```

### 4. Installer les dépendances Python

```bash
uv sync
```

### 5. Indexer les procédures

```bash
uv run python src/indexer/indexer.py
```

Génère les embeddings des fichiers `data/procedures/*.md` et les stocke dans pgvector (recherche hybride dense + tsvector BM25). Opération **idempotente**.

### 6. Lancer l'agent

```bash
# Mode ReAct (défaut)
uv run python src/agent/cli.py

# Mode LangGraph — StateGraph custom avec nœuds explicites
uv run python src/agent/cli.py --mode langgraph
```

---

## Configuration `.env`

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `VERTEX_PROJECT` | **oui** | GCP project ID |
| `VERTEX_LOCATION` | non | Région Vertex AI (défaut : `global`) |
| `LLM_MODEL` | non | Modèle Gemini (défaut : `gemini-3.1-flash-lite`) |
| `EMBEDDING_MODEL` | non | Modèle d'embedding (défaut : `text-multilingual-embedding-002`) |
| `DATABASE_URL` | non | URL PostgreSQL (défaut : `postgresql+psycopg://bforbank:bforbank@localhost:5432/bforbank`) |
| `LANGFUSE_PUBLIC_KEY` | non | Clé publique Langfuse |
| `LANGFUSE_SECRET_KEY` | non | Clé secrète Langfuse |
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
│   └── mock/
│       ├── schema.sql           # Schéma : clients, transactions
│       └── seed.sql             # Données de test (4 clients)
└── src/
    ├── config.py                # Configuration via pydantic-settings
    ├── llm_factory.py           # Factory LLM/Embeddings (abstraction provider)
    ├── agent/
    │   ├── cli.py               # Entrypoint CLI (--mode react|langgraph)
    │   ├── agent_react.py       # Agent ReAct (create_react_agent prebuilt)
    │   └── agent_langgraph.py   # Agent LangGraph (StateGraph custom)
    ├── tools/
    │   ├── rag_tool.py          # @tool retrieve_procedures — recherche hybride
    │   ├── sql_tool.py          # @tool query_client_data — Text-to-SQL + self-correction ×3
    │   └── schema_inspector.py  # DDL du schéma pour la génération SQL
    ├── indexer/
    │   ├── indexer.py           # Indexation des procédures dans pgvector
    │   └── retriever.py         # Recherche hybride dense + tsvector (RRF)
    ├── pii/
    │   └── anonymizer.py        # Filtrage PII colonnes DB + patterns regex
    └── eval/
        ├── dataset.py           # 3 questions d'évaluation (RAG, SQL, mixte)
        └── run_eval.py          # Comparaison ReAct vs LangGraph — DeepEval
```

---

## Sécurité — Protection des PII

Les données personnelles des clients (nom, prénom, email, téléphone, date de naissance) sont filtrées **en sortie de base de données**, avant injection dans le contexte du LLM.

```python
# sql_tool.py
_PII_COLUMNS = {"nom", "prenom", "email", "telephone", "date_naissance"}

def _strip_pii(rows):
    return [{k: v for k, v in row.items() if k not in _PII_COLUMNS} for row in rows]
```

**Pourquoi en sortie et non en entrée ?** Masquer le nom dans la question du conseiller casserait le Text-to-SQL (`WHERE nom = '[PERSONNE_1]'` ne matche rien en base). La solution complète production-grade — alias mapping + SQL rewriter — est décrite dans `ARCHITECTURE_DECISIONS.md`.

---

## Observabilité

Langfuse trace chaque tour de conversation dès que les clés sont renseignées dans `.env`. Chaque nœud du graph apparaît comme un span enfant avec son input, output, et les tools appelés.

```
Trace : bforbank-langgraph  [tag: langgraph]
├── input  : { question: "Quelles transactions suspectes pour Marie Martin ?" }
├── Span : call_model  → tool_calls: ["query_client_data"]
├── Span : tools       → résultats SQL filtrés
├── Span : call_model  → tool_calls: ["retrieve_procedures"]
├── Span : tools       → procédure litige
└── Span : call_model  → réponse finale
    output : { answer: "Marie Martin a 2 transactions LITIGE..." }
```

L'observabilité est **optionnelle** — si les clés sont absentes, l'agent fonctionne normalement.

---

## Évaluation

Comparaison quantitative des deux modes (ReAct vs LangGraph) sur 3 questions représentatives :

```bash
uv run python src/eval/run_eval.py
```

| Métrique | Type de question |
|----------|-----------------|
| `AnswerRelevancy` | toutes |
| `Faithfulness` | RAG, mixte |
| `GEval Correctness` | SQL |
| Temps de réponse | toutes |
| Nombre de tool calls | toutes |
| Tokens consommés | toutes |

Le judge LLM est le même modèle que l'agent (Gemini via Vertex AI) — aucune dépendance externe supplémentaire.

---

## Scale & Ops — Du POC à la production

| Composant | POC (actuel) | Production GCP |
|-----------|-------------|----------------|
| Base transactionnelle | PostgreSQL (Docker) | **AlloyDB** — PostgreSQL managé, HA, ~10× plus rapide sur les scans |
| Recherche vectorielle | pgvector (même instance) | **Vertex AI Vector Search** — index ANN managé, scalable à des millions de vecteurs |
| LLM | Gemini Flash Lite (Vertex AI) | Gemini Pro / fine-tuned — selon les exigences qualité |
| Déploiement agent | CLI locale | **Cloud Run** (serverless) ou **GKE** si état persistant |
| Observabilité | Langfuse self-hosted | Langfuse Cloud ou intégration **Cloud Monitoring** |
| Évaluation | Manuel (`run_eval.py`) | CI/CD — exécution automatique sur chaque PR, régression bloquante si score < seuil |
| PII | Filtrage colonnes (POC) | Alias mapping + SQL rewriter + LLM on-premise (Mistral/Llama sur GKE) |

---

## Utilitaires

```bash
# Tester le retriever directement
uv run python src/indexer/retriever.py "remboursement frais bancaires"

# Accéder à la base de données
docker exec -it bforbank_db psql -U bforbank -d bforbank

# Réinitialisation complète
docker compose down -v && docker compose up -d && uv run python src/indexer/indexer.py
```
