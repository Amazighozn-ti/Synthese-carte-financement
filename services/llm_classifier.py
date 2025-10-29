"""
Service de classification de documents avec LangChain et Mistral LLM
"""

import os
from typing import Dict, List
import logging
from datetime import datetime

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.exceptions import OutputParserException
from models.schemas import DocumentClassification, ClassificationResult

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClassifier:
    """Classe pour classifier les documents en utilisant LangChain et Mistral LLM"""

    def __init__(self):
        """Initialiser le client LangChain avec Mistral"""
        self.api_key = os.getenv('MISTRAL_API_KEY')
        if not self.api_key:
            logger.warning("MISTRAL_API_KEY non trouvé dans les variables d'environnement")

        # Initialiser le modèle LangChain avec Mistral
        self.llm = ChatMistralAI(
            api_key=self.api_key,
            model="mistral-large-latest",
            temperature=0.1  # Température basse pour plus de cohérence
        ) if self.api_key else None

        # Créer le template de prompt structuré
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu es un expert en classification de documents administratifs et financiers français.
Analyse attentivement le texte fourni et identifie LE TYPE EXACT parmi la liste fournie.

IMPORTANT: Tu dois OBLIGATOIREMENT choisir un type de document dans la liste exacte fournie. Ne propose jamais un type qui n'est pas dans cette liste.
Si aucun type ne correspond parfaitement, choisis "Autre" dans la catégorie appropriée.

Sois précis et cohérent dans ta classification et fournis un score de confiance réaliste (0.0 à 1.0)."""),
            ("user", """Texte à analyser:
{text}

Types de documents disponibles (CHOISIR OBLIGATOIREMENT DANS CETTE LISTE):
{document_types}

Identifie le type de document EXACT qui correspond le mieux.""")
        ])

        # Créer la chaîne avec sortie structurée
        if self.llm:
            self.chain = self.prompt | self.llm.with_structured_output(DocumentClassification)
        else:
            self.chain = None

        # Charger les types de documents depuis la base de données
        self._load_document_types_from_db()

    def _load_document_types_from_db(self):
        """
        Charger les types de documents et catégories depuis la base de données
        """
        try:
            from database import get_document_types

            # Récupérer les types depuis la base de données
            db_types = get_document_types()

            # Extraire les listes
            self.document_types = [doc_type['name'] for doc_type in db_types]
            self.categories = {doc_type['name']: doc_type['category'] for doc_type in db_types}

            logger.info(f"✅ Chargé {len(self.document_types)} types de documents depuis la base de données")

        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des types de documents: {e}")
            # En cas d'erreur, utiliser des listes vides pour éviter les crashs
            self.document_types = []
            self.categories = {}

    async def classify_document(self, text: str) -> Dict[str, any]:
        """
        Classifier un document en utilisant LangChain et Mistral LLM

        Args:
            text: Texte extrait du document

        Returns:
            Dict: Résultat de la classification avec type, catégorie et confiance
        """
        start_time = datetime.now()

        if not self.chain:
            logger.error("Chaîne LangChain non initialisée")
            fallback = self._fallback_classification(text)
            return ClassificationResult(
                success=False,
                classification=DocumentClassification(**fallback),
                processing_time=(datetime.now() - start_time).total_seconds(),
                error_message="Chaîne LangChain non initialisée"
            ).model_dump()

        try:
            # Limiter la longueur du texte pour éviter les limites de l'API
            truncated_text = text[:8000]  # Limiter à 8000 caractères

            # Préparer la liste des types de documents pour le prompt
            document_types_str = "\n".join([f"- {doc_type}" for doc_type in self.document_types])

            # Invoquer la chaîne LangChain avec sortie structurée
            logger.info("Classification avec LangChain...")
            result = await self.chain.ainvoke({
                "text": truncated_text,
                "document_types": document_types_str
            })

            # Valider que le type est bien dans la liste (juste pour vérification)
            if result.document_type not in self.document_types:
                logger.warning(f"❌ Le LLM a proposé un type non valide: {result.document_type}")
                # Chercher le "Autre" approprié
                for doc_type in self.document_types:
                    if "autre" in doc_type.lower():
                        result.document_type = doc_type
                        result.category = self.categories.get(doc_type, "Autre")
                        break

            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"✅ Classification réussie: {result.document_type} ({result.confidence:.2f})")

            return ClassificationResult(
                success=True,
                classification=result,
                processing_time=processing_time
            ).model_dump()

        except OutputParserException as e:
            logger.warning(f"Erreur de parsing du LLM: {e}")
            fallback = self._fallback_classification(text)
            return ClassificationResult(
                success=False,
                classification=DocumentClassification(**fallback),
                processing_time=(datetime.now() - start_time).total_seconds(),
                error_message=f"Erreur parsing: {str(e)}"
            ).model_dump()

        except Exception as e:
            logger.error(f"Erreur lors de la classification: {e}")
            fallback = self._fallback_classification(text)
            return ClassificationResult(
                success=False,
                classification=DocumentClassification(**fallback),
                processing_time=(datetime.now() - start_time).total_seconds(),
                error_message=str(e)
            ).model_dump()

    def _validate_and_correct_result(self, result: DocumentClassification) -> DocumentClassification:
        """
        Valider et corriger le résultat de classification

        Args:
            result: Résultat de classification brut

        Returns:
            DocumentClassification: Résultat validé et corrigé
        """
        # S'assurer que le type de document est dans la liste prédéfinie
        if result.document_type not in self.document_types:
            logger.warning(f"Type de document non reconnu: {result.document_type}")
            # Chercher le type le plus proche par simple inclusion de texte
            best_match = self._find_closest_match(result.document_type)
            result.document_type = best_match

        # Corriger la catégorie si nécessaire
        expected_category = self.categories.get(result.document_type, 'Autre')
        if result.category != expected_category:
            result.category = expected_category

        # Valider le score de confiance
        if not (0.0 <= result.confidence <= 1.0):
            result.confidence = 0.5  # Valeur par défaut

        return result

    def _find_closest_match(self, document_type: str) -> str:
        """
        Chercher la correspondance la plus proche par inclusion de texte

        Args:
            document_type: Type de document à rechercher

        Returns:
            str: Meilleure correspondance trouvée
        """
        document_type_lower = document_type.lower()

        # Chercher une correspondance exacte ou partielle
        for doc_type in self.document_types:
            if document_type_lower in doc_type.lower() or doc_type.lower() in document_type_lower:
                return doc_type

        # Si rien trouvé, chercher "Autre" dans les types disponibles
        for doc_type in self.document_types:
            if "autre" in doc_type.lower():
                return doc_type

        # Si rien trouvé, retourner le premier type comme fallback
        return self.document_types[0] if self.document_types else "Document non identifié"

    def _fallback_classification(self, text: str) -> Dict[str, any]:
        """
        Classification de secours simple utilisée en cas d'erreur LLM

        Args:
            text: Texte à classifier

        Returns:
            Dict: Résultat de classification basique
        """
        # Fallback simple - recherche par mots-clés dans les types de documents disponibles
        text_lower = text.lower()

        # Chercher une correspondance directe avec les types disponibles
        for doc_type in self.document_types:
            doc_type_lower = doc_type.lower()
            # Extraire les mots-clés du type de document
            keywords = doc_type_lower.split()
            for keyword in keywords:
                if len(keyword) > 3 and keyword in text_lower:  # Éviter les mots trop courts
                    result = DocumentClassification(
                        document_type=doc_type,
                        category=self.categories.get(doc_type, "Autre"),
                        confidence=0.3,  # Confiance faible pour le fallback
                        reasoning=f"Classification de secours par mot-clé: '{keyword}'"
                    )
                    return result.model_dump()

        # Chercher "Autre" comme fallback
        for doc_type in self.document_types:
            if "autre" in doc_type.lower():
                result = DocumentClassification(
                    document_type=doc_type,
                    category=self.categories.get(doc_type, "Autre"),
                    confidence=0.2,
                    reasoning="Classification de secours: Autre"
                )
                return result.model_dump()

        # Fallback par défaut
        default_type = self.document_types[0] if self.document_types else "Document non identifié"
        result = DocumentClassification(
            document_type=default_type,
            category=self.categories.get(default_type, "Autre"),
            confidence=0.1,
            reasoning="Classification par défaut (erreur LLM)"
        )
        return result.model_dump()

    def get_supported_types(self) -> List[str]:
        """
        Retourner la liste des types de documents supportés

        Returns:
            List[str]: Types de documents supportés
        """
        return self.document_types.copy()

    def get_categories(self) -> Dict[str, str]:
        """
        Retourner le mapping des types vers catégories

        Returns:
            Dict[str, str]: Mapping type -> catégorie
        """
        return self.categories.copy()

    def reload_document_types(self):
        """
        Recharger les types de documents depuis la base de données
        Utile si la base de données a été mise à jour
        """
        logger.info("🔄 Rechargement des types de documents depuis la base de données...")
        self._load_document_types_from_db()