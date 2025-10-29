"""
Configuration de l'application
"""

import os
from dotenv import load_dotenv
from typing import Optional

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

class Config:
    """Classe de configuration"""

    # Configuration API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Configuration Mistral
    MISTRAL_API_KEY: Optional[str] = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

    # Configuration base de données
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///documents.db")

    # Configuration upload
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "50")) * 1024 * 1024  # 50MB par défaut

    # Suppression automatique des fichiers après traitement
    DELETE_AFTER_PROCESSING: bool = os.getenv("DELETE_AFTER_PROCESSING", "true").lower() == "true"

    # Types de fichiers supportés
    SUPPORTED_EXTENSIONS: list = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']

    @classmethod
    def validate(cls):
        """Valider la configuration"""
        if not cls.MISTRAL_API_KEY:
            print("WARNING: MISTRAL_API_KEY non définie - OCR et classification limités")
            return False

        print("✅ MISTRAL_API_KEY configurée")
        # Créer le répertoire d'upload
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        return True

# Instance de configuration
config = Config()
config.validate()