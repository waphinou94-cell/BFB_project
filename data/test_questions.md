# 🧪 Questions de test — Agent BforBank

> Ces questions couvrent les 3 cas d'usage de l'agent :
> - **❄️ Froide** : réponse basée uniquement sur les procédures (RAG)
> - **🔥 Chaude** : réponse basée uniquement sur les données transactionnelles (Text-to-SQL)
> - **🔄 Mixte** : nécessite les deux sources croisées

---

## ❄️ Données froides uniquement (procédures)

**Q1** — *"Quels sont les délais pour contester un prélèvement SEPA non autorisé ?"*
> Attendu : procédure litige_transaction.md → 13 mois (DSP2)

**Q2** — *"Est-ce qu'un client peut faire rembourser un frais d'incident si c'était son deuxième cette année ?"*
> Attendu : procédure remboursement_frais.md → non, règle du remboursement unique annuel

**Q3** — *"Quelles informations dois-je vérifier avant de faire une opposition sur carte ?"*
> Attendu : procédure opposition_carte.md → double vérification d'identité (date naissance + 4 derniers chiffres)

---

## 🔥 Données chaudes uniquement (transactions)

**Q4** — *"Montre-moi les 5 dernières transactions de Marie Martin."*
> Attendu : SQL SELECT sur transactions WHERE client_id = 2 ORDER BY date DESC LIMIT 5

**Q5** — *"Quel est le revenu mensuel moyen de Sophie Leroy sur les 3 derniers mois ?"*
> Attendu : SQL SUM des virements entrants de type SALAIRE pour client_id = 4, moyenné sur 3 mois

**Q6** — *"Pierre Bernard a-t-il des transactions suspectes récentes ?"*
> Attendu : SQL SELECT WHERE statut = 'SUSPICIEUX' AND client_id = 3 ORDER BY date DESC

---

## 🔄 Données mixtes (procédures + transactions)

**Q7** — *"Jean Dupont a payé des frais d'incident il y a 45 jours. Peut-il en obtenir le remboursement ?"*
> Attendu :
> - SQL : retrouver le frais (35€ + 18.50€), vérifier qu'il n'y a pas d'autre remboursement dans les 12 mois
> - RAG : procédure remboursement_frais.md → critères d'éligibilité
> - Synthèse : oui si premier incident → remboursable à 100 %, conseiller peut valider seul (< 50€)

**Q8** — *"Marie Martin conteste un double débit de 245€ chez Zara il y a 10 jours. Comment dois-je traiter ça ?"*
> Attendu :
> - SQL : confirmer le double débit (2 transactions identiques en statut LITIGE)
> - RAG : procédure litige_transaction.md → motif DOUBLE_DEBIT → remboursement immédiat du doublon
> - Synthèse : procédure claire, action immédiate, montant et date confirmés

**Q9** — *"Pierre Bernard signale le vol de sa carte. Que dois-je faire et y a-t-il des transactions à contester ?"*
> Attendu :
> - SQL : transactions SUSPICIEUX des 7 derniers jours (3 transactions pour ~995€)
> - RAG : procédure opposition_carte.md → vérifier identité, mettre en opposition, ouvrir dossier litige pour chaque transaction suspecte
> - Synthèse : étapes ordonnées + liste des transactions à contester avec montants

**Q10** — *"Sophie Leroy demande un prêt de 15 000€. Est-elle solvable ?"*
> Attendu :
> - SQL : calculer revenus (4100€/mois), charges fixes (1200+380+95 = 1675€), taux endettement (40.8%)
> - RAG : procédure analyse_solvabilite.md → taux > 40% → zone refus recommandé, décision superviseur
> - Synthèse : taux calculé explicitement, recommandation motivée avec référence à la procédure
