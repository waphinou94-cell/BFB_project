-- ============================================================
-- BforBank — Schéma transactionnel
-- Compatible pgvector (extension activée dans la même base)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- pour la recherche hybride (Phase 3)

-- ------------------------------------------------------------
-- Table : clients
-- ------------------------------------------------------------
CREATE TABLE clients (
    id              SERIAL PRIMARY KEY,
    nom             VARCHAR(100)    NOT NULL,
    prenom          VARCHAR(100)    NOT NULL,
    email           VARCHAR(255)    UNIQUE NOT NULL,
    telephone       VARCHAR(20),
    date_naissance  DATE            NOT NULL,
    date_ouverture  DATE            NOT NULL DEFAULT CURRENT_DATE,
    solde           NUMERIC(12, 2)  NOT NULL DEFAULT 0.00,
    decouvert_autorise NUMERIC(10, 2) NOT NULL DEFAULT 0.00
);

-- ------------------------------------------------------------
-- Table : transactions
-- ------------------------------------------------------------
CREATE TABLE transactions (
    id              SERIAL PRIMARY KEY,
    client_id       INTEGER         NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    date_transaction TIMESTAMP      NOT NULL,
    montant         NUMERIC(10, 2)  NOT NULL,  -- négatif = débit, positif = crédit
    libelle         VARCHAR(255)    NOT NULL,
    type            VARCHAR(50)     NOT NULL   -- 'CB', 'VIREMENT', 'PRELEVEMENT', 'FRAIS'
        CHECK (type IN ('CB', 'VIREMENT', 'PRELEVEMENT', 'FRAIS')),
    statut          VARCHAR(50)     NOT NULL DEFAULT 'OK'
        CHECK (statut IN ('OK', 'LITIGE', 'SUSPICIEUX', 'REJETE'))
);

-- Index pour les requêtes fréquentes
CREATE INDEX idx_transactions_client_id ON transactions(client_id);
CREATE INDEX idx_transactions_date ON transactions(date_transaction DESC);
CREATE INDEX idx_transactions_statut ON transactions(statut);
