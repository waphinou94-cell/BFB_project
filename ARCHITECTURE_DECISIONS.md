# Choix d'Architecture

---

## 1. Framework agent : LangGraph

**Choix** : LangGraph (`StateGraph` + `MessagesState`) plutôt que LangChain LCEL.

LangGraph modélise l'agent comme une machine à états — chaque nœud est une étape (LLM, tool call, correction SQL…), les arêtes définissent le routing. Ça rend le flux de décision explicite et extensible : ajouter un tool = ajouter un nœud + une arête conditionnelle, sans refactorer le reste.

---

## 2. Abstraction provider LLM : Factory pattern

**Choix** : `src/llm_factory.py` expose `get_llm()` et `get_embeddings()` derrière les interfaces `BaseChatModel` / `Embeddings` de LangChain.

L'agent et les tools ne connaissent jamais Vertex AI, OpenAI ou autre — ils appellent juste `get_llm()`. Changer de provider = un `elif` dans la factory, zéro modification au code métier.

---

## 3. Base de données unifiée : PostgreSQL + pgvector

**Choix** : un seul PostgreSQL pour les données transactionnelles (`clients`, `transactions`) ET le stockage vectoriel (`procedures` avec `pgvector`), plutôt qu'une base vectorielle dédiée (Pinecone, Weaviate…).

Ça évite un service de plus à opérer, et pgvector est suffisant pour les volumes de ce projet. La même connexion sert aux deux usages.

---

## 4. Recherche hybride : dense + sparse + RRF

**Choix** : combiner recherche vectorielle (dense) et full-text PostgreSQL (sparse) fusionnées par Reciprocal Rank Fusion, plutôt que du dense seul.

### Comment ça marche

| | Dense | Sparse |
|---|---|---|
| **Qui calcule** | Python (Vertex AI) | PostgreSQL automatiquement |
| **Quand** | Au moment de l'insert Python | Au moment de l'insert SQL (`GENERATED ALWAYS AS`) |
| **Ce qu'il stocke** | Vecteur de 768 floats | Index inversé de mots racinisés (dictionnaire `french`) |
| **Recherche** | Similarité cosinus (`<=>`) | Matching de mots-clés (`@@`) |
| **Fort sur** | Synonymes, sémantique | Termes exacts (`SEPA`, `IBAN`, `RIB`, noms propres) |

La colonne `content_tsv` est générée et maintenue automatiquement par PostgreSQL — aucun code Python nécessaire pour le sparse, juste l'indexation dense.

**RRF** (Reciprocal Rank Fusion) : chaque canal classe ses 20 meilleurs candidats, le score final est `1/(60 + rang_dense) + 1/(60 + rang_sparse)`. Pas de poids à tuner, robuste par construction.

---

## 5. Modèle d'embedding : text-multilingual-embedding-002 (Vertex AI)

**Choix** : `text-multilingual-embedding-002` (768 dims) plutôt que `text-embedding-004` (1536 dims).

Natif multilingue, dimension plus légère, suffisant pour des procédures bancaires en français. Aucun compromis sur la qualité de récupération pour ce cas d'usage.

---

## 6. Chunking : RecursiveCharacterTextSplitter (512 / 64)

**Choix** : chunks de 512 tokens avec 64 de chevauchement.

Adapté aux procédures Markdown : assez grand pour conserver le contexte d'une étape, assez petit pour que le chunk retourné au LLM soit précis et pas bruité.

---

## 7. Observabilité : Langfuse v2 auto-hébergé + décorateur `@observe`

### Choix de la plateforme

**Langfuse v2 self-hosted** via Docker, plutôt que :
- Langfuse cloud : nécessite d'envoyer des données à un service externe — problématique dans un contexte bancaire
- Langfuse v3 : nécessite ClickHouse + MinIO + Redis en plus de PostgreSQL — surcharge opérationnelle injustifiée pour un POC
- Phoenix/Arize : outillage différent, moins intégré à LangChain/LangGraph

Langfuse v2 ne nécessite qu'un PostgreSQL dédié. Un service `langfuse` + `langfuse-postgres` dans `docker-compose.yaml` suffisent. L'UI est disponible sur `http://localhost:3000`.

### Choix de l'intégration : `@observe` plutôt que `CallbackHandler`

Langfuse propose deux modes d'intégration LangChain :
- `langfuse.callback.CallbackHandler` — s'injecte dans `agent.invoke(config={"callbacks": [...]})` et capture automatiquement tous les appels LLM imbriqués
- `langfuse.decorators.observe` — décorateur Python standard, sans dépendance LangChain

Le `CallbackHandler` a été écarté car il importe `langchain.callbacks.base` qui a été **supprimé dans LangChain 1.x** (le projet est sur `langchain==1.3.9`). L'import échoue à la compilation, rendant le module inutilisable.

Le décorateur `@observe` est utilisé à la place : il wrape la fonction d'exécution d'un tour de conversation dans `cli.py` et crée une trace par échange. Pour le mode LangGraph, le graph est streamé via `agent.stream(stream_mode="updates")` qui expose les événements nœud par nœud — chaque nœud (`call_model`, `tools`) est tracé comme un span enfant via un `@observe` imbriqué.

```
Trace : bforbank-langgraph          ← @observe sur le tour de conversation
├── Span : call_model               ← @observe sur l'événement de stream
├── Span : tools
└── Span : call_model
```

### Optionnalité

Si `LANGFUSE_PUBLIC_KEY` est absent du `.env`, aucun callback ni décorateur n'est instancié — l'agent tourne normalement. Le branchement conditionnel est dans `cli.py` uniquement, les tools et agents n'ont aucune dépendance à Langfuse.

---

## 9. Deux variantes d'agent : ReAct vs LangGraph custom

**Choix** : deux implémentations distinctes coexistent — `agent_react.py` et `agent_langgraph.py` — sélectionnables via `cli.py --mode react|langgraph`.

### ReAct (prebuilt)

`create_react_agent(llm, tools, prompt=...)` de LangGraph. L'agent observe → réfléchit → appelle un tool → observe → … jusqu'à avoir une réponse finale. Le LLM pilote librement l'ordre et la combinaison des tools. Code minimal, comportement émergent.

### LangGraph custom (StateGraph)

Même logique, mais le graphe est défini nœud par nœud :

```
START → call_model → (tool_calls ?) → tools → call_model → … → END
```

L'arête conditionnelle `_should_use_tools` est explicite. Chaque nœud est modifiable indépendamment : ajouter un nœud de masquage PII avant `call_model`, un nœud de logging structuré après `tools`, ou une étape de synthèse dédiée ne nécessite qu'une ligne d'`add_node` + une arête.

### Pourquoi garder les deux

L'objectif est de les comparer quantitativement une fois l'évaluation Ragas en place (Phase 5). ReAct sera la baseline ; LangGraph custom permettra d'expérimenter des contraintes de routing sans modifier les tools. Les tools (`retrieve_procedures`, `query_client_data`) sont partagés entre les deux — seule la structure du graph diffère.

### Self-correction SQL

La boucle de correction (max 3 essais) est encapsulée dans `sql_tool.py` et fonctionne identiquement dans les deux modes. Ce choix simplifie le graphe LangGraph custom — si on voulait rendre la correction visible dans le graphe (nœud `sql_retry`), c'est une évolution possible sans casser les tools.
