"""
Service de classification de documents avec Mistral LLM
"""

import os
from typing import Dict, List, Optional
from mistralai import Mistral
import json
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClassifier:
    """Classe pour classifier les documents en utilisant Mistral LLM"""

    def __init__(self):
        """Initialiser le client Mistral"""
        self.api_key = os.getenv('MISTRAL_API_KEY')
        if not self.api_key:
            logger.warning("MISTRAL_API_KEY non trouvé dans les variables d'environnement")

        self.client = Mistral(api_key=self.api_key) if self.api_key else None
        self.model = "mistral-large-latest"  # ou "mistral-medium-latest"

        # Types de documents prédéfinis
        self.document_types = [
            "CV(s) du(des) associé(s)",
            "Compromis de vente",
            "Bail ou projet de bail du bien objet de l'acquisition",
            "Projet de statuts société emprunteur",
            "Organigramme des sociétés de la société emprunteur",
            "KBIS société emprunteur",
            "Statuts société emprunteur",
            "PV d'AG autorisant la société à emprunter",
            "Liasses fiscales société emprunteur N-1",
            "Liasses fiscales société emprunteur N-2",
            "Bilan et compte de résultat détaillés de l'emprunteur N-1",
            "Bilan et compte de résultat détaillés de l'emprunteur N-2",
            "Avis d'imposition T+N-1",
            "Avis d'imposition T+N-2",
            "Tableau de remboursement d'emprunt",
            "Attestation de prêt",
            "Offre de prêt",
            "Plan de financement prévisionnel",
            "RIB de l'emprunteur",
            "Pièce d'identité du représentant légal",
            "Attestation d'assurance",
            "Bilans et comptes de résultat de la société contrôlée N-1",
            "Bilans et comptes de résultat de la société contrôlée N-2",
            "Bilans et comptes de résultat de la société contrôlée N-3",
            "Devis des travaux prévisionnels",
            "Factures d'acompte travaux",
            "Facture finale des travaux",
            "Attestation de fin de travaux",
            "Diagnostic de performance énergétique",
            "Diagnostic amiante",
            "Diagnostic plomb",
            "Diagnostic termites",
            "Diagnostic gaz",
            "Diagnostic électricité",
            "État des lieux d'entrée",
            "État des lieux de sortie",
            "Inventaire du mobilier",
            "Contrat de réservation du logement",
            "Acte de vente définitif",
            "Extrait du plan cadastral"
        ]

        # Catories correspondantes
        self.categories = {
            "CV(s) du(des) associé(s)": "Associés",
            "Pièce d'identité du représentant légal": "Associés",
            "Avis d'imposition T+N-1": "Associés",
            "Avis d'imposition T+N-2": "Associés",
            "Compromis de vente": "Object",
            "Bail ou projet de bail du bien objet de l'acquisition": "Object",
            "Projet de statuts société emprunteur": "Company",
            "Organigramme des sociétés de la société emprunteur": "Company",
            "KBIS société emprunteur": "Company",
            "Statuts société emprunteur": "Company",
            "PV d'AG autorisant la société à emprunter": "Company",
            "Liasses fiscales société emprunteur N-1": "Company",
            "Liasses fiscales société emprunteur N-2": "Company",
            "Bilan et compte de résultat détaillés de l'emprunteur N-1": "Company",
            "Bilan et compte de résultat détaillés de l'emprunteur N-2": "Company",
            "RIB de l'emprunteur": "Company",
            "Tableau de remboursement d'emprunt": "Financement",
            "Attestation de prêt": "Financement",
            "Offre de prêt": "Financement",
            "Plan de financement prévisionnel": "Financement",
            "Attestation d'assurance": "Assurance",
            "Bilans et comptes de résultat de la société contrôlée N-1": "Sociétés contrôlées",
            "Bilans et comptes de résultat de la société contrôlée N-2": "Sociétés contrôlées",
            "Bilans et comptes de résultat de la société contrôlée N-3": "Sociétés contrôlées",
            "Devis des travaux prévisionnels": "Travaux",
            "Factures d'acompte travaux": "Travaux",
            "Facture finale des travaux": "Travaux",
            "Attestation de fin de travaux": "Travaux",
            "Diagnostic de performance énergétique": "Diagnostics",
            "Diagnostic amiante": "Diagnostics",
            "Diagnostic plomb": "Diagnostics",
            "Diagnostic termites": "Diagnostics",
            "Diagnostic gaz": "Diagnostics",
            "Diagnostic électricité": "Diagnostics",
            "État des lieux d'entrée": "Location",
            "État des lieux de sortie": "Location",
            "Inventaire du mobilier": "Location",
            "Contrat de réservation du logement": "Vente",
            "Acte de vente définitif": "Vente",
            "Extrait du plan cadastral": "Vente"
        }

    async def classify_document(self, text: str) -> Dict[str, any]:
        """
        Classifier un document en utilisant Mistral LLM

        Args:
            text: Texte extrait du document

        Returns:
            Dict: Résultat de la classification avec type, catégorie et confiance
        """
        if not self.client:
            logger.error("Client Mistral non initialisé")
            return self._fallback_classification(text)

        try:
            # Limiter la longueur du texte pour éviter les limites de l'API
            truncated_text = text[:8000]  # Limiter à 8000 caractères

            # Construire le prompt pour la classification
            prompt = self._build_classification_prompt(truncated_text)

            # Appeler l'API Mistral
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en classification de documents administratifs et financiers. Analyse attentivement le texte fourni et identifie le type de document parmi la liste prédéfinie. Sois précis et cohérent dans ta classification."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Température basse pour plus de cohérence
                max_tokens=500
            )

            # Extraire et parser la réponse
            result_text = response.choices[0].message.content
            return self._parse_llm_response(result_text)

        except Exception as e:
            logger.error(f"Erreur lors de la classification avec Mistral: {e}")
            return self._fallback_classification(text)

    def _build_classification_prompt(self, text: str) -> str:
        """
        Construire le prompt pour la classification

        Args:
            text: Texte à classifier

        Returns:
            str: Prompt formaté
        """
        document_types_str = "\n".join([f"- {doc_type}" for doc_type in self.document_types])

        prompt = f"""Analyse le texte suivant et identifie le type de document correspondant.

Texte à analyser:
{text[:3000]}

{'Texte trop long, analyse de la première partie...' if len(text) > 3000 else ''}

Types de documents possibles:
{document_types_str}

IMPORTANT: Réponds UNIQUEMENT avec un JSON valide et CONCIS. Ne dépasse pas 500 caractères.

Format JSON obligatoire:
{{"document_type": "Nom exact du type", "category": "Catégorie", "confidence": 0.95, "key_information": {{}}, "reasoning": "explication courte"}}

Règles:
- key_information doit être un objet vide {{}}
- reasoning doit être court (max 50 caractères)
- Ne pas utiliser de code blocks (```json```)
- JSON direct et valide uniquement

Exemples:
{{"document_type": "KBIS société emprunteur", "category": "Company", "confidence": 0.95, "key_information": {{}}, "reasoning": "Document KBIS identifié"}}
{{"document_type": "Bail ou projet de bail", "category": "Object", "confidence": 0.90, "key_information": {{}}, "reasoning": "Contrat de location détecté"}}
{{"document_type": "CV(s) du(des) associé(s)", "category": "Associés", "confidence": 0.85, "key_information": {{}}, "reasoning": "Curriculum vitae reconnu"}}

Ta réponse JSON :"""
        return prompt

    def _clean_json_string(self, json_str: str) -> str:
        """
        Nettoyer une chaîne JSON pour la rendre valide

        Args:
            json_str: Chaîne JSON potentiellement mal formatée

        Returns:
            str: Chaîne JSON nettoyée
        """
        import re

        # Corrections simples
        json_str = json_str.replace("'", '"')  # Quotes simples en doubles
        json_str = re.sub(r',\s*}', '}', json_str)  # Virgule avant }
        json_str = re.sub(r',\s*]', ']', json_str)  # Virgule avant ]

        # Corriger les virgules manquantes entre les clés
        json_str = re.sub(r'"\s*\n\s*"', '",\n  "', json_str)

        return json_str

    def _repair_truncated_json(self, json_str: str) -> str:
        """
        Réparer un JSON tronqué en complétant les accolades manquantes

        Args:
            json_str: JSON tronqué

        Returns:
            str: JSON réparé
        """
        # Compter le nombre d'accolades ouvrantes et fermantes
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')

        # Ajouter les accolades fermantes manquantes
        missing_braces = open_braces - close_braces
        if missing_braces > 0:
            # Compléter le JSON avec des valeurs par défaut et accolades
            if not json_str.rstrip().endswith(','):
                json_str = json_str.rstrip() + ','

            # Ajouter les champs manquants si nécessaire
            if '"reasoning"' not in json_str:
                json_str += '\n  "reasoning": "Classification basée sur le contenu du document"'

            # Ajouter les accolades fermantes manquantes
            json_str += '\n' + '}' * missing_braces

        return json_str

    def _parse_llm_response(self, response_text: str) -> Dict[str, any]:
        """
        Parser la réponse du LLM

        Args:
            response_text: Réponse textuelle du LLM

        Returns:
            Dict: Résultat structuré
        """
        try:
            # Logger la réponse brute pour débogage
            logger.info(f"Réponse brute du LLM: {repr(response_text)}")

            # Nettoyer la réponse enlever les markers de code block
            response_text = response_text.strip()

            # Enlever les markers ```json et ``` si présents
            if response_text.startswith('```json'):
                response_text = response_text[7:]  # Enlever ```json
            if response_text.startswith('```'):
                response_text = response_text[3:]   # Enlever ```
            if response_text.endswith('```'):
                response_text = response_text[:-3]  # Enlever ```

            response_text = response_text.strip()

            # Chercher le début du JSON
            json_start = response_text.find('{')
            if json_start == -1:
                raise ValueError("Aucun JSON trouvé dans la réponse")

            # Chercher la fin du JSON - chercher la dernière accolade fermante complète
            json_end = response_text.rfind('}')
            if json_end == -1:
                raise ValueError("JSON incomplet dans la réponse")

            # Si le JSON semble tronqué, essayer de le compléter
            json_str = response_text[json_start:json_end+1]

            # Vérifier si le JSON est malformé (tronqué)
            if json_str.count('{') > json_str.count('}'):
                logger.warning("JSON semble tronqué, tentative de réparation...")
                json_str = self._repair_truncated_json(json_str)

            logger.info(f"JSON extrait: {repr(json_str[:200])}...")  # Limiter le log

            # Nettoyer et parser le JSON
            try:
                # D'abord essayer de parser directement
                result = json.loads(json_str)
                logger.info("JSON parsé avec succès")
            except json.JSONDecodeError as e:
                logger.warning(f"Premier essai de parsing échoué: {e}")
                # Si ça échoue, nettoyer et réessayer
                json_str = self._clean_json_string(json_str)
                logger.info(f"JSON nettoyé: {repr(json_str)}")
                try:
                    result = json.loads(json_str)
                    logger.info("JSON parsé avec succès après nettoyage")
                except json.JSONDecodeError as e:
                    logger.error(f"Erreur de parsing JSON: {e}")
                    logger.error(f"JSON problématique: {repr(json_str)}")
                    raise ValueError(f"JSON invalide: {e}")

            # Validation et correction des résultats
            if 'document_type' not in result:
                raise ValueError("document_type manquant")

            # S'assurer que le type de document est dans la liste prédéfinie
            if result['document_type'] not in self.document_types:
                # Chercher la meilleure correspondance approximative
                result['document_type'] = self._find_best_match(result['document_type'])

            # Ajouter la catégorie si absente
            if 'category' not in result:
                result['category'] = self.categories.get(result['document_type'], 'Autre')

            # Valider le score de confiance
            if 'confidence' not in result or not (0 <= result['confidence'] <= 1):
                result['confidence'] = 0.5  # Valeur par défaut

            return result

        except Exception as e:
            logger.error(f"Erreur lors du parsing de la réponse LLM: {e}")
            # Retourner une classification par défaut
            return {
                "document_type": "Document non identifié",
                "category": "Autre",
                "confidence": 0.1,
                "key_information": {},
                "reasoning": f"Erreur de parsing: {str(e)}"
            }

    def _find_best_match(self, document_type: str) -> str:
        """
        Chercher la meilleure correspondance approximative

        Args:
            document_type: Type de document à rechercher

        Returns:
            str: Meilleure correspondance trouvée
        """
        document_type_lower = document_type.lower()

        # Mots-clés pour chaque type
        keywords_map = {
            "kbis": ["kbis", "k.b.i.s", "extrait", "immatriculation", "rcs"],
            "statuts": ["statuts", "statut", "société"],
            "bail": ["bail", "location", "loyer"],
            "compromis": ["compromis", "vente", "promesse"],
            "cv": ["cv", "curriculum", "vitae"],
            "avis imposition": ["avis", "imposition", "impôt", "fiscal"],
            "bilan": ["bilan", "compte", "résultat", "financier"],
            "diagnostic": ["diagnostic", "dpe", "amiante", "plomb", "termites"],
            "identité": ["carte", "identité", "cni", "passeport"],
            "assurance": ["assurance", "garantie"],
            "rib": ["rib", "relevé", "iban", "bic"]
        }

        for doc_type in self.document_types:
            doc_type_lower = doc_type.lower()
            for keyword_group in keywords_map.values():
                if any(keyword in doc_type_lower for keyword in keyword_group):
                    if any(keyword in document_type_lower for keyword in keyword_group):
                        return doc_type

        return "Document non identifié"

    def _fallback_classification(self, text: str) -> Dict[str, any]:
        """
        Classification de secours basée sur des mots-clés

        Args:
            text: Texte à classifier

        Returns:
            Dict: Résultat de classification basique
        """
        text_lower = text.lower()

        # Mots-clés pour chaque type de document
        keywords = {
            "KBIS société emprunteur": ["kbis", "k.b.i.s", "extrait", "immatriculation", "rcs", "greffe"],
            "Statuts société emprunteur": ["statuts", "statut", "société", "forme juridique", "capital"],
            "Bail ou projet de bail du bien objet de l'acquisition": ["bail", "location", "loyer", "bailleur", "locataire"],
            "Compromis de vente": ["compromis", "vente", "promesse", "acquereur", "vendeur"],
            "CV(s) du(des) associé(s)": ["cv", "curriculum", "vitae", "expérience", "formation"],
            "Avis d'imposition": ["avis", "imposition", "impôt", "fiscal", "revenu"],
            "Bilan et compte de résultat": ["bilan", "compte", "résultat", "actif", "passif"],
            "Diagnostic de performance énergétique": ["dpe", "diagnostic", "performance", "énergétique", "énergie"],
            "Pièce d'identité du représentant légal": ["carte", "identité", "cni", "passeport", "né"],
            "Attestation d'assurance": ["assurance", "garantie", "attestation", "contrat"],
            "RIB de l'emprunteur": ["rib", "relevé", "iban", "bic", "banque"]
        }

        # Compter les occurrences de mots-clés
        scores = {}
        for doc_type, doc_keywords in keywords.items():
            score = sum(1 for keyword in doc_keywords if keyword in text_lower)
            if score > 0:
                scores[doc_type] = score

        if scores:
            # Prendre le type avec le plus de mots-clés
            best_type = max(scores.keys(), key=lambda x: scores[x])
            confidence = min(scores[best_type] / 5, 0.8)  # Confiance basée sur le nombre de mots-clés

            return {
                "document_type": best_type,
                "category": self.categories.get(best_type, "Autre"),
                "confidence": confidence,
                "key_information": {},
                "reasoning": f"Classification basée sur {scores[best_type]} mot(s)-clé(s) trouvé(s)"
            }

        # Classification par défaut si aucun mot-clé trouvé
        return {
            "document_type": "Document non identifié",
            "category": "Autre",
            "confidence": 0.1,
            "key_information": {},
            "reasoning": "Aucun mot-clé reconnaissable trouvé"
        }

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