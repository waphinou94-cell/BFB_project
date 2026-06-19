-- ============================================================
-- BforBank — Données de test (mock data)
-- 4 clients, chacun calibré pour tester une procédure précise
-- ============================================================

-- ------------------------------------------------------------
-- Clients
-- ------------------------------------------------------------
INSERT INTO clients (nom, prenom, email, telephone, date_naissance, date_ouverture, solde, decouvert_autorise) VALUES
-- Client 1 : demande de remboursement de frais (test procédure remboursement_frais)
('Dupont', 'Jean', 'jean.dupont@email.fr', '0612345678', '1985-03-15', '2022-01-10', 1240.50, 500.00),

-- Client 2 : transaction contestée / litige CB (test procédure litige_transaction)
('Martin', 'Marie', 'marie.martin@email.fr', '0698765432', '1992-07-22', '2021-06-01', 3450.00, 200.00),

-- Client 3 : opposition carte suite à vol (test procédure opposition_carte)
('Bernard', 'Pierre', 'pierre.bernard@email.fr', '0756781234', '1978-11-08', '2023-03-15', 680.20, 0.00),

-- Client 4 : demande de prêt / analyse de solvabilité (test procédure analyse_solvabilite)
('Leroy', 'Sophie', 'sophie.leroy@email.fr', '0634567890', '1990-05-30', '2020-09-20', 5200.80, 1000.00);

-- ------------------------------------------------------------
-- Transactions — Client 1 : Jean Dupont
-- Contexte : frais d'incident ponctuel, premier de l'année
-- ------------------------------------------------------------
INSERT INTO transactions (client_id, date_transaction, montant, libelle, type, statut) VALUES
(1, NOW() - INTERVAL '90 days', 2400.00,  'VIREMENT SALAIRE TECHCORP',         'VIREMENT',    'OK'),
(1, NOW() - INTERVAL '88 days', -850.00,  'LOYER MARS AGENCE IMMOBILIER PARIS', 'PRELEVEMENT', 'OK'),
(1, NOW() - INTERVAL '85 days', -65.00,   'ASSURANCE HABITATION AXA',           'PRELEVEMENT', 'OK'),
(1, NOW() - INTERVAL '80 days', -120.00,  'COURSES CARREFOUR',                  'CB',          'OK'),
(1, NOW() - INTERVAL '60 days', 2400.00,  'VIREMENT SALAIRE TECHCORP',         'VIREMENT',    'OK'),
(1, NOW() - INTERVAL '58 days', -850.00,  'LOYER AVRIL AGENCE IMMOBILIER PARIS','PRELEVEMENT', 'OK'),
(1, NOW() - INTERVAL '45 days', -35.00,   'FRAIS INCIDENT PAIEMENT CB',         'FRAIS',       'OK'),
(1, NOW() - INTERVAL '44 days', -18.50,   'COMMISSION INTERVENTION',            'FRAIS',       'OK'),
(1, NOW() - INTERVAL '30 days', 2400.00,  'VIREMENT SALAIRE TECHCORP',         'VIREMENT',    'OK'),
(1, NOW() - INTERVAL '28 days', -850.00,  'LOYER MAI AGENCE IMMOBILIER PARIS',  'PRELEVEMENT', 'OK'),
(1, NOW() - INTERVAL '10 days', -89.99,   'AMAZON MARKETPLACE',                 'CB',          'OK'),
(1, NOW() - INTERVAL '5 days',  -45.00,   'RESTAURANT LE ZINC',                 'CB',          'OK');

-- ------------------------------------------------------------
-- Transactions — Client 2 : Marie Martin
-- Contexte : double débit CB + une transaction suspicieuse
-- ------------------------------------------------------------
INSERT INTO transactions (client_id, date_transaction, montant, libelle, type, statut) VALUES
(2, NOW() - INTERVAL '60 days', 3200.00,  'VIREMENT SALAIRE MINISTERE EDUCATION','VIREMENT',   'OK'),
(2, NOW() - INTERVAL '58 days', -900.00,  'LOYER AVRIL NEXITY',                  'PRELEVEMENT', 'OK'),
(2, NOW() - INTERVAL '55 days', -120.00,  'CREDIT CETELEM MENSUALITE',            'PRELEVEMENT', 'OK'),
(2, NOW() - INTERVAL '40 days', -299.00,  'ACHAT FNAC PARIS 15',                 'CB',          'OK'),
(2, NOW() - INTERVAL '30 days', 3200.00,  'VIREMENT SALAIRE MINISTERE EDUCATION','VIREMENT',   'OK'),
(2, NOW() - INTERVAL '28 days', -900.00,  'LOYER MAI NEXITY',                    'PRELEVEMENT', 'OK'),
(2, NOW() - INTERVAL '15 days', -79.99,   'NETFLIX ABONNEMENT',                  'PRELEVEMENT', 'OK'),
(2, NOW() - INTERVAL '10 days', -245.00,  'ZARA BOUTIQUE OPERA',                 'CB',          'LITIGE'),
(2, NOW() - INTERVAL '10 days', -245.00,  'ZARA BOUTIQUE OPERA',                 'CB',          'LITIGE'),  -- double débit
(2, NOW() - INTERVAL '3 days',  -1850.00, 'ACHAT ELECTRONIQUE ISTANBUL',         'CB',          'SUSPICIEUX');

-- ------------------------------------------------------------
-- Transactions — Client 3 : Pierre Bernard
-- Contexte : transactions normales puis activité suspecte après vol
-- ------------------------------------------------------------
INSERT INTO transactions (client_id, date_transaction, montant, libelle, type, statut) VALUES
(3, NOW() - INTERVAL '60 days', 1900.00,  'VIREMENT SALAIRE BATIMENT PRO',      'VIREMENT',    'OK'),
(3, NOW() - INTERVAL '58 days', -600.00,  'LOYER AVRIL PARTICULIER',             'VIREMENT',    'OK'),
(3, NOW() - INTERVAL '50 days', -80.00,   'ASSURANCE AUTO MAIF',                 'PRELEVEMENT', 'OK'),
(3, NOW() - INTERVAL '35 days', -55.00,   'TOTAL ENERGIES ESSENCE',              'CB',          'OK'),
(3, NOW() - INTERVAL '30 days', 1900.00,  'VIREMENT SALAIRE BATIMENT PRO',      'VIREMENT',    'OK'),
(3, NOW() - INTERVAL '7 days',  -420.00,  'ACHAT TELEPHONIE SFPARK NICE',        'CB',          'SUSPICIEUX'),
(3, NOW() - INTERVAL '6 days',  -380.00,  'CASINO JEU EN LIGNE',                 'CB',          'SUSPICIEUX'),
(3, NOW() - INTERVAL '5 days',  -195.00,  'RETRAIT DAB MARSEILLE',               'CB',          'SUSPICIEUX');

-- ------------------------------------------------------------
-- Transactions — Client 4 : Sophie Leroy
-- Contexte : profil solvable, revenus stables, demande de prêt 15 000€
-- ------------------------------------------------------------
INSERT INTO transactions (client_id, date_transaction, montant, libelle, type, statut) VALUES
(4, NOW() - INTERVAL '90 days', 4100.00,  'VIREMENT SALAIRE CABINET LEROY CONSULTANT','VIREMENT','OK'),
(4, NOW() - INTERVAL '88 days', -1200.00, 'LOYER MARS FONCIA',                   'PRELEVEMENT', 'OK'),
(4, NOW() - INTERVAL '87 days', -380.00,  'MENSUALITE CREDIT AUTO SOFINCO',      'PRELEVEMENT', 'OK'),
(4, NOW() - INTERVAL '85 days', -95.00,   'ASSURANCE VIE GENERALI',              'PRELEVEMENT', 'OK'),
(4, NOW() - INTERVAL '80 days', -250.00,  'COURSES MONOPRIX',                    'CB',          'OK'),
(4, NOW() - INTERVAL '60 days', 4100.00,  'VIREMENT SALAIRE CABINET LEROY CONSULTANT','VIREMENT','OK'),
(4, NOW() - INTERVAL '58 days', -1200.00, 'LOYER AVRIL FONCIA',                  'PRELEVEMENT', 'OK'),
(4, NOW() - INTERVAL '57 days', -380.00,  'MENSUALITE CREDIT AUTO SOFINCO',      'PRELEVEMENT', 'OK'),
(4, NOW() - INTERVAL '55 days', -95.00,   'ASSURANCE VIE GENERALI',              'PRELEVEMENT', 'OK'),
(4, NOW() - INTERVAL '30 days', 4100.00,  'VIREMENT SALAIRE CABINET LEROY CONSULTANT','VIREMENT','OK'),
(4, NOW() - INTERVAL '28 days', -1200.00, 'LOYER MAI FONCIA',                    'PRELEVEMENT', 'OK'),
(4, NOW() - INTERVAL '27 days', -380.00,  'MENSUALITE CREDIT AUTO SOFINCO',      'PRELEVEMENT', 'OK'),
(4, NOW() - INTERVAL '26 days', -95.00,   'ASSURANCE VIE GENERALI',              'PRELEVEMENT', 'OK'),
(4, NOW() - INTERVAL '5 days',  -320.00,  'VOYAGE SNCF TGV PARIS BORDEAUX',      'CB',          'OK');
