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
            (1, "CV(s) du(des) associé(s)", "Associés"),
            (2, "Compromis de vente", "Object"),
            (3, "Bail ou projet de bail du bien objet de l'acquisition", "Object"),
            (4, "Projet de statuts société emprunteur", "Company"),
            (5, "Organigramme des sociétés de la société emprunteur", "Company"),
            (6, "KBIS société emprunteur", "Company"),
            (7, "Statuts société emprunteur", "Company"),
            (8, "PV d'AG autorisant la société à emprunter", "Company"),
            (9, "Liasses fiscales société emprunteur N-1", "Company"),
            (10, "Liasses fiscales société emprunteur N-2", "Company"),
            (11, "Bilan et compte de résultat détaillés de l'emprunteur N-1", "Company"),
            (12, "Bilan et compte de résultat détaillés de l'emprunteur N-2", "Company"),
            (13, "Avis d'imposition T+N-1", "Associés"),
            (14, "Avis d'imposition T+N-2", "Associés"),
            (15, "Tableau de remboursement d'emprunt", "Financement"),
            (16, "Attestation de prêt", "Financement"),
            (17, "Offre de prêt", "Financement"),
            (18, "Plan de financement prévisionnel", "Financement"),
            (19, "RIB de l'emprunteur", "Company"),
            (20, "Pièce d'identité du représentant légal", "Associés"),
            (21, "Attestation d'assurance", "Assurance"),
            (22, "Bilans et comptes de résultat de la société contrôlée N-1", "Sociétés contrôlées"),
            (23, "Bilans et comptes de résultat de la société contrôlée N-2", "Sociétés contrôlées"),
            (24, "Bilans et comptes de résultat de la société contrôlée N-3", "Sociétés contrôlées"),
            (25, "Devis des travaux prévisionnels", "Travaux"),
            (26, "Factures d'acompte travaux", "Travaux"),
            (27, "Facture finale des travaux", "Travaux"),
            (28, "Attestation de fin de travaux", "Travaux"),
            (29, "Diagnostic de performance énergétique", "Diagnostics"),
            (30, "Diagnostic amiante", "Diagnostics"),
            (31, "Diagnostic plomb", "Diagnostics"),
            (32, "Diagnostic termites", "Diagnostics"),
            (33, "Diagnostic gaz", "Diagnostics"),
            (34, "Diagnostic électricité", "Diagnostics"),
            (35, "État des lieux d'entrée", "Location"),
            (36, "État des lieux de sortie", "Location"),
            (37, "Inventaire du mobilier", "Location"),
            (38, "Contrat de réservation du logement", "Vente"),
            (39, "Acte de vente définitif", "Vente"),
            (40, "Extrait du plan cadastral", "Vente")
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