# 🗺️ Plan de Développement — Agent IA Copilote BforBank

> **Philosophie** : *Working software over comprehensive documentation.*
> Chaque phase produit quelque chose qui tourne. On ne passe à la suivante que si c'est stable.

---

## 📊 Vue d'ensemble

```
Phase 1 → Données         (fondations)
Phase 2 → Agent nu        (squelette conversationnel)
Phase 3 → Indexation      (RAG pipeline)
Phase 4 → Agent outillé   (RAG + SQL + routing)
Phase 5 → Production-isation (PII, observabilité, README)
```

---

## Phase 1 — Fondations des données

> *Objectif : avoir des données réalistes sur lesquelles tester chaque brique.*

### 1.1 — Répertoire `data/procedures/`
- [ ] Créer 4-5 fichiers Markdown de procédures BforBank :
  - `remboursement_frais.md` — Politique de remboursement des frais bancaires
  - `litige_transaction.md` — Procédure de contestation d'une transaction
  - `analyse_solvabilite.md` — Critères et process d'analyse de solvabilité
  - `opposition_carte.md` — Procédure d'opposition sur carte
- [ ] Chaque fichier contient : contexte, étapes, critères de décision, lien Confluence fictif

### 1.2 — Schéma PostgreSQL + Mock Data
- [ ] `docker-compose.yaml` avec `pgvector/pgvector:pg16`
- [ ] `data/sql/schema.sql` — Tables : `clients`, `transactions`
- [ ] `data/sql/seed.sql` — 3 à 5 clients fictifs avec historique transactionnel varié :
  - Un client avec frais contestables
  - Un client standard (contrôle)

### 1.3 — Catalogue de questions de test
- [ ] `data/test_questions.md` — 10 questions représentatives, par exemple :
  - *"Quels frais peut-on rembourser à Marie Martin selon nos procédures ?"*
  - *"Montre-moi les 5 dernières transactions de Pierre Durand et analyse les risques."*

> ✅ **Critère de sortie** : `docker-compose up` lance PostgreSQL avec données injectées.

---

## Phase 2 — Agent de base (squelette nu)

> *Objectif : un agent LLM qui répond, sans aucun outil. Valider la structure du code.*

- [ ] Choisir le framework : **LangGraph** (recommandé pour l'agentic routing) ou LangChain LCEL
- [ ] `src/agent/base_agent.py` — Agent conversationnel simple (LLM seul, pas de tools)
- [ ] `src/config.py` — Gestion des variables d'environnement (clés API, DB URL)
- [ ] Tester avec 2-3 questions du catalogue → valider que le LLM répond correctement sur le fond

> ✅ **Critère de sortie** : `python src/agent/base_agent.py` → conversation fonctionnelle en CLI.

---

## Phase 3 — Script d'indexation

> *Objectif : indexer les procédures dans pgvector pour les rendre interrogeables.*

### 3.1 — Indexation dense (obligatoire)
- [ ] `src/indexer/indexer.py` — Pipeline :
  1. Lire les fichiers Markdown de `data/procedures/`
  2. Chunker (RecursiveCharacterTextSplitter, chunk=512, overlap=64)
  3. Générer les embeddings (OpenAI `text-embedding-3-small` ou `nomic-embed-text` local)
  4. Stocker dans pgvector (`langchain_postgres` ou `psycopg3` direct)

### 3.2 — Indexation hybride (challenger ⚡)

> **Mon challenge** : Hybride, oui, mais seulement si tu as le temps.
>
> **Pourquoi ça vaut le coup ici** : les procédures bancaires contiennent des termes très spécifiques (*"fraude au président"*, *"SEPA"*, *"RIB"*) que le dense seul peut rater. L'hybride (dense + BM25/keyword) récupère ces cas edge.
>
> **Comment faire simplement avec PostgreSQL** :
> - Dense : `pgvector` (colonne `embedding vector(1536)`)
> - Sparse : `tsvector` natif PostgreSQL (Full-Text Search intégré, 0 dépendance externe)
> - Fusion : **Reciprocal Rank Fusion (RRF)** — simple, prouvé, pas de poids à tuner

```sql
-- Exemple de requête hybride RRF
WITH dense AS (
  SELECT id, RANK() OVER (ORDER BY embedding <=> $1) AS rank
  FROM procedures ORDER BY embedding <=> $1 LIMIT 20
),
sparse AS (
  SELECT id, RANK() OVER (ORDER BY ts_rank(content_tsv, query) DESC) AS rank
  FROM procedures, to_tsquery('french', $2) query
  WHERE content_tsv @@ query LIMIT 20
)
SELECT COALESCE(d.id, s.id),
       1.0/60+d.rank) + 1.0/(60+s.rank) AS rrf_score
FROM dense d FULL JOIN sparse s ON d.id = s.id
ORDER BY rrf_score DESC LIMIT 5;
```

> **Verdict** : Commence par dense seul. Si Phase 3.1 est terminée rapidement → ajoute le `tsvector`. C'est 30 min de plus, pas plus.

- [ ] `src/indexer/retriever.py` — Fonction `retrieve(query, k=5)` testable indépendamment

> ✅ **Critère de sortie** : `python src/indexer/indexer.py` → procédures indexées. `retrieve("fraude")` → top 5 chunks pertinents.

---

## Phase 4 — Agent outillé (RAG + Text-to-SQL)

> *Objectif : l'agent utilise ses outils pour répondre aux questions du catalogue.*

### 4.1 — Tool : RAG sur procédures
- [ ] `src/tools/rag_tool.py` — `@tool retrieve_procedures(query: str)` → appelle `retriever.py`
- [ ] Prompt système : *"Cite la procédure utilisée avec son lien Confluence fictif"*

### 4.2 — Tool : Text-to-SQL avec self-correction
- [ ] `src/tools/sql_tool.py` — `@tool query_client_data(client_id: str, question: str)`
  1. LLM génère le SQL à partir du schéma
  2. Exécution de la requête
  3. **Boucle de self-correction** : si erreur SQL → LLM analyse l'erreur + corrige → max 3 tentatives
- [ ] `src/tools/schema_inspector.py` — Fournit le DDL du schéma au LLM au moment de la génération SQL

### 4.3 — Routing & Synthèse finale
- [ ] Intégrer les 2 tools dans l'agent (LangGraph state machine ou ReAct)
- [ ] Prompt de synthèse : *"Croise procédure + données transactionnelles → réponse argumentée"*
- [ ] Tester les 10 questions du catalogue

> ✅ **Critère de sortie** : les 3 cas clients du seed répondus correctement avec source citée.

---

## Phase 5 — Production-isation

> *Objectif : couvrir les exigences "Production-Ready" du livrable.*

### 5.1 — PII Protection (local)
- [ ] `src/security/pii_detector.py` — Modèle local de détection/masquage PII
  - Option A : `presidio-analyzer` + `spacy fr_core_news_sm` (léger, open-source)
  - Option B : regex rules + NER pour les cas bancaires (IBAN, n° carte, etc.)
- [ ] Pipeline : `requête → anonymisation → LLM → réponse → dé-anonymisation`

### 5.2 — Observabilité
- [ ] Intégrer **Langfuse** (auto-hébergé en Docker ou cloud free tier) ou **Phoenix (Arize)**
- [ ] Tracer : chaque tool call, le SQL généré, les chunks RAG récupérés, la synthèse finale

### 5.3 — README Production-Ready
- [ ] Instructions d'installation (`docker-compose up`, `pip install`, variables d'env)
- [ ] Architecture Mermaid
- [ ] Section "Scale & Ops" : migration vers GCP (AlloyDB pgvector → Vertex AI Vector Search)
- [ ] Stratégie d'évaluation : **Ragas** (faithfulness, answer relevancy, context precision)

### 5.4 — Polish final
- [ ] Relire les questions du catalogue → vérifier cohérence des réponses
- [ ] Nettoyer le code, ajouter les docstrings essentiels
- [ ] Vérifier que `docker-compose up && python main.py` fonctionne from scratch

> ✅ **Critère de sortie** : le jury peut cloner le repo et lancer la démo en < 5 min.

---

## ⏱️ Estimation temporelle (2h)

| Phase | Durée estimée | Priorité |
|-------|--------------|----------|
| Phase 1 — Données | 25 min | 🔴 Critique |
| Phase 2 — Agent nu | 15 min | 🔴 Critique |
| Phase 3 — Indexation (dense) | 20 min | 🔴 Critique |
| Phase 3.2 — Hybride | +20 min | 🟡 Si temps dispo |
| Phase 4 — Agent outillé | 35 min | 🔴 Critique |
| Phase 5 — Production-isation | 25 min | 🟠 Partiel OK |

> **Si tu manques de temps** : Phase 5 peut être partielle. Un agent qui fonctionne bien vaut mieux qu'un agent PII-ready qui crashe.

---

## 🏗️ Structure cible du repo

```
bforbank-agent/
├── docker-compose.yaml
├── README.md
├── .env.example
├── data/
│   ├── procedures/          # Markdown procédures
│   ├── sql/
│   │   ├── schema.sql
│   │   └── seed.sql
│   └── test_questions.md
└── src/
    ├── agent/
    │   └── agent.py         # LangGraph agent
    ├── tools/
    │   ├── rag_tool.py
    │   └── sql_tool.py
    ├── indexer/
    │   ├── indexer.py
    │   └── retriever.py
    ├── security/
    │   └── pii_detector.py
    └── config.py
```
