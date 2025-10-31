"""
Service de classification de documents avec LangChain et Mistral LLM
"""

import os
import json
from typing import Dict, List, Optional
import logging
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.exceptions import OutputParserException
from models.schemas import (
    DocumentClassification, ClassificationResult,
    EXTRACTION_MODELS, ExtractionGenerale
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClassifier:
    """Classe pour classifier les documents en utilisant LangChain et Mistral LLM"""

    def __init__(self):
        """Initialiser le client LangChain avec OpenAI"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OPENAI_API_KEY non trouvé dans les variables d'environnement")

        # Initialiser le modèle LangChain avec OpenAI
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model="gpt-4.1-mini",
            temperature=0.1  # Température basse pour plus de cohérence
        ) if self.api_key else None

        # Créer le template de prompt structuré
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu es un expert en classification de documents administratifs et financiers français.

MISSION: Analyse le document et identifie LE TYPE LE PLUS PRÉCIS possible.

RÈGLES CRITIQUES:
1. Tu DOIS choisir un type dans la liste - JAMAIS "Autre" sauf si VRAIMENT aucune correspondance
2. Pour un KBIS → "KBIS société emprunteur"
3. Pour un bilan comptable → "Bilans, Liasses fiscales"
4. Pour un avis d'imposition → "Avis d'imposition"
5. Pour un devis → "Devis"
6. Pour un avis de valeur → "Avis de valeur" (si disponible) sinon proche
7. Analyse TOUS les mots-clés du document

EXEMPLES:
- "extrait Kbis" → "KBIS société emprunteur"
- "bilan comptable société" → "Bilans, Liasses fiscales"
- "revenu fiscal" → "Avis d'imposition"

Sois exhaustif dans l'analyse. Score de confiance réaliste (0.0 à 1.0)."""),
            ("user", """Texte à analyser:
{text}

Types disponibles:
{document_types}

QUEL EST LE TYPE EXACT LE PLUS PRÉCIS pour ce document?""")
        ])

        # Créer la chaîne avec sortie structurée
        if self.llm:
            self.chain = self.prompt | self.llm.with_structured_output(DocumentClassification, method="function_calling")
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

            # Valider et corriger le type si nécessaire
            if result.document_type not in self.document_types or "autre" in result.document_type.lower():
                logger.info(f"🔄 Classification à améliorer: {result.document_type}")
                # Forcer une meilleure classification avec validation stricte
                improved_result = self._strict_validation_and_reclassification(truncated_text, result.document_type)
                if improved_result:
                    result = improved_result

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

    def _strict_validation_and_reclassification(self, text: str, initial_type: str) -> Optional[DocumentClassification]:
        """
        Reclassifie de manière stricte si le type initial n'est pas satisfaisant
        """
        try:
            # Créer un prompt plus strict pour forcer une meilleure classification
            strict_prompt = ChatPromptTemplate.from_messages([
                ("system", """Tu dois classifier ce document avec PRÉCISION MAXIMALE.

RÈGLES ABSOLUES:
1. JAMAIS "Autre" - Trouve TOUJOURS le bon type dans la liste
2. Analyse TOUS les mots-clés (société, bilan, Kbis, avis, facture, etc.)
3. Cherche les indices: "SARL", "SAS", "revenu", "bilan", "chiffre affaires"

EXEMPLES CONCRETS:
- "extrait Kbis, registre du commerce" → "KBIS société emprunteur"
- "bilan comptable 2023, compte de résultat" → "Bilans, Liasses fiscales"
- "avis d'imposition 2023, DGFiP" → "Avis d'imposition"
- "devis travaux, entreprise" → "Devis"

Si tu vois "KBIS", choisis OBLIGATOIREMENT "KBIS société emprunteur"
Si tu vois "bilan" + "société", choisis OBLIGATOIREMENT "Bilans, Liasses fiscales"

ILI FAUT CHOISIR LE TYPE EXACT LE PLUS PRÉCIS!"""),
                ("user", """Types disponibles:
{document_types}

Texte:
{text}

TYPE EXACT (UNE SEULE LIGNE):""")
            ])

            if not self.llm:
                return None

            chain = strict_prompt | self.llm.with_structured_output(DocumentClassification, method="function_calling")

            document_types_str = "\n".join([f"- {doc_type}" for doc_type in self.document_types])

            # Appel direct (plus simple et fiable)
            result = chain.invoke({"text": text, "document_types": document_types_str})

            # Valider et retourner le résultat
            if result and result.document_type in self.document_types:
                logger.info(f"✅ Reclassification réussie: {result.document_type}")
                return result
            return None

        except Exception as e:
            logger.warning(f"❌ Erreur reclassification: {str(e)}")
            return None

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

    async def extract_document_data(self, text: str, document_type: str) -> Dict[str, any]:
        """
        Extraire les données structurées d'un document en utilisant Pydantic et LangChain

        Args:
            text: Texte extrait du document
            document_type: Type de document détecté

        Returns:
            Dict: Résultat d'extraction avec données structurées et confiance
        """
        start_time = datetime.now()

        try:
            # Récupérer le modèle Pydantic approprié pour ce type de document
            extraction_model = EXTRACTION_MODELS.get(document_type, ExtractionGenerale)

            # Créer le prompt d'extraction avec le modèle Pydantic
            extraction_template = ChatPromptTemplate.from_messages([
                ("system", f"""Tu es un expert en extraction d'informations pour les documents de type "{document_type}".
Analyse attentivement le texte fourni et extrais TOUTES les informations pertinentes demandées par le schéma.

Instructions importantes:
- Extrais les informations précisément comme elles apparaissent dans le document
- Si une information n'est pas trouvée dans le document, utilise "Non spécifié"
- Sois précis et exhaustif dans ton extraction
- Le format de sortie sera automatiquement validé par le système Pydantic"""),
                ("user", """Texte du document à analyser:

{text}

Extrais toutes les informations pertinentes de ce document en utilisant le schéma {model_name}.""")
            ])

            # Créer la chaîne d'extraction avec sortie structurée Pydantic
            if not self.llm:
                logger.error("LLM non initialisé pour l'extraction")
                return {
                    "success": False,
                    "error": "LLM non initialisé",
                    "extracted_data": None,
                    "confidence": 0.0,
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }

            # Créer la chaîne avec le modèle Pydantic
            extraction_chain = extraction_template | self.llm.with_structured_output(extraction_model, method="function_calling")

            # Limiter la longueur du texte pour éviter les limites de l'API
            truncated_text = text[:12000]

            logger.info(f"🔍 Extraction structurée pour: {document_type} (modèle: {extraction_model.__name__})")

            # Invoquer la chaîne d'extraction
            result = await extraction_chain.ainvoke({
                "text": truncated_text,
                "model_name": extraction_model.__name__
            })

            # Convertir le résultat en dictionnaire
            extracted_dict = result.model_dump()

            # Créer le résultat final avec métadonnées
            final_result = {
                "document_type": document_type,
                "category": self.categories.get(document_type, "Autre"),
                "extracted_fields": extracted_dict,
                "extraction_model": extraction_model.__name__,
                "extraction_timestamp": datetime.now().isoformat(),
                "confidence": 0.9
            }

            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Extraction structurée réussie pour: {document_type}")

            # Encoder en JSON formaté pour une meilleure lisibilité
            formatted_json = json.dumps(final_result, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "extracted_data": formatted_json,
                "confidence": 0.9,  # Haute confiance avec Pydantic
                "processing_time": processing_time,
                "llm_used": "gpt-4.1-mini",
                "normalized_result": final_result  # Ajout du résultat normalisé pour une utilisation directe
            }

        except Exception as e:
            # Limiter la taille du message d'erreur pour éviter les logs trop longs
            error_message = str(e)
            if len(error_message) > 500:
                error_message = error_message[:500] + "... [tronqué]"

            # Nettoyer l'erreur pour éviter les problèmes de formatage dans les logs
            import re
            # Supprimer les caractères de contrôle et les nouvelles lignes excessives
            error_message = re.sub(r'[\r\n]+', ' | ', error_message)
            error_message = re.sub(r'\s+', ' ', error_message)

            logger.error(f"❌ Erreur lors de l'extraction structurée: {error_message}")

            # Ne pas utiliser de fallback - remonter l'erreur directement
            return {
                "success": False,
                "error": f"Extraction échouée: {str(e)}",
                "extracted_data": None,
                "confidence": 0.0,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }

    async def process_document_complete(self, text: str) -> Dict[str, any]:
        """
        Pipeline complet de traitement : classification puis extraction

        Args:
            text: Texte extrait du document

        Returns:
            Dict: Résultat complet avec classification et extraction
        """
        logger.info("🚀 Démarrage du pipeline complet de traitement")
        total_start_time = datetime.now()

        # Étape 1: Classification
        logger.info("📍 Étape 1/2: Classification du document")
        classification_result = await self.classify_document(text)

        if not classification_result.get("success", False):
            logger.error("❌ Échec de la classification, extraction annulée")
            return {
                "success": False,
                "error": "Échec de la classification",
                "classification": classification_result,
                "extraction": None,
                "total_processing_time": (datetime.now() - total_start_time).total_seconds()
            }

        document_type = classification_result["classification"]["document_type"]
        logger.info(f"✅ Document classifié comme: {document_type}")

        # Étape 2: Extraction
        logger.info("📍 Étape 2/2: Extraction des données structurées")
        extraction_result = await self.extract_document_data(text, document_type)

        total_processing_time = (datetime.now() - total_start_time).total_seconds()

        # Résultat complet
        complete_result = {
            "success": extraction_result.get("success", False),
            "classification": classification_result,
            "extraction": extraction_result,
            "total_processing_time": total_processing_time,
            "document_type": document_type,
            "confidence": classification_result["classification"]["confidence"]
        }

        if extraction_result.get("success"):
            logger.info(f"✅ Pipeline complet terminé avec succès en {total_processing_time:.2f}s")
        else:
            logger.warning(f"⚠️ Pipeline terminé avec erreurs en {total_processing_time:.2f}s")

        return complete_result