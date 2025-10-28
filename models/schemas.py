"""
Modèles Pydantic pour la sortie structurée du LLM
"""

from pydantic import BaseModel, Field
from typing import Optional


class DocumentClassification(BaseModel):
    """Résultat de classification d'un document"""
    document_type: str = Field(description="Type de document spécifique parmi les 40 types prédéfinis")
    category: str = Field(description="Catégorie principale (Company, Object, Associates, Financing, Diagnostics, Works, Sale, Location)")
    confidence: float = Field(ge=0.0, le=1.0, description="Score de confiance de la classification entre 0 et 1")
    reasoning: str = Field(default="Non précisé", description="Explication de la classification basée sur le contenu du document")


class ClassificationResult(BaseModel):
    """Résultat complet de la classification avec métadonnées"""
    success: bool = Field(description="Indique si la classification a réussi")
    classification: DocumentClassification = Field(description="Résultat de la classification")
    processing_time: Optional[float] = Field(None, description="Temps de traitement en secondes")
    error_message: Optional[str] = Field(None, description="Message d'erreur si échec")