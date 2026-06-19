# Procédure : Opposition sur Carte Bancaire

**Référence** : [CONF-BFB-003](https://confluence.bforbank.internal/pages/opposition-carte)
**Version** : 2.0 — mise à jour le 10/01/2025
**Propriétaire** : Service Cartes & Moyens de Paiement

---

## 1. Contexte

Une opposition sur carte bancaire est une mesure conservatoire qui bloque immédiatement toute utilisation d'une carte de paiement BforBank.
Elle peut être initiée par le client ou par la banque (en cas de détection de fraude).

---

## 2. Motifs d'opposition

| Code motif | Libellé | Initiateur |
|------------|---------|------------|
| `PERTE` | Perte de la carte | Client |
| `VOL` | Vol de la carte | Client |
| `UTILISATION_FRAUDULEUSE` | Transactions non reconnues | Client ou Banque |
| `DETERIORATION` | Carte endommagée (chip défectueux) | Client |
| `INITIATIVE_BANQUE` | Risque détecté par scoring fraude | Banque |

---

## 3. Étapes de mise en opposition

### 3.1 — Vérification d'identité (obligatoire)

Avant toute action, vérifier l'identité du client par **deux facteurs** :
1. Date de naissance **et**
2. Les 4 derniers chiffres du numéro de carte **ou** la dernière transaction mémorisée

> ⚠️ En cas d'échec de vérification d'identité : ne pas procéder à l'opposition et escalader au superviseur.

### 3.2 — Mise en opposition

1. Saisir l'opposition dans le système de gestion des cartes (SGC)
2. Enregistrer : date/heure, motif, identifiant conseiller
3. Notifier Visa/Mastercard via le réseau interbancaire (automatique via SGC)
4. Confirmer l'opposition au client par SMS et email

**Délai de traitement** : opposition effective en **moins de 5 minutes** après saisie.

### 3.3 — Émission de la carte de remplacement

- Carte de remplacement envoyée automatiquement sous **5 à 7 jours ouvrés**
- Adresse de livraison : adresse principale enregistrée (vérifier avant confirmation)
- Le client peut demander une livraison express (48h) — frais de 15 € à sa charge

---

## 4. Après l'opposition

### 4.1 — Remboursement des transactions frauduleuses

Si le motif est `UTILISATION_FRAUDULEUSE` ou `VOL` :
- Ouvrir un dossier litige pour chaque transaction contestée (→ voir procédure [CONF-BFB-002](https://confluence.bforbank.internal/pages/litige-transaction))
- Remboursement provisoire sous 24h pour les transactions < 1 500 €

### 4.2 — Déclaration de vol (recommandée)

Informer le client qu'il est **fortement recommandé** de déposer une plainte auprès des autorités (police/gendarmerie).
Le numéro de plainte devra être fourni pour les dossiers > 1 500 €.

---

## 5. Cas particuliers

- **Carte récupérée après opposition** : l'opposition ne peut pas être levée. Une nouvelle carte doit être émise.
- **Opposition hors horaires conseiller** : disponible 24h/24 via le serveur vocal automatique (0 800 XXX XXX) ou l'application mobile.
- **Client à l'étranger** : privilégier la livraison à une agence partenaire (réseau Visa Assistance).

---

## 6. Traçabilité

Tout événement lié à une opposition est journalisé dans le système avec horodatage, identifiant conseiller et motif.
Conservation des logs : 5 ans (obligation réglementaire).
