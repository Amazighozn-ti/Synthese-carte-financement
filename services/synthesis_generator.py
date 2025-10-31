"""
Service de génération de la Carte de Financement - Version simplifiée
"""

import json
import logging
from datetime import datetime
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from config import config

from models.schemas import CARTE_FINANCEMENT_MODEL
from database import get_documents_with_extractions, insert_synthese

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SynthesisGenerator:
    """Service pour générer la synthèse de financement (Carte de Financement)"""

    def __init__(self):
        """Initialiser le service de synthèse"""
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=6000
        )
        self.initialized = True

    def _generate_dossier_id(self) -> str:
        """Générer un identifiant de dossier unique"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"DOSS-{timestamp}"

    def _get_all_extractions(self, document_ids: List[int]) -> str:
        """
        Récupérer toutes les extractions et les formater pour le prompt
        """
        logger.info(f"🔍 [EXTRACTIONS] Récupération de {len(document_ids)} documents depuis la base...")
        documents = get_documents_with_extractions(document_ids)
        logger.info(f"✅ [EXTRACTIONS] {len(documents)} documents récupérés")

        all_extractions = []
        for doc in documents:
            extraction = {
                "document_id": doc["id"],
                "filename": doc["filename"],
                "type": doc["detected_type"],
                "data": doc["extracted_data"]
            }
            all_extractions.append(extraction)
            logger.debug(f"📄 [EXTRACTIONS] Document {doc['id']}: {doc['detected_type']}")

        result = json.dumps(all_extractions, indent=2, ensure_ascii=False)
        logger.info(f"📦 [EXTRACTIONS] Données formatées: {len(result)} caractères")
        return result

    def _create_simple_prompt(self, extractions: str) -> str:
        """
        Créer un prompt simple avec toutes les extractions
        """
        return f"""Tu es un expert financier. Voici toutes les données extraites des documents :

{extractions}

Génère une Carte de Financement complète en utilisant TOUTES ces informations.
Respecte le modèle Pydantic fourni et utilise chaque donnée extraite.
Ne laisse aucun champ vide, fais des inférences si nécessaire.

Réponds UNIQUEMENT avec le JSON valide selon le modèle."""

    async def generate_synthesis(self, document_ids: List[int]) -> Dict:
        """
        Générer la synthèse à partir des documents
        """
        logger.info(f"🔄 [SYNTHESE] Début génération synthèse pour {len(document_ids)} documents")
        try:
            # Récupérer toutes les extractions
            logger.info(f"📄 [SYNTHESE] Récupération des extractions pour documents IDs: {document_ids}")
            extractions = self._get_all_extractions(document_ids)
            logger.info(f"✅ [SYNTHESE] Extractions récupérées ({len(extractions)} caractères)")

            # Créer le prompt simple
            logger.info(f"📝 [SYNTHESE] Création du prompt...")
            prompt = self._create_simple_prompt(extractions)
            logger.info(f"✅ [SYNTHESE] Prompt créé ({len(prompt)} caractères)")

            # Créer le template
            logger.info(f"🔧 [SYNTHESE] Configuration du template LLM...")
            template = ChatPromptTemplate.from_messages([
                ("user", "{prompt}")
            ])

            # Générer avec le LLM
            logger.info(f"🤖 [SYNTHESE] Lancement appel LLM...")
            start_time = datetime.now()
            chain = template | self.llm.with_structured_output(CARTE_FINANCEMENT_MODEL)
            result = await chain.ainvoke({"prompt": prompt})
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"✅ [SYNTHESE] Appel LLM réussi en {duration:.2f}s")

            # Ajouter les métadonnées
            logger.info(f"🏷️ [SYNTHESE] Ajout des métadonnées...")
            dossier_id = self._generate_dossier_id()
            result.dossier_id = dossier_id
            result.date_generation = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            logger.info(f"✅ [SYNTHESE] Dossier ID généré: {dossier_id}")

            # Sauvegarder en base
            logger.info(f"💾 [SYNTHESE] Sauvegarde en base de données...")
            synthese_id = insert_synthese(
                dossier_id=dossier_id,
                input_documents=json.dumps(document_ids),
                synthese_text=json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
                confidence=0.85
            )
            logger.info(f"✅ [SYNTHESE] Sauvegarde réussie, ID: {synthese_id}")

            return {
                "success": True,
                "synthese_id": synthese_id,
                "dossier_id": dossier_id,
                "synthese": result.model_dump(),
                "message": "Synthèse générée avec succès"
            }

        except Exception as e:
            logger.error(f"❌ [SYNTHESE] Erreur lors de la génération: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_complete_synthesis(self, document_ids: List[int]) -> Dict:
        """
        Générer la synthèse complète (JSON + Document Word)
        """
        logger.info(f"🚀 [SYNTHESE-COMPLETE] Début génération complète pour {len(document_ids)} documents")
        try:
            # Générer la synthèse
            logger.info(f"📄 [SYNTHESE-COMPLETE] Étape 1/2: Génération de la synthèse...")
            synthese_result = await self.generate_synthesis(document_ids)

            if not synthese_result["success"]:
                logger.error(f"❌ [SYNTHESE-COMPLETE] Échec génération synthèse")
                return synthese_result

            logger.info(f"✅ [SYNTHESE-COMPLETE] Synthèse générée avec succès")

            # Générer le document Word
            logger.info(f"📄 [SYNTHESE-COMPLETE] Étape 2/2: Génération document Word...")
            from services.word_generator import WordDocumentGenerator
            word_generator = WordDocumentGenerator()
            synthese_data = synthese_result["synthese"]
            dossier_id = synthese_result["dossier_id"]
            word_result = word_generator.generate_word_document(synthese_data, dossier_id)

            logger.info(f"✅ [SYNTHESE-COMPLETE] Document Word généré avec succès")

            return {
                "success": True,
                "synthese": synthese_result,
                "word_document": word_result,
                "message": "Génération complète réussie"
            }

        except Exception as e:
            logger.error(f"❌ [SYNTHESE-COMPLETE] Erreur lors de la génération complète: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
