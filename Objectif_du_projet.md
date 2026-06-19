# 🏦 Cas Pratique — Agent IA Copilote pour BforBank

> **Rôle** : Tech Lead IA · **Durée d'implémentation** : 2h max · **Restitution** : 1h d'entretien

---

## 🏢 Contexte de l'entreprise

**BforBank** est une banque digitale en forte croissance. Elle finalise une première phase de construction à la suite d'un lancement commercial en 2023, et doit désormais :

- Développer son portefeuille de produits (épargne, assurance, etc.)
- Atteindre ses objectifs d'acquisition

Avec près de **500 000 clients**, la complexité des demandes *(litiges fraudes, analyses de solvabilité, frais bancaires…)* **sature le service client**.

---

## 🎯 Objectif du cas pratique

Réduire le **Temps Moyen de Traitement** des requêtes tout en augmentant la pertinence des réponses, via un Agent IA capable d'unifier :

| Source | Type | Description |
|--------|------|-------------|
| 📄 Procédures | Connaissance froide | Règles métier, documentation Confluence |
| 💳 Transactions | Donnée chaude | Historique transactionnel des clients |

---

## 👤 Rôle du candidat

En tant que **Tech Lead IA**, vous devez concevoir et prototyper un agent conversationnel **Agentic RAG** capable de :

1. **🔍 Recherche Documentaire (RAG)** — Indexer et interroger une base de connaissances *(ex : procédures Confluence sur le traitement des fraudes)*
2. **🗄️ Analyse de Données (Text-to-SQL)** — Interroger un schéma de base de données transactionnelle (PostgreSQL) pour extraire l'historique d'un client
3. **🧠 Raisonnement & Synthèse** — Croiser les deux sources pour proposer une réponse argumentée au conseiller

---

## 📦 Livrables

### 1. L'Implémentation

> ℹ️ Ne cherchez pas la perfection visuelle, mais la **clarté architecturale**.

Votre dépôt GitHub doit contenir :

| Fichier / Répertoire | Description |
|----------------------|-------------|
| `docker-compose.yaml` | Lance une base PostgreSQL locale avec les données transactionnelles anonymisées |
| `data/procedures/` | Fichiers Markdown décrivant les règles métier *(remboursement de frais, détection de fraude…)* |
| `src/` | Code source de l'agent *(Python / LangChain / LlamaIndex ou autre)* |
| `data/mock/` | Jeu de données : fichiers Markdown + script SQL pour le schéma transactionnel |
| `README.md` | Documentation production-ready |

#### 📋 Contenu du README Production-Ready

**Instructions d'installation**

**Schéma de l'architecture technique** *(Mermaid.js ou image)*

**Agentic Routing & Orchestration** :

- 🔎 **RAG** — Extraire les procédures applicables
- 🔄 **Text-to-SQL avec Boucle de Self-Correction** — Traduire le besoin en SQL, exécuter la requête. Si une erreur SQL survient, l'agent analyse l'erreur et **corrige sa requête de manière autonome**
- 📝 **Synthèse finale** — Réponse argumentée pour le conseiller, citant explicitement :
  - La procédure de référence *(lien Confluence fictif)*
  - Les données transactionnelles clés ayant servi au raisonnement

**🔒 Sécurité Bancaire — PII Protection** :

> ⚠️ La fuite de données personnelles (PII) vers des LLM externes est **interdite**.

Proposer un modèle **local** pour la détection et le masquage qui :
1. Anonymise la requête avant envoi aux APIs LLM
2. Rétablit les valeurs d'origine localement avant l'affichage

**📊 Observabilité & Évaluation** :

- **Traçabilité complète** des étapes de réflexion *(logs d'exécution, traces Langfuse / Phoenix)*
- **Stratégie d'évaluation quantitative** *(Ragas / DeepEval)* pour prévenir les régressions lors des mises à jour de prompts ou de modèles

---

### 2. La Restitution *(1h d'entretien)*

Le candidat présentera son travail devant l'**Architecte Data** et le **Tribe Lead IA** :

| # | Segment | Durée | Contenu |
|---|---------|-------|---------|
| 1 | 🎬 Démo | 10 min | Parcours d'une requête complexe de bout en bout |
| 2 | 🏗️ Conception Technique | 20 min | Justification de l'approche *(Agent vs Chain, stratégie d'indexation, gestion de la mémoire)* |
| 3 | 🚀 Vision "Scale & Ops" | 20 min | Du POC à la production *(Observabilité, évaluation hallucinations, CI/CD, scalabilité sur Google Cloud)* |
| 4 | ❓ Q&A | 10 min | Questions libres du jury |

---

## 📬 Contacts & Partage

Le lien vers le dépôt GitHub sera partagé avec :

- **Anne-Charlotte Maertens** — [anne-charlotte.maertens@bforbank.com](mailto:anne-charlotte.maertens@bforbank.com)
- **Baptiste Derré** — [baptiste.derre@bforbank.com](mailto:baptiste.derre@bforbank.com)

> Ce dépôt sera évalué par l'**Architecte Data** *(évaluation technique)* et le **Tribe Lead IA** *(évaluation fonctionnelle)* en vue de la restitution.