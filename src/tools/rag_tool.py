"""Tool RAG : recherche les procédures internes BforBank via l'index hybride."""

from langchain_core.tools import tool

from src.indexer.retriever import retrieve


@tool
def retrieve_procedures(query: str) -> str:
    """Recherche les procédures internes BforBank applicables à la situation décrite.

    Utiliser pour toute question sur les règles métier : remboursement de frais,
    litiges, opposition carte, analyse de solvabilité.

    Args:
        query: Description de la situation ou de la procédure recherchée.

    Returns:
        Les procédures pertinentes avec leur source (lien Confluence fictif).
    """
    results = retrieve(query, k=5)
    if not results:
        return "Aucune procédure trouvée pour cette requête."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"### Procédure {i} [Source: {r['source']}]\n\n{r['content']}")

    return "\n\n---\n\n".join(parts)
