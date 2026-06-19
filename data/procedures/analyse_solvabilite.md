# Procédure : Analyse de Solvabilité

**Référence** : [CONF-BFB-004](https://confluence.bforbank.internal/pages/analyse-solvabilite)
**Version** : 1.8 — mise à jour le 20/02/2025
**Propriétaire** : Direction du Risque Crédit

---

## 1. Contexte

L'analyse de solvabilité est réalisée avant toute décision d'octroi de crédit (prêt personnel, découvert autorisé, crédit renouvelable) ou de révision des conditions tarifaires d'un client.
Elle repose sur l'examen de la situation financière réelle du client à partir des données transactionnelles.

---

## 2. Indicateurs clés à analyser

### 2.1 — Revenus

- **Revenu net mensuel moyen** : calculé sur les 3 derniers mois à partir des virements récurrents entrants (libellé contenant `SALAIRE`, `VIREMENT EMPLOYEUR`, `PENSION`, `ALLOCATION`)
- **Stabilité des revenus** : écart-type < 15 % → revenus stables ; > 15 % → revenus variables (mention obligatoire dans le dossier)

### 2.2 — Charges fixes

| Type de charge | Identification dans les transactions |
|----------------|--------------------------------------|
| Loyer | Prélèvement récurrent > 400 € avec libellé `LOYER` ou `AGENCE` |
| Crédits en cours | Prélèvements avec libellé `CREDIT`, `MENSUALITE`, `CETELEM`, `COFIDIS` |
| Assurances | Prélèvements récurrents < 150 € avec libellé `ASSURANCE` |

### 2.3 — Taux d'endettement

```
Taux d'endettement = (Charges fixes mensuelles / Revenu net mensuel) × 100
```

| Taux | Décision |
|------|----------|
| < 33 % | Solvable — accord possible |
| 33 % à 40 % | Zone grise — étude approfondie requise |
| > 40 % | Non solvable — refus recommandé |

### 2.4 — Comportement de compte

- **Solde moyen sur 3 mois** : positif requis
- **Incidents de paiement** : 0 incident sur 6 mois → favorable ; 1 ou 2 incidents → mitigé ; > 2 incidents → défavorable
- **Utilisation du découvert** : si découvert utilisé > 80 % des jours du mois → signal négatif

---

## 3. Étapes de l'analyse

1. **Collecter les données** : extraire les 3 derniers mois de transactions depuis le système transactionnel
2. **Calculer les revenus** : identifier et sommer les entrées récurrentes de type salaire/pension
3. **Identifier les charges fixes** : lister les prélèvements récurrents et les mensualités de crédit
4. **Calculer le taux d'endettement**
5. **Analyser le comportement de compte** : incidents, utilisation du découvert, solde moyen
6. **Produire la synthèse** avec recommandation motivée

---

## 4. Décision et responsabilités

| Montant demandé | Décisionnaire |
|-----------------|---------------|
| ≤ 5 000 € | Conseiller client (si taux < 33 %) |
| 5 001 € à 25 000 € | Superviseur + validation scoring automatique |
| > 25 000 € | Comité Crédit |

---

## 5. Documents requis pour le dossier

- Justificatif de revenus (3 derniers bulletins de salaire ou avis d'imposition)
- RIB du compte principal
- Justificatif de domicile < 3 mois
- Pour les indépendants : 2 derniers bilans comptables

---

## 6. Durée de validité de l'analyse

Une analyse de solvabilité est valable **3 mois**. Au-delà, une nouvelle analyse doit être conduite avant toute décision d'octroi.
