# BforBank Agent — IA Copilote Conseiller

Agent conversationnel **Agentic RAG** pour les conseillers BforBank : recherche de procédures internes (RAG sur Markdown) et analyse de données transactionnelles (Text-to-SQL sur PostgreSQL), disponible en deux modes d'exécution comparables.

Construit sur **LangGraph** + **Vertex AI (Gemini)**, avec une factory de modèles qui isole toute dépendance au provider (`src/llm_factory.py`) — changer de LLM ne touche pas au code métier.

---

## Architecture

```mermaid
graph TD
    A["Conseiller — CLI"] --> B{Mode}

    B -->|react| C["ReAct Agent\ncreate_react_agent"]
    B -->|langgraph| D["LangGraph Agent\nStateGraph custom"]

    C --> E["Tools partagés"]
    D --> E

    E --> F["RAG Tool\nretrieve_procedures"]
    E --> G["SQL Tool\nquery_client_data\nself-correction x3"]

    F --> H[("pgvector\ndense + BM25 RRF")]
    G --> I[("PostgreSQL\nclients / transactions")]

    F --> J["LLM Factory\nVertex AI / Gemini"]
    G --> J

    J --> K["Langfuse\nTraces / Spans"]
```

### Mode ReAct

Boucle observe → think → act via `create_react_agent`. Le LLM enchaîne les outils de façon adaptative : il peut appeler SQL, lire les résultats, puis construire une requête RAG ciblée.

![Graph ReAct](graph_react.png)

### Mode LangGraph — fan-out conditionnel

Un nœud `router` classifie la question (`rag` / `sql` / `both` / `direct`), puis dispatch. En mode `both`, `rag_node` et `sql_node` tournent **en parallèle**. Le nœud `synthesis` agrège.

![Graph LangGraph](graph_langgraph.png)

| | ReAct | LangGraph |
|---|---|---|
| Routing | LLM décide à chaque tour | Une décision upfront |
| Parallélisme | Non | Oui (`both`) |
| Adaptatif (chained reasoning) | Oui | Non — RAG sans contexte SQL |
| Flux de contrôle | Implicite (boucle) | Explicite (graph visible) |
| Tokens | Plus élevés (historique accumulé) | Réduits (nœuds isolés) |

---

## Prérequis

| Outil | Version |
|-------|---------|
| Docker + Docker Compose | 24+ |
| Python | 3.11+ |
| uv | latest |
| gcloud CLI | latest |

---

## Installation

```bash
# 1. Authentification Google Cloud (ADC — pas de clé API)
gcloud auth application-default login

# 2. Configuration
cp .env.example .env
# Renseigner : VERTEX_PROJECT=your-gcp-project-id

# 3. Services (PostgreSQL + Langfuse)
docker compose up -d

# 4. Dépendances Python
uv sync

# 5. Indexation des procédures dans pgvector
uv run python src/indexer/indexer.py

# 6. Lancer l'agent
uv run python src/agent/cli.py                  # Mode ReAct
uv run python src/agent/cli.py --mode langgraph # Mode LangGraph
```

### Langfuse (optionnel)

1. Ouvrir `http://localhost:3000` → créer un compte local
2. Créer un projet → **Settings** → **API Keys**
3. Copier `pk-lf-...` et `sk-lf-...` dans `.env`

> Sur VM distante : `ssh -L 3000:localhost:3000 <user>@<ip>`

---

## Configuration `.env`

| Variable | Description |
|----------|-------------|
| `VERTEX_PROJECT` | GCP project ID **(obligatoire)** |
| `VERTEX_LOCATION` | Région Vertex AI (défaut : `global`) |
| `LLM_MODEL` | Modèle Gemini (défaut : `gemini-3.1-flash-lite`) |
| `EMBEDDING_MODEL` | Modèle embedding (défaut : `text-multilingual-embedding-002`) |
| `DATABASE_URL` | PostgreSQL (défaut : `postgresql+psycopg://bforbank:bforbank@localhost:5432/bforbank`) |
| `LANGFUSE_PUBLIC_KEY` / `SECRET_KEY` / `HOST` | Observabilité (optionnel) |

> Pour OpenAI à la place de Vertex AI : `LLM_PROVIDER=openai`, `LLM_API_KEY=sk-...`

---

## Structure

```
bforbank-agent/
├── docker-compose.yaml
├── data/
│   ├── procedures/              # Procédures BforBank en Markdown
│   └── mock/
│       ├── schema.sql
│       └── seed.sql             # 4 clients de test
└── src/
    ├── config.py
    ├── llm_factory.py           # Abstraction provider (Vertex AI / OpenAI)
    ├── agent/
    │   ├── cli.py               # Entrypoint --mode react|langgraph
    │   ├── agent_react.py       # create_react_agent prebuilt
    │   └── agent_langgraph.py   # StateGraph fan-out custom
    ├── tools/
    │   ├── rag_tool.py          # retrieve_procedures
    │   ├── sql_tool.py          # query_client_data + self-correction ×3
    │   └── schema_inspector.py
    ├── indexer/
    │   ├── indexer.py
    │   └── retriever.py         # Recherche hybride dense + BM25 (RRF)
    ├── pii/
    │   └── anonymizer.py
    └── eval/
        ├── dataset.py           # 4 questions avec expected_output
        └── run_eval.py          # Comparaison ReAct vs LangGraph — DeepEval
```

---

## Sécurité — Protection des PII

Les données personnelles (nom, prénom, email, téléphone, date de naissance) sont filtrées **en sortie de base de données**, avant injection dans le contexte du LLM.

**Pourquoi en sortie et non en entrée ?** Masquer le nom dans la question casserait le Text-to-SQL (`WHERE nom = '[PERSONNE_1]'` ne matche rien). La solution production-grade — alias mapping + SQL rewriter — est documentée dans `ARCHITECTURE_DECISIONS.md`.

---

## Observabilité

Langfuse trace chaque tour dès que les clés sont renseignées. Chaque nœud apparaît comme span enfant avec input, output et tools appelés. Sans clés, l'agent fonctionne normalement.

---

## Évaluation

```bash
uv run python src/eval/run_eval.py
```

Comparaison ReAct vs LangGraph sur 4 questions (RAG / SQL / Mixte / Both), chacune avec un `expected_output` de référence. Métriques : `AnswerRelevancy` + `GEval Correctness` (judge = même modèle Gemini). Un fichier `eval_audit_latest.json` est généré à chaque run avec les réponses complètes et les raisons du judge.

La question mixte est intentionnellement vague ("Faites un bilan du compte…") pour mettre en défaut le fan-out parallèle : sans chaînage, le LangGraph ne sait pas quelle procédure chercher avant d'avoir vu les données SQL.

---

## Scale & Ops

| Composant | POC | Production GCP |
|-----------|-----|----------------|
| Base transactionnelle | PostgreSQL (Docker) | **AlloyDB** |
| Recherche vectorielle | pgvector | **Vertex AI Vector Search** |
| LLM | Gemini Flash Lite | Gemini Pro / fine-tuned |
| Déploiement | CLI locale | **Cloud Run** / GKE |
| Observabilité | Langfuse self-hosted | Langfuse Cloud / Cloud Monitoring |
| Évaluation | `run_eval.py` manuel | CI/CD — régression bloquante si score < seuil |
| PII | Filtrage colonnes | Alias mapping + SQL rewriter + LLM on-premise |

---

## Utilitaires

```bash
# Tester le retriever
uv run python src/indexer/retriever.py "remboursement frais bancaires"

# Accéder à la base
docker exec -it bforbank_db psql -U bforbank -d bforbank

# Reset complet
docker compose down -v && docker compose up -d && uv run python src/indexer/indexer.py
```
