# Procédure : Remboursement des Frais Bancaires

**Référence** : [CONF-BFB-001](https://confluence.bforbank.internal/pages/frais-bancaires)
**Version** : 2.4 — mise à jour le 01/03/2025
**Propriétaire** : Direction des Opérations Bancaires

---

## 1. Contexte

BforBank peut procéder au remboursement de certains frais bancaires sous conditions strictes.
Cette procédure s'applique aux frais de tenue de compte, frais d'incident de paiement, commissions d'intervention et frais de virement SEPA.

---

## 2. Critères d'éligibilité

Un client est éligible à un remboursement si **toutes** les conditions suivantes sont réunies :

- Le client est titulaire d'un compte actif depuis au moins **3 mois**
- La demande est formulée dans les **60 jours** suivant le prélèvement du frais
- Le client n'a pas déjà bénéficié d'un remboursement de frais dans les **12 derniers mois** (règle du remboursement unique annuel)
- Le motif de la demande entre dans l'une des catégories remboursables (voir §3)

---

## 3. Catégories de frais remboursables

| Catégorie | Condition de remboursement | Montant max remboursable |
|-----------|---------------------------|--------------------------|
| Frais d'incident de paiement | Premier incident sur les 12 derniers mois | 100 % du frais |
| Commission d'intervention | Erreur avérée de la banque | 100 % |
| Frais de virement SEPA | Erreur de libellé de notre part | 100 % |
| Frais de tenue de compte | Geste commercial (décision N+1) | 50 % max |

---

## 4. Étapes de traitement

1. **Vérifier l'éligibilité** : consulter l'historique des remboursements dans le CRM (champ `remboursements_anterieurs`)
2. **Identifier la catégorie du frais** : se référer au libellé de la transaction (ex : `FRAIS INCIDENT CB`, `COMM INTERVENTION`)
3. **Valider le délai de 60 jours** : comparer la date du frais avec la date de la demande
4. **Effectuer le remboursement** :
   - Montant ≤ 50 € : conseiller peut valider seul
   - Montant > 50 € : validation requise par le superviseur
5. **Tracer l'opération** dans le CRM avec le motif et le montant remboursé
6. **Informer le client** par email automatique via le module de notification

---

## 5. Cas de refus

Le remboursement est **refusé** si :
- Le client a déjà obtenu un remboursement dans les 12 derniers mois
- Le frais est lié à un découvert non autorisé répété (> 3 fois sur 6 mois)
- La demande dépasse le délai de 60 jours
- Le frais est réglementaire et non discrétionnaire

En cas de refus, informer le client par écrit en citant le motif précis.

---

## 6. Escalade

Si le client conteste le refus, ouvrir un ticket de réclamation formelle (`TYPE: RECLAMATION_FRAIS`) et transmettre au service Médiation.
