"""Fournit le DDL du schéma transactionnel BforBank au LLM pour la génération SQL."""

SCHEMA_DDL = """
-- Table: clients
CREATE TABLE clients (
    id                 SERIAL PRIMARY KEY,
    nom                VARCHAR(100)   NOT NULL,
    prenom             VARCHAR(100)   NOT NULL,
    email              VARCHAR(255)   NOT NULL,
    telephone          VARCHAR(20),
    date_naissance     DATE           NOT NULL,
    date_ouverture     DATE           NOT NULL,
    solde              NUMERIC(12, 2) NOT NULL,
    decouvert_autorise NUMERIC(10, 2) NOT NULL
);

-- Table: transactions
-- montant : négatif = débit, positif = crédit
-- type    : 'CB' | 'VIREMENT' | 'PRELEVEMENT' | 'FRAIS'
-- statut  : 'OK' | 'LITIGE' | 'SUSPICIEUX' | 'REJETE'
CREATE TABLE transactions (
    id               SERIAL PRIMARY KEY,
    client_id        INTEGER        NOT NULL REFERENCES clients(id),
    date_transaction TIMESTAMP      NOT NULL,
    montant          NUMERIC(10, 2) NOT NULL,
    libelle          VARCHAR(255)   NOT NULL,
    type             VARCHAR(50)    NOT NULL,
    statut           VARCHAR(50)    NOT NULL
);
"""


def get_schema() -> str:
    return SCHEMA_DDL
