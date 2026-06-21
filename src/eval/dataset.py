"""
Jeu de données statique — 9 questions d'évaluation.

Les expected_output SQL sont dérivés des données seed figées (seed.sql).
Les retrieval_query sont les requêtes passées au retriever pour obtenir le contexte RAG.
"""

RAG_CASES = [
    {
        "name": "rag_litige",
        "input": "Quelle est la procédure pour contester une transaction CB en litige ?",
        "retrieval_query": "procédure litige transaction CB contestation",
    },
]

# expected_output = vérité terrain tirée du seed.sql (données figées)
SQL_CASES = [
    {
        "name": "sql_solde",
        "input": "Quel est le solde actuel de Marie Martin ?",
        "expected_output": "Marie Martin a un solde de 3450 euros.",
    },
]

MIXED_CASES = [
    {
        "name": "mixed_anomalies_martin",
        "input": (
            "Analysez le compte de Marie Martin et identifiez les transactions problématiques. "
            "Quelle procédure BforBank appliquer ?"
        ),
        "retrieval_query": "procédure litige transaction double débit CB",
    },
]
