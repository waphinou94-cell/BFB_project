# Procédure : Contestation d'une Transaction

**Référence** : [CONF-BFB-002](https://confluence.bforbank.internal/pages/litige-transaction)
**Version** : 3.1 — mise à jour le 15/04/2025
**Propriétaire** : Service Litiges & Réclamations

---

## 1. Contexte

Cette procédure encadre le traitement des contestations de transactions émises par les clients BforBank.
Elle couvre les transactions par carte bancaire (CB), les virements SEPA et les prélèvements automatiques.

---

## 2. Délais réglementaires de contestation

| Type de transaction | Délai de contestation | Base réglementaire |
|--------------------|----------------------|--------------------|
| Paiement CB non autorisé | 13 mois | DSP2 Art. 76 |
| Paiement CB autorisé (erreur commerçant) | 8 semaines | Chargeback Visa/MC |
| Prélèvement SEPA non autorisé | 13 mois | Règlement SEPA |
| Prélèvement SEPA autorisé | 8 semaines | Règlement SEPA |
| Virement mal exécuté | 13 mois | DSP2 Art. 89 |

---

## 3. Étapes de traitement

### 3.1 — Qualification initiale (< 24h)

1. **Identifier la transaction** : date, montant, libellé, type (CB / virement / prélèvement)
2. **Vérifier le délai** : la contestation est-elle dans les délais réglementaires ?
3. **Qualifier le motif** :
   - `NON_AUTORISE` : le client affirme ne pas avoir effectué la transaction
   - `DOUBLE_DEBIT` : même transaction prélevée deux fois
   - `MONTANT_ERRONE` : le montant débité diffère du montant autorisé
   - `NON_LIVRE` : bien ou service non livré malgré le paiement
   - `ABONNEMENT_RESILIÉ` : prélèvement après résiliation d'un abonnement

### 3.2 — Actions immédiates

- Si motif `NON_AUTORISE` et montant > 150 € → **bloquer la carte immédiatement** et ouvrir un dossier fraude
- Si motif `NON_AUTORISE` et montant ≤ 150 € → proposer le remboursement provisoire sous 24h (règle DSP2)
- Si motif `DOUBLE_DEBIT` → remboursement immédiat du doublon

### 3.3 — Instruction du dossier (J+1 à J+15)

1. Collecter les justificatifs client (relevé, ticket de caisse, email de confirmation)
2. Soumettre la demande de chargeback auprès de Visa/Mastercard si applicable
3. Contacter le commerçant pour obtention des preuves de transaction
4. Décision dans un délai maximum de **15 jours ouvrés**

### 3.4 — Clôture

- **Remboursement validé** : créditer le compte client, notifier par email, clore le dossier
- **Remboursement refusé** : notifier le client avec justification écrite, informer des voies de recours (Médiateur bancaire)

---

## 4. Montants et responsabilités

- Franchise légale en cas de perte/vol de carte : **50 €** (hors négligence grave du client)
- Négligence grave (ex : code PIN communiqué) → aucun remboursement
- Carte non reçue / usurpée à distance → remboursement intégral

---

## 5. Escalade

Ticket de type `LITIGE_TRANSACTION` dans le CRM.
Pour les montants > 5 000 € : transmission obligatoire au Département Juridique.
