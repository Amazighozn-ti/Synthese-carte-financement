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

        # Utiliser INSERT OR IGNORE pour éviter les doublons
        cursor.executemany('''
            INSERT OR IGNORE INTO document_types (id, name, category)
            VALUES (?, ?, ?)
        ''', document_types)

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