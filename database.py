"""
Module de gestion de la base de données SQLite
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

# Nom de la base de données
DB_NAME = "documents.db"

def get_connection() -> sqlite3.Connection:
    """Créer une connexion à la base de données"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
    return conn

def init_database():
    """Initialiser la base de données avec les tables nécessaires"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Table des documents
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                detected_type TEXT NOT NULL,
                detected_category TEXT,
                confidence REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des types de documents
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL
            )
        ''')

        # Table des prompts d'extraction
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS extraction_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                extraction_prompt TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_type) REFERENCES document_types (name)
            )
        ''')

        # Table des extractions de documents
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                extracted_data TEXT NOT NULL,
                llm_used TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        ''')

        # Table des synthèses de financement
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS syntheses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dossier_id TEXT NOT NULL,
                input_documents TEXT NOT NULL,
                synthese_text TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des documents générés
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents_generes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dossier_id TEXT NOT NULL,
                type_document TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                generated_from TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Insérer les types de documents prédéfinis
        document_types = [
            (1, "CV(s) du(des) associés", "Associés"),
            (2, "Compromis de vente", "Object"),
            (3, "Bail ou projet de bail du bien objet de l'acquisition", "Object"),
            (4, "Projet de statuts société emprunteur", "Company"),
            (5, "Organigramme des sociétés de la société emprunteur", "Company"),
            (6, "KBIS société emprunteur", "Company"),
            (7, "Statuts société emprunteur", "Company"),
            (8, "PV d'AG autorisant la société à emprunter", "Company"),
            (9, "Liasses fiscales société emprunteur N-1", "Company"),
            (10, "Liasses fiscales société emprunteur N-2", "Company"),
            (11, "Liasses fiscales société emprunteur N-3", "Company"),
            (12, "Bilan et compte de résultat détaillés de l'emprunteur N-1", "Company"),
            (13, "Bilan et compte de résultat détaillés de l'emprunteur N-2", "Company"),
            (14, "Bilan et compte de résultat détaillés de l'emprunteur N-3", "Company"),
            (15, "Relevé de compte Mois M - 1", "Banque et épargne"),
            (16, "Relevé de compte Mois M - 2", "Banque et épargne"),
            (17, "Relevé de compte Mois M - 3", "Banque et épargne"),
            (18, "Carte d'identité(recto verso) ou Passeport", "Etat civil"),
            (19, "Justificatif de domicile", "Etat civil"),
            (20, "Livret de famille", "Etat civil"),
            (21, "Contrat de mariage", "Etat civil"),
            (22, "Avis d'imposition N - 1", "Revenus"),
            (23, "Avis d'imposition N - 2", "Revenus"),
            (24, "Avis d'imposition N - 3", "Revenus"),
            (25, "Dernière taxe foncière", "Patrimoine immobilier"),
            (26, "Attestation notariée d'acquisition indiquant le prix", "Patrimoine immobilier"),
            (27, "Bail", "Patrimoine immobilier"),
            (28, "Tableau d'amortissement du crédit immobilier", "Patrimoine immobilier"),
            (29, "Dernière déclaration 2044", "Revenus"),
            (30, "Dernier relevé d'épargne", "Banque et épargne"),
            (31, "Tableau d'amortissement crédit en cours", "Crédits et charges divers hors immobilier"),
            (32, "Organigramme des sociétés contrôlées", "Sociétés contrôlées"),
            (33, "Statuts de la société contrôlée", "Sociétés contrôlées"),
            (34, "Relevé de compte de la société contrôlée M - 1", "Sociétés contrôlées"),
            (35, "Relevé de compte de la société contrôlée M - 2", "Sociétés contrôlées"),
            (36, "Relevé de compte de la société contrôlée M - 3", "Sociétés contrôlées"),
            (37, "KBIS de la société contrôlée", "Sociétés contrôlées"),
            (38, "Dernière déclaration 2072", "Sociétés contrôlées"),
            (39, "Bilans et comptes de résultat de la société contrôlée N-1", "Sociétés contrôlées"),
            (40, "Bilans et comptes de résultat de la société contrôlée N-2", "Sociétés contrôlées"),
            (41, "Bilans et comptes de résultat de la société contrôlée N-3", "Sociétés contrôlées"),
            (42, "Liasses fiscales de la société contrôlée N-1", "Sociétés contrôlées"),
            (43, "Liasses fiscales de la société contrôlée N-2", "Sociétés contrôlées"),
            (44, "Liasses fiscales de la société contrôlée N-3", "Sociétés contrôlées"),
            (45, "Arrêté du permis de construire", "Object"),
            (46, "Autre", "Object"),
            (47, "Autre", "Company")
        ]

        # Prompts d'extraction pour chaque type de document
        extraction_prompts = [
            ("CV(s) du(des) associés", "Associés", "Tu es un expert en analyse de CV. Extrait les informations suivantes : nom complet, prénom, email, téléphone, formations principales, expériences professionnelles avec durée, compétences techniques et langues. Retourne un JSON structuré."),
            ("Compromis de vente", "Object", "Tu es un expert en documents immobiliers. Extrait : nom du vendeur, nom de l'acheteur, adresse du bien, prix de vente, date de signature, conditions suspensives, date de disponibilité. Retourne un JSON structuré."),
            ("Bail ou projet de bail du bien objet de l'acquisition", "Object", "Tu es un expert en contrats de bail. Extrait : nom du bailleur, nom du locataire, adresse du bien, montant du loyer, charges, durée du bail, date de début, conditions de révision du loyer. Retourne un JSON structuré."),
            ("Projet de statuts société emprunteur", "Company", "Tu es un expert en documents juridiques d'entreprise. Extrait : raison sociale, forme juridique, capital social, adresse du siège, objet social, durée de la société, noms des associés et leurs apports. Retourne un JSON structuré."),
            ("Organigramme des sociétés de la société emprunteur", "Company", "Tu es un expert en analyse de structures d'entreprise. Extrait : nom de la société mère, noms des filiales avec pourcentage de détention, noms des dirigeants principaux, liens de participation. Retourne un JSON structuré."),
            ("KBIS société emprunteur", "Company", "Tu es un expert en documents commerciaux. Extrait : raison sociale, SIREN, SIRET, forme juridique, capital social, adresse du siège, date d'immatriculation, nom du dirigeant. Retourne un JSON structuré."),
            ("Statuts société emprunteur", "Company", "Tu es un expert en statuts d'entreprise. Extrait : raison sociale, forme juridique, capital social, adresse, objet social, durée, répartition des parts, noms des associés avec leurs pourcentages, règles de prise de décision. Retourne un JSON structuré."),
            ("PV d'AG autorisant la société à emprunter", "Company", "Tu es un expert en procès-verbaux d'assemblée générale. Extrait : date de l'AG, lieu, noms des présents, objet de la délibération, montant de l'emprunt autorisé, nom du banquier, durée de l'autorisation. Retourne un JSON structuré."),
            ("Liasses fiscales société emprunteur N-1", "Company", "Tu es un expert en analyse financière. Extrait : exercice fiscal, chiffre d'affaires, résultat net, effectif moyen, montant des dettes, montant des créances, montant des immobilisations. Retourne un JSON structuré."),
            ("Liasses fiscales société emprunteur N-2", "Company", "Tu es un expert en analyse financière. Extrait : exercice fiscal, chiffre d'affaires, résultat net, effectif moyen, montant des dettes, montant des créances, montant des immobilisations. Retourne un JSON structuré."),
            ("Liasses fiscales société emprunteur N-3", "Company", "Tu es un expert en analyse financière. Extrait : exercice fiscal, chiffre d'affaires, résultat net, effectif moyen, montant des dettes, montant des créances, montant des immobilisations. Retourne un JSON structuré."),
            ("Bilan et compte de résultat détaillés de l'emprunteur N-1", "Company", "Tu es un expert en analyse financière. Extrait : exercice fiscal, total actif, total passif, chiffre d'affaires, résultat d'exploitation, résultat net, fonds propres, endettement total. Retourne un JSON structuré."),
            ("Bilan et compte de résultat détaillés de l'emprunteur N-2", "Company", "Tu es un expert en analyse financière. Extrait : exercice fiscal, total actif, total passif, chiffre d'affaires, résultat d'exploitation, résultat net, fonds propres, endettement total. Retourne un JSON structuré."),
            ("Bilan et compte de résultat détaillés de l'emprunteur N-3", "Company", "Tu es un expert en analyse financière. Extrait : exercice fiscal, total actif, total passif, chiffre d'affaires, résultat d'exploitation, résultat net, fonds propres, endettement total. Retourne un JSON structuré."),
            ("Relevé de compte Mois M - 1", "Banque et épargne", "Tu es un expert en relevés bancaires. Extrait : période concernée, solde initial, total des crédits, total des débits, solde final, noms des principaux créditeurs et débiteurs avec montants. Retourne un JSON structuré."),
            ("Relevé de compte Mois M - 2", "Banque et épargne", "Tu es un expert en relevés bancaires. Extrait : période concernée, solde initial, total des crédits, total des débits, solde final, noms des principaux créditeurs et débiteurs avec montants. Retourne un JSON structuré."),
            ("Relevé de compte Mois M - 3", "Banque et épargne", "Tu es un expert en relevés bancaires. Extrait : période concernée, solde initial, total des crédits, total des débits, solde final, noms des principaux créditeurs et débiteurs avec montants. Retourne un JSON structuré."),
            ("Carte d'identité(recto verso) ou Passeport", "Etat civil", "Tu es un expert en documents d'identité. Extrait : nom complet, prénom(s), date de naissance, lieu de naissance, nationalité, sexe, numéro du document, date de délivrance, date d'expiration, adresse si mentionnée. Retourne un JSON structuré."),
            ("Justificatif de domicile", "Etat civil", "Tu es un expert en justificatifs de domicile. Extrait : nom du titulaire, adresse complète, date du document, type de document (facture, quittance...), nom de l'émetteur. Retourne un JSON structuré."),
            ("Livret de famille", "Etat civil", "Tu es un expert en documents d'état civil. Extrait : noms et prénoms des parents, dates et lieux de naissance, noms et prénoms des enfants avec dates de naissance, date du document. Retourne un JSON structuré."),
            ("Contrat de mariage", "Etat civil", "Tu es un expert en documents de mariage. Extrait : noms et prénoms des époux, dates et lieux de naissance, date du mariage, régime matrimonial, noms des témoins. Retourne un JSON structuré."),
            ("Avis d'imposition N - 1", "Revenus", "Tu es un expert en avis d'imposition. Extrait : année d'imposition, nom complet, adresse fiscale, revenu fiscal de référence, nombre de parts, impôt sur le revenu, contributions sociales. Retourne un JSON structuré."),
            ("Avis d'imposition N - 2", "Revenus", "Tu es un expert en avis d'imposition. Extrait : année d'imposition, nom complet, adresse fiscale, revenu fiscal de référence, nombre de parts, impôt sur le revenu, contributions sociales. Retourne un JSON structuré."),
            ("Avis d'imposition N - 3", "Revenus", "Tu es un expert en avis d'imposition. Extrait : année d'imposition, nom complet, adresse fiscale, revenu fiscal de référence, nombre de parts, impôt sur le revenu, contributions sociales. Retourne un JSON structuré."),
            ("Dernière taxe foncière", "Patrimoine immobilier", "Tu es un expert en impôts fonciers. Extrait : année d'imposition, nom du propriétaire, adresse du bien, valeur locative cadastrale, taxe foncière brute, montants des déductions, taxe foncière nette. Retourne un JSON structuré."),
            ("Attestation notariée d'acquisition indiquant le prix", "Patrimoine immobilier", "Tu es un expert en documents notariés. Extrait : nom de l'acquéreur, nom du vendeur, adresse du bien, prix d'acquisition, date d'acquisition, nom du notaire, référence de l'acte. Retourne un JSON structuré."),
            ("Bail", "Patrimoine immobilier", "Tu es un expert en contrats de bail. Extrait : nom du bailleur, nom du locataire, adresse du bien, montant du loyer mensuel, charges, durée du bail, date de début, date de fin, montant du dépôt de garantie. Retourne un JSON structuré."),
            ("Tableau d'amortissement du crédit immobilier", "Patrimoine immobilier", "Tu es un expert en tableaux d'amortissement. Extrait : nom de l'emprunteur, nom de la banque, montant total emprunté, taux d'intérêt, durée totale, mensualité, date de première échéance, capital restant dû. Retourne un JSON structuré."),
            ("Dernière déclaration 2044", "Revenus", "Tu es un expert en déclarations de revenus fonciers. Extrait : année de déclaration, nom du déclarant, montant des revenus bruts, charges déductibles, revenus fonciers imposables, déficit reportable. Retourne un JSON structuré."),
            ("Dernier relevé d'épargne", "Banque et épargne", "Tu es un expert en relevés d'épargne. Extrait : nom du titulaire, type de compte, date du relevé, solde principal, montant des intérêts annuels, taux d'intérêt, disponibilité des fonds. Retourne un JSON structuré."),
            ("Tableau d'amortissement crédit en cours", "Crédits et charges divers hors immobilier", "Tu es un expert en tableaux d'amortissement. Extrait : nom de l'emprunteur, nom du créancier, montant total emprunté, taux d'intérêt, durée totale, mensualité, date de première échéance, objet du crédit. Retourne un JSON structuré."),
            ("Organigramme des sociétés contrôlées", "Sociétés contrôlées", "Tu es un expert en structures de groupe. Extrait : nom de la société holding, noms des sociétés contrôlées, pourcentages de détention, noms des dirigeants, nature des activités. Retourne un JSON structuré."),
            ("Statuts de la société contrôlée", "Sociétés contrôlées", "Tu es un expert en statuts d'entreprise. Extrait : raison sociale, forme juridique, capital social, adresse du siège, objet social, durée, noms des associés principaux, pourcentage de détention de la société mère. Retourne un JSON structuré."),
            ("Relevé de compte de la société contrôlée M - 1", "Sociétés contrôlées", "Tu es un expert en relevés bancaires d'entreprise. Extrait : nom de la société, période concernée, solde initial, total des encaissements, total des décaissements, solde final, principales opérations avec montants. Retourne un JSON structuré."),
            ("Relevé de compte de la société contrôlée M - 2", "Sociétés contrôlées", "Tu es un expert en relevés bancaires d'entreprise. Extrait : nom de la société, période concernée, solde initial, total des encaissements, total des décaissements, solde final, principales opérations avec montants. Retourne un JSON structuré."),
            ("Relevé de compte de la société contrôlée M - 3", "Sociétés contrôlées", "Tu es un expert en relevés bancaires d'entreprise. Extrait : nom de la société, période concernée, solde initial, total des encaissements, total des décaissements, solde final, principales opérations avec montants. Retourne un JSON structuré."),
            ("KBIS de la société contrôlée", "Sociétés contrôlées", "Tu es un expert en documents commerciaux. Extrait : raison sociale, SIREN, SIRET, forme juridique, capital social, adresse du siège, date d'immatriculation, nom du représentant légal. Retourne un JSON structuré."),
            ("Dernière déclaration 2072", "Sociétés contrôlées", "Tu es un expert en déclarations de revenus des sociétés. Extrait : raison sociale, exercice fiscal, chiffre d'affaires, résultat fiscal, montant de l'impôt, montant de la CFE/CVAE. Retourne un JSON structuré."),
            ("Bilans et comptes de résultat de la société contrôlée N-1", "Sociétés contrôlées", "Tu es un expert en bilans d'entreprise. Extrait : exercice fiscal, total actif, total passif, chiffre d'affaires, résultat net, fonds propres, dettes à long terme, dettes à court terme. Retourne un JSON structuré."),
            ("Bilans et comptes de résultat de la société contrôlée N-2", "Sociétés contrôlées", "Tu es un expert en bilans d'entreprise. Extrait : exercice fiscal, total actif, total passif, chiffre d'affaires, résultat net, fonds propres, dettes à long terme, dettes à court terme. Retourne un JSON structuré."),
            ("Bilans et comptes de résultat de la société contrôlée N-3", "Sociétés contrôlées", "Tu es un expert en bilans d'entreprise. Extrait : exercice fiscal, total actif, total passif, chiffre d'affaires, résultat net, fonds propres, dettes à long terme, dettes à court terme. Retourne un JSON structuré."),
            ("Liasses fiscales de la société contrôlée N-1", "Sociétés contrôlées", "Tu es un expert en liasses fiscales. Extrait : raison sociale, exercice fiscal, chiffre d'affaires, résultat fiscal, effectif, montant des taxes, montant des subventions. Retourne un JSON structuré."),
            ("Liasses fiscales de la société contrôlée N-2", "Sociétés contrôlées", "Tu es un expert en liasses fiscales. Extrait : raison sociale, exercice fiscal, chiffre d'affaires, résultat fiscal, effectif, montant des taxes, montant des subventions. Retourne un JSON structuré."),
            ("Liasses fiscales de la société contrôlée N-3", "Sociétés contrôlées", "Tu es un expert en liasses fiscales. Extrait : raison sociale, exercice fiscal, chiffre d'affaires, résultat fiscal, effectif, montant des taxes, montant des subventions. Retourne un JSON structuré."),
            ("Arrêté du permis de construire", "Object", "Tu es un expert en permis de construire. Extrait : nom du demandeur, adresse du terrain, nature des travaux, surface autorisée, coût estimé, date de délivrance, durée de validité. Retourne un JSON structuré."),
            ("Autre", "Object", "Tu es un expert en analyse de documents. Identifie le type de document et extrait les informations principales pertinentes avec leur contexte. Retourne un JSON structuré avec les informations clés identifiées."),
            ("Autre", "Company", "Tu es un expert en analyse de documents d'entreprise. Identifie le type de document et extrait les informations principales pertinentes avec leur contexte. Retourne un JSON structuré avec les informations clés identifiées.")
        ]

        # Utiliser INSERT OR IGNORE pour éviter les doublons
        cursor.executemany('''
            INSERT OR IGNORE INTO document_types (id, name, category)
            VALUES (?, ?, ?)
        ''', document_types)

        # Insérer les prompts d'extraction
        cursor.executemany('''
            INSERT OR IGNORE INTO extraction_prompts (document_type, category, extraction_prompt)
            VALUES (?, ?, ?)
        ''', extraction_prompts)

        conn.commit()
        print("Base de données initialisée avec succès")

    except sqlite3.Error as e:
        print(f"Erreur lors de l'initialisation de la base de données: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def insert_document(filename: str, file_path: str, extracted_text: str,
                   detected_type: str, detected_category: str, confidence: float) -> int:
    """
    Insérer un nouveau document dans la base de données

    Returns:
        int: ID du document inséré
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO documents (filename, file_path, extracted_text, detected_type, detected_category, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (filename, file_path, extracted_text, detected_type, detected_category, confidence))

        document_id = cursor.lastrowid
        conn.commit()
        return document_id

    except sqlite3.Error as e:
        print(f"Erreur lors de l'insertion du document: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_documents(document_id: Optional[int] = None) -> List[Dict]:
    """
    Récupérer les documents de la base de données

    Args:
        document_id: ID spécifique du document (None pour tous)

    Returns:
        List[Dict]: Liste des documents
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if document_id:
            cursor.execute('''
                SELECT * FROM documents WHERE id = ?
            ''', (document_id,))
            result = cursor.fetchone()
            return [dict(result)] if result else []
        else:
            cursor.execute('''
                SELECT * FROM documents ORDER BY created_at DESC
            ''')
            results = cursor.fetchall()
            return [dict(row) for row in results]

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération des documents: {e}")
        return []
    finally:
        conn.close()

def get_document_types() -> List[Dict]:
    """
    Récupérer tous les types de documents prédéfinis

    Returns:
        List[Dict]: Liste des types de documents
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM document_types ORDER BY category, name
        ''')
        results = cursor.fetchall()
        return [dict(row) for row in results]

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération des types de documents: {e}")
        return []
    finally:
        conn.close()

def update_document(document_id: int, **kwargs) -> bool:
    """
    Mettre à jour un document

    Args:
        document_id: ID du document à mettre à jour
        **kwargs: Champs à mettre à jour

    Returns:
        bool: True si la mise à jour a réussi
    """
    if not kwargs:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    try:
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [document_id]

        cursor.execute(f'''
            UPDATE documents
            SET {set_clause}
            WHERE id = ?
        ''', values)

        success = cursor.rowcount > 0
        conn.commit()
        return success

    except sqlite3.Error as e:
        print(f"Erreur lors de la mise à jour du document: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_document(document_id: int) -> bool:
    """
    Supprimer un document

    Args:
        document_id: ID du document à supprimer

    Returns:
        bool: True si la suppression a réussi
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        success = cursor.rowcount > 0
        conn.commit()
        return success

    except sqlite3.Error as e:
        print(f"Erreur lors de la suppression du document: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_extraction_prompt(document_type: str) -> Optional[str]:
    """
    Récupérer le prompt d'extraction pour un type de document

    Args:
        document_type: Type de document

    Returns:
        Optional[str]: Prompt d'extraction ou None si non trouvé
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT extraction_prompt FROM extraction_prompts
            WHERE document_type = ?
        ''', (document_type,))
        result = cursor.fetchone()
        return result['extraction_prompt'] if result else None

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération du prompt d'extraction: {e}")
        return None
    finally:
        conn.close()

def insert_document_extraction(document_id: int, extracted_data: str, llm_used: str, confidence: float) -> int:
    """
    Insérer les résultats d'extraction d'un document

    Args:
        document_id: ID du document
        extracted_data: Données extraites (JSON)
        llm_used: Modèle LLM utilisé
        confidence: Score de confiance

    Returns:
        int: ID de l'extraction insérée
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO document_extractions (document_id, extracted_data, llm_used, confidence)
            VALUES (?, ?, ?, ?)
        ''', (document_id, extracted_data, llm_used, confidence))

        extraction_id = cursor.lastrowid
        conn.commit()
        return extraction_id

    except sqlite3.Error as e:
        print(f"Erreur lors de l'insertion de l'extraction: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_document_extractions(document_id: Optional[int] = None) -> List[Dict]:
    """
    Récupérer les extractions de documents

    Args:
        document_id: ID spécifique du document (None pour toutes)

    Returns:
        List[Dict]: Liste des extractions
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if document_id:
            cursor.execute('''
                SELECT de.*, d.filename, d.detected_type
                FROM document_extractions de
                JOIN documents d ON de.document_id = d.id
                WHERE de.document_id = ?
                ORDER BY de.created_at DESC
            ''', (document_id,))
        else:
            cursor.execute('''
                SELECT de.*, d.filename, d.detected_type
                FROM document_extractions de
                JOIN documents d ON de.document_id = d.id
                ORDER BY de.created_at DESC
            ''')

        results = cursor.fetchall()
        return [dict(row) for row in results]

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération des extractions: {e}")
        return []
    finally:
        conn.close()

def get_extraction_prompts() -> List[Dict]:
    """
    Récupérer tous les prompts d'extraction

    Returns:
        List[Dict]: Liste des prompts d'extraction
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM extraction_prompts ORDER BY category, document_type
        ''')
        results = cursor.fetchall()
        return [dict(row) for row in results]

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération des prompts d'extraction: {e}")
        return []
    finally:
        conn.close()

def update_extraction_prompt(document_type: str, extraction_prompt: str) -> bool:
    """
    Mettre à jour un prompt d'extraction

    Args:
        document_type: Type de document
        extraction_prompt: Nouveau prompt d'extraction

    Returns:
        bool: True si la mise à jour a réussi
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE extraction_prompts
            SET extraction_prompt = ?
            WHERE document_type = ?
        ''', (extraction_prompt, document_type))

        success = cursor.rowcount > 0
        conn.commit()
        return success

    except sqlite3.Error as e:
        print(f"Erreur lors de la mise à jour du prompt d'extraction: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def insert_synthese(dossier_id: str, input_documents: str, synthese_text: str, confidence: float) -> int:
    """
    Insérer une nouvelle synthèse de financement

    Args:
        dossier_id: Identifiant du dossier
        input_documents: JSON des documents utilisés
        synthese_text: Texte de la synthèse générée
        confidence: Score de confiance

    Returns:
        int: ID de la synthèse insérée
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO syntheses (dossier_id, input_documents, synthese_text, confidence)
            VALUES (?, ?, ?, ?)
        ''', (dossier_id, input_documents, synthese_text, confidence))

        synthese_id = cursor.lastrowid
        conn.commit()
        return synthese_id

    except sqlite3.Error as e:
        print(f"Erreur lors de l'insertion de la synthèse: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_syntheses(dossier_id: Optional[str] = None) -> List[Dict]:
    """
    Récupérer les synthèses de financement

    Args:
        dossier_id: ID spécifique du dossier (None pour toutes)

    Returns:
        List[Dict]: Liste des synthèses
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if dossier_id:
            cursor.execute('''
                SELECT * FROM syntheses WHERE dossier_id = ?
                ORDER BY created_at DESC
            ''', (dossier_id,))
        else:
            cursor.execute('''
                SELECT * FROM syntheses ORDER BY created_at DESC
            ''')

        results = cursor.fetchall()
        return [dict(row) for row in results]

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération des synthèses: {e}")
        return []
    finally:
        conn.close()

def get_documents_with_extractions(document_ids: List[int]) -> List[Dict]:
    """
    Récupérer les documents avec leurs données d'extraction

    Args:
        document_ids: Liste des IDs de documents

    Returns:
        List[Dict]: Liste des documents avec leurs extractions
    """
    if not document_ids:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    try:
        placeholders = ','.join(['?' for _ in document_ids])
        cursor.execute(f'''
            SELECT d.id, d.filename, d.detected_type, d.detected_category, d.confidence,
                   d.created_at, de.extracted_data, de.llm_used, de.confidence as extraction_confidence
            FROM documents d
            LEFT JOIN document_extractions de ON d.id = de.document_id
            WHERE d.id IN ({placeholders})
            ORDER BY d.detected_category, d.detected_type
        ''', document_ids)

        results = cursor.fetchall()
        documents = []

        for row in results:
            doc = dict(row)
            # Parser le JSON des données extraites si disponible
            if doc['extracted_data']:
                try:
                    import json
                    doc['extracted_data'] = json.loads(doc['extracted_data'])
                except:
                    doc['extracted_data'] = None
            documents.append(doc)

        return documents

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération des documents avec extractions: {e}")
        return []
    finally:
        conn.close()

def insert_document_genere(dossier_id: str, type_document: str, file_path: str,
                          file_name: str, generated_from: str) -> int:
    """
    Insérer un nouveau document généré

    Args:
        dossier_id: Identifiant du dossier lié
        type_document: Type de document (ex: "Carte de Financement (.docx)")
        file_path: Chemin du fichier généré
        file_name: Nom du fichier
        generated_from: Source de génération (synthèse JSON)

    Returns:
        int: ID du document généré inséré
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO documents_generes (dossier_id, type_document, file_path, file_name, generated_from)
            VALUES (?, ?, ?, ?, ?)
        ''', (dossier_id, type_document, file_path, file_name, generated_from))

        document_id = cursor.lastrowid
        conn.commit()
        return document_id

    except sqlite3.Error as e:
        print(f"Erreur lors de l'insertion du document généré: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_document_genere(document_id: int) -> Optional[Dict]:
    """
    Récupérer un document généré par son ID

    Args:
        document_id: ID du document généré

    Returns:
        Optional[Dict]: Document généré ou None si non trouvé
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM documents_generes WHERE id = ?
        ''', (document_id,))
        result = cursor.fetchone()
        return dict(result) if result else None

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération du document généré: {e}")
        return None
    finally:
        conn.close()

def get_documents_generes(dossier_id: Optional[str] = None) -> List[Dict]:
    """
    Récupérer les documents générés

    Args:
        dossier_id: ID spécifique du dossier (None pour tous)

    Returns:
        List[Dict]: Liste des documents générés
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if dossier_id:
            cursor.execute('''
                SELECT * FROM documents_generes WHERE dossier_id = ?
                ORDER BY created_at DESC
            ''', (dossier_id,))
        else:
            cursor.execute('''
                SELECT * FROM documents_generes ORDER BY created_at DESC
            ''')

        results = cursor.fetchall()
        return [dict(row) for row in results]

    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération des documents générés: {e}")
        return []
    finally:
        conn.close()

def delete_document_genere(document_id: int) -> bool:
    """
    Supprimer un document généré

    Args:
        document_id: ID du document généré à supprimer

    Returns:
        bool: True si la suppression a réussi
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM documents_generes WHERE id = ?', (document_id,))
        success = cursor.rowcount > 0
        conn.commit()
        return success

    except sqlite3.Error as e:
        print(f"Erreur lors de la suppression du document généré: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()