"""
Jeu de données statique — 4 questions d'évaluation.

Chaque cas a un expected_output qui constitue la vérité terrain.
Les expected_output SQL sont dérivés des données seed figées (seed.sql).
Les expected_output RAG sont dérivés des fichiers data/procedures/*.md.
"""

RAG_CASES = [
    {
        "name": "rag_litige",
        "input": "Quelle est la procédure pour contester une transaction CB en litige ?",
        "retrieval_query": "procédure litige transaction CB contestation",
        "expected_output": (
            "La procédure CONF-BFB-002 encadre la contestation de transaction CB. "
            "Étapes : identifier la transaction, vérifier les délais réglementaires "
            "(13 mois pour une transaction non autorisée, 8 semaines pour erreur commerçant), "
            "qualifier le motif (NON_AUTORISE, DOUBLE_DEBIT, MONTANT_ERRONE ou NON_LIVRE), "
            "collecter les justificatifs, instruire le dossier sous 15 jours ouvrés. "
            "Si montant > 150€ et motif NON_AUTORISE : bloquer la carte immédiatement."
        ),
    },
]

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
        "input": "Faites un bilan du compte de Marie Martin et dites-moi ce qu'il faut faire.",
        "retrieval_query": "procédure litige transaction double débit CB",
        "expected_output": (
            "Marie Martin a 3 transactions problématiques : "
            "deux débits identiques ZARA BOUTIQUE OPERA de 245€ en statut LITIGE (double débit), "
            "et un achat ELECTRONIQUE ISTANBUL de 1850€ en statut SUSPICIEUX. "
            "Procédure CONF-BFB-002 : remboursement immédiat du doublon (DOUBLE_DEBIT section 3.2), "
            "mise en opposition carte et ouverture dossier fraude pour la transaction suspecte "
            "(montant > 150€, motif NON_AUTORISE → blocage obligatoire section 3.2)."
        ),
    },
]

# Question "both" : les deux besoins (SQL + RAG) sont explicites dès la question initiale.
# Idéale pour le LangGraph fan-out qui construit les deux queries en parallèle.
BOTH_CASES = [
    {
        "name": "both_solvabilite_leroy",
        "input": (
            "Sophie Leroy souhaite contracter un prêt de 15 000€. "
            "Quels sont ses revenus mensuels et quelle est la procédure d'analyse de solvabilité ?"
        ),
        "retrieval_query": "procédure analyse solvabilité prêt revenus",
        "expected_output": (
            "Aucun revenu mensuel récurrent identifié pour Sophie Leroy dans la base transactionnelle. "
            "Procédure applicable : CONF-BFB-004 (analyse de solvabilité). "
            "Pour un prêt de 15 000€, la décision requiert l'accord d'un superviseur "
            "et la validation du scoring automatique. "
            "Taux d'endettement cible < 33%. "
            "Documents requis : justificatif de revenus, RIB, justificatif de domicile < 3 mois."
        ),
    },
]
