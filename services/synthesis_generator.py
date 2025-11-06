"""
Service de génération de la Carte de Financement - Version améliorée
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from config import config

from models.schemas import CARTE_FINANCEMENT_MODEL, SyntheseProjet, ProfilEmprunteur, RevenusEmprunteur, PatrimoineImmobilier, PatrimoineMobilier, SocieteInformation, PlanFinancement, AnalyseFinanciere
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
            max_tokens=4000
        )
        self.initialized = True

    def _generate_dossier_id(self) -> str:
        """Générer un identifiant de dossier unique"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"DOSS-{timestamp}"

    def _get_all_extractions_with_texts(self, document_ids: List[int]) -> Dict:
        """
        Récupérer toutes les extractions et les textes bruts des documents
        """
        logger.info(f"🔍 [EXTRACTIONS] Récupération de {len(document_ids)} documents depuis la base...")
        documents = get_documents_with_extractions(document_ids)
        logger.info(f"✅ [EXTRACTIONS] {len(documents)} documents récupérés")

        # Récupérer les textes bruts des documents
        conn = sqlite3.connect("documents.db")
        cursor = conn.cursor()
        placeholders = ','.join(['?' for _ in document_ids])
        cursor.execute(f'''
            SELECT id, filename, extracted_text, detected_type, detected_category
            FROM documents
            WHERE id IN ({placeholders})
        ''', document_ids)
        raw_documents = cursor.fetchall()
        conn.close()

        all_extractions = []
        raw_texts = {}
        
        for doc in documents:
            extraction = {
                "document_id": doc["id"],
                "filename": doc["filename"],
                "detected_type": doc["detected_type"],
                "detected_category": doc["detected_category"],
                "extracted_data": doc["extracted_data"],
                "confidence": doc["confidence"]
            }
            all_extractions.append(extraction)
            logger.debug(f"📄 [EXTRACTIONS] Document {doc['id']}: {doc['detected_type']}")

        # Ajouter les textes bruts
        for raw_doc in raw_documents:
            raw_texts[raw_doc[0]] = {
                "filename": raw_doc[1],
                "text": raw_doc[2],
                "type": raw_doc[3],
                "category": raw_doc[4]
            }

        result = {
            "extractions": all_extractions,
            "raw_texts": raw_texts
        }
        
        logger.info(f"📦 [EXTRACTIONS] Données formatées: {len(json.dumps(all_extractions, ensure_ascii=False))} caractères pour extractions, {sum(len(text) for text in raw_texts.values())} caractères pour textes bruts")
        return result

    def _create_section_prompt(self, section: str, extractions_data: Dict, custom_prompt: Optional[str] = None) -> str:
        """
        Créer un prompt spécifique pour chaque section de la Carte de Financement

        Args:
            section: Nom de la section à générer
            extractions_data: Données extraites des documents
            custom_prompt: Instructions personnalisées à intégrer dans le prompt
        """
        extractions_json = json.dumps(extractions_data["extractions"], indent=2, ensure_ascii=False)
        raw_texts_str = "\n\n".join([f"Document: {info['filename']} (Type: {info['type']})\nContenu: {info['text'][:2000]}..." for info in extractions_data["raw_texts"].values()])

        # Fonction helper pour ajouter les instructions personnalisées
        def add_custom_instructions(base_prompt: str) -> str:
            if custom_prompt:
                custom_section = f"""

{'='*80}
INSTRUCTIONS PERSONNALISÉES:
{custom_prompt}
{'='*80}

Appliquez ces instructions personnalisées lors de la génération de cette section, en plus des instructions de base ci-dessus.
"""
                return base_prompt + custom_section
            return base_prompt

        if section == "synthese_projet":
            base_prompt = f"""Tu es un expert financier. Génère la synthèse du projet à partir des données suivantes :

Données extraites des documents :
{extractions_json}

Textes bruts des documents (extraits) :
{raw_texts_str}

Génère spécifiquement la section 'synthese_projet' de la Carte de Financement en utilisant TOUTES ces informations.
Respecte le modèle Pydantic et utilise chaque donnée extraite.
Ne laisse AUCUN champ vide, fais des inférences si nécessaire basées sur les données disponibles.

Voici les champs à remplir :
- description: Description complète du projet immobilier ou professionnel
- objectif_financement: Objectif principal du financement
- lieu: Lieu du projet (ville, département)
- montant_total: Montant total du projet en euros
- duree: Durée du projet ou du financement
- garanties: Garanties prévues

Réponds UNIQUEMENT avec le JSON valide pour la section 'synthese_projet' selon le modèle Pydantic."""
            return add_custom_instructions(base_prompt)

        elif section == "profil_emprunteur":
            base_prompt = f"""Tu es un expert financier. Génère le profil de l'emprunteur à partir des données suivantes :

Données extraites des documents :
{extractions_json}

Textes bruts des documents (extraits) :
{raw_texts_str}

Génère spécifiquement la section 'profil_emprunteur' de la Carte de Financement en utilisant TOUTES ces informations.
Respecte le modèle Pydantic et utilise chaque donnée extraite.
Ne laisse AUCUN champ vide, fais des inférences si nécessaire basées sur les données disponibles.

Voici les champs à remplir :
- identite: Informations d'identité complètes (civilite, nom, prenoms, date_naissance, lieu_naissance, nationalite, email, telephone, profession)
- situation_familiale: Situation familiale (marié, pacsé, célibataire, etc.)
- regime_matrimonial: Régime matrimonial si applicable
- adresse: Adresse personnelle (numero_voie, nom_voie, code_postal, ville, pays)
- enfants_a_charge: Nombre et âge des enfants à charge

Réponds UNIQUEMENT avec le JSON valide pour la section 'profil_emprunteur' selon le modèle Pydantic."""
            return add_custom_instructions(base_prompt)

        elif section == "revenus":
            base_prompt = f"""Tu es un expert financier. Génère les revenus de l'emprunteur à partir des données suivantes :

Données extraites des documents :
{extractions_json}

Textes bruts des documents (extraits) :
{raw_texts_str}

Génère spécifiquement la section 'revenus' de la Carte de Financement en utilisant TOUTES ces informations.
Respecte le modèle Pydantic et utilise chaque donnée extraite, notamment des avis d'imposition, bulletins de salaire, Kbis, etc.
Ne laisse AUCUN champ vide, fais des inférences si nécessaire basées sur les données disponibles.

Voici les champs à remplir :
- revenus_annuels_moyens: Revenus annuels moyens sur 3 ans en euros
- dernier_revenu_fiscal: Dernier revenu fiscal de référence en euros
- revenus_mensuels: Revenus mensuels nets en euros
- bonus_primes: Bonus et primes annuels en euros
- revenus_fonciers: Revenus fonciers annuels en euros
- autres_revenus: Autres revenus réguliers en euros

DONNEES SPECIFIQUES A INTEGRER:
- Données des avis d'imposition (revenu fiscal de référence, impôt sur le revenu)
- Informations des bulletins de salaire si disponibles
- Revenus déclarés dans les bilans d'entreprise
- Revenus fonciers des déclarations fiscales
- Revenus de la société F.M.R. si identifiés

INCLUSIONS SPECIFIQUES:
- Tableau de répartition des revenus par source si possible
- Analyse de la stabilité des revenus
- Comparaison entre revenus déclarés et revenus professionnels

Réponds UNIQUEMENT avec le JSON valide pour la section 'revenus' selon le modèle Pydantic."""
            return add_custom_instructions(base_prompt)

        elif section == "patrimoine_immobilier":
            base_prompt = f"""Tu es un expert financier. Génère le patrimoine immobilier à partir des données suivantes :

Données extraites des documents :
{extractions_json}

Textes bruts des documents (extraits) :
{raw_texts_str}

Génère spécifiquement la section 'patrimoine_immobilier' de la Carte de Financement en utilisant TOUTES ces informations.
Respecte le modèle Pydantic et utilise chaque donnée extraite, notamment des documents d'évaluation, compromis de vente, avis de valeur, etc.
Ne laisse AUCUN champ vide, fais des inférences si nécessaire basées sur les données disponibles.

Voici les champs à remplir :
- biens_immobiliers: Liste détaillée des biens immobiliers possédés avec caractéristiques (type, surface, localisation, etc.)
- valeur_estimee_totale: Valeur estimée totale du patrimoine immobilier en euros
- credits_restants_dus: Total des crédits restants dus en euros
- loyers_percus_annuels: Loyers perçus annuellement en euros
- patrimoine_net_immobilier: Patrimoine net immobilier en euros

DONNEES SPECIFIQUES A INTEGRER:
- Informations des documents d'évaluation (avis de valeur, etc.)
- Détails des biens du compromis de vente
- Informations sur les prêts immobiliers en cours
- Caractéristiques techniques des biens (surface, type de logement, etc.)

INCLUSIONS SPECIFIQUES:
- Tableau détaillé des biens si possible (bien / caractéristiques / valeur / loyer annuel)
- Analyse de la couverture des crédits par la valeur immobilière
- Répartition du patrimoine immobilier par type de bien

Réponds UNIQUEMENT avec le JSON valide pour la section 'patrimoine_immobilier' selon le modèle Pydantic."""
            return add_custom_instructions(base_prompt)

        elif section == "patrimoine_mobilier":
            base_prompt = f"""Tu es un expert financier. Génère le patrimoine mobilier à partir des données suivantes :

Données extraites des documents :
{extractions_json}

Textes bruts des documents (extraits) :
{raw_texts_str}

Génère spécifiquement la section 'patrimoine_mobilier' de la Carte de Financement en utilisant TOUTES ces informations.
Respecte le modèle Pydantic et utilise chaque donnée extraite.
Ne laisse AUCUN champ vide, fais des inférences si nécessaire basées sur les données disponibles.

Voici les champs à remplir :
- comptes_bancaires: Solde total des comptes bancaires en euros
- epargne_financiere: Montant total de l'épargne financière en euros
- assurance_vie: Montant assurance vie en euros
- autres_investissements: Autres investissements financiers en euros
- patrimoine_mobilier_total: Total patrimoine mobilier en euros

Réponds UNIQUEMENT avec le JSON valide pour la section 'patrimoine_mobilier' selon le modèle Pydantic."""
            return add_custom_instructions(base_prompt)

        elif section == "societes":
            base_prompt = f"""Tu es un expert financier. Génère les informations sur les sociétés à partir des données suivantes :

Données extraites des documents :
{extractions_json}

Textes bruts des documents (extraits) :
{raw_texts_str}

Génère spécifiquement la section 'societes' de la Carte de Financement en utilisant TOUTES ces informations.
Respecte le modèle Pydantic et utilise chaque donnée extraite, notamment des documents de type 'Liasses fiscales société emprunteur', 'Bilan et compte de résultat détaillés de l'emprunteur', 'Statuts société emprunteur', 'KBIS société emprunteur'.
Ne laisse AUCUN champ vide, fais des inférences si nécessaire basées sur les données disponibles.

Voici les champs à remplir pour chaque société :
- raison_sociale: Nom de la société
- forme_juridique: Forme juridique (SAS, SARL, etc.)
- pourcentage_detention: Pourcentage de détention
- chiffre_affaires_n1: Chiffre d'affaires N-1 en euros
- resultat_net_n1: Résultat net N-1 en euros
- dettes_totales: Dettes totales en euros
- fonds_propres: Fonds propres en euros
- activite: Description de l'activité principale

ATTENTION:
- Si plusieurs sociétés sont identifiées, renvoie une liste de toutes les sociétés
- Utilise des données spécifiques des bilans et liasses fiscales pour les indicateurs financiers
- Identifie les sociétés à partir des documents KBIS et Statuts
- Si aucune société n'est trouvée, renvoie une liste vide []

DONNEES SPECIFIQUES A RECHERCHER:
- Pour les chiffres d'affaires et résultats: cherche dans 'Liasses fiscales société emprunteur', 'Bilan et compte de résultat détaillés'
- Pour les détails juridiques: cherche dans 'KBIS société emprunteur', 'Statuts société emprunteur'
- Pour les détails de propriété: cherche dans les documents associés aux associés

Réponds UNIQUEMENT avec le JSON valide pour la section 'societes' selon le modèle Pydantic."""
            return add_custom_instructions(base_prompt)

        elif section == "plan_financement":
            base_prompt = f"""Tu es un expert financier. Génère le plan de financement à partir des données suivantes :

Données extraites des documents :
{extractions_json}

Textes bruts des documents (extraits) :
{raw_texts_str}

Génère spécifiquement la section 'plan_financement' de la Carte de Financement en utilisant TOUTES ces informations.
Respecte le modèle Pydantic et utilise chaque donnée extraite, notamment les détails du compromis de vente, devis travaux, etc.
Ne laisse AUCUN champ vide, fais des inférences si nécessaire basées sur les données disponibles.

Voici les champs à remplir :
- apport_personnel: Montant de l'apport personnel en euros
- pret_sollicite: Montant du prêt sollicité en euros
- duration_pret: Durée du prêt souhaitée
- taux_estime: Taux d'intérêt estimé
- mensualite_estimee: Mensualité estimée en euros
- garanties_prevues: Garanties prévues pour le financement
- autres_financements: Autres sources de financement

DONNEES SPECIFIQUES A INTEGRER:
- Les montants du compromis de vente ou acte de propriété
- Les coûts de travaux mentionnés dans les devis
- Les apports potentiels identifiés dans les documents financiers
- Les autres financements éventuels (PEA, assurance-vie, etc.)

INCLUSIONS SPECIFIQUES:
- Tableau de financement détaillé si possible (poste / montant)
- Analyse de la structure du financement
- Détail des sources et utilisations de fonds

Réponds UNIQUEMENT avec le JSON valide pour la section 'plan_financement' selon le modèle Pydantic."""
            return add_custom_instructions(base_prompt)

        elif section == "analyse_financiere":
            base_prompt = f"""Tu es un expert financier. Génère l'analyse financière à partir des données suivantes :

Données extraites des documents :
{extractions_json}

Textes bruts des documents (extraits) :
{raw_texts_str}

Génère spécifiquement la section 'analyse_financiere' de la Carte de Financement en utilisant TOUTES ces informations.
Respecte le modèle Pydantic et utilise chaque donnée extraite, notamment les chiffres des bilans, liasses fiscales et avis d'imposition.
Ne laisse AUCUN champ vide, fais des inférences si nécessaire basées sur les données disponibles.

Voici les champs à remplir :
- capacite_emprunt: Capacité d'emprunt mensuelle estimée en euros
- ratio_endettement: Ratio d'endettement actuel en pourcentage
- patrimoine_net_total: Patrimoine net total en euros
- ratio_patrimoine_emprunt: Ratio patrimoine/emprunt
- points_forts: Principaux points forts du dossier (minimum 3 points avec détails spécifiques)
- points_vigilance: Points de vigilance identifiés (minimum 3 points avec détails spécifiques)
- recommandation: Recommandation finale sur le financement avec justifications détaillées

DONNEES SPECIFIQUES A INTEGRER:
- Les ratios financiers à partir des bilans et liasses fiscales
- Les revenus déclarés dans les avis d'imposition
- Les capitaux propres, dettes et autres indicateurs financiers
- Les analyses croisées entre patrimoine, revenus et capacités d'emprunt

INCLUSIONS SPECIFIQUES:
- Tableau récapitulatif des indicateurs clés si possible
- Analyse comparative des données financières
- Notation du risque (ex: faible/moyen/élevé) avec justification

Réponds UNIQUEMENT avec le JSON valide pour la section 'analyse_financiere' selon le modèle Pydantic."""
            return add_custom_instructions(base_prompt)

    async def _generate_section(self, section: str, extractions_data: Dict, custom_prompt: Optional[str] = None) -> Optional[Dict]:
        """
        Générer une section spécifique de la Carte de Financement

        Args:
            section: Nom de la section à générer
            extractions_data: Données extraites des documents
            custom_prompt: Instructions personnalisées à intégrer dans le prompt
        """
        logger.info(f"📝 [SECTION-{section.upper()}] Création du prompt pour la section {section}...")
        prompt = self._create_section_prompt(section, extractions_data, custom_prompt)
        logger.info(f"✅ [SECTION-{section.upper()}] Prompt créé ({len(prompt)} caractères)")

        # Créer le template
        template = ChatPromptTemplate.from_messages([
            ("user", "{prompt}")
        ])

        # Déterminer le modèle de sortie approprié pour chaque section
        model_mapping = {
            "synthese_projet": SyntheseProjet,
            "profil_emprunteur": ProfilEmprunteur,
            "revenus": RevenusEmprunteur,
            "patrimoine_immobilier": PatrimoineImmobilier,
            "patrimoine_mobilier": PatrimoineMobilier,
            "plan_financement": PlanFinancement,
            "analyse_financiere": AnalyseFinanciere
        }

        # Générer avec le LLM
        logger.info(f"🤖 [SECTION-{section.upper()}] Lancement appel LLM...")
        start_time = datetime.now()
        try:
            # Pour la section des sociétés, on gère spécifiquement car c'est une liste
            if section == "societes":
                # Tentons de demander une liste spécifique de sociétés
                try:
                    # Créer un prompt qui explicite la demande d'une liste
                    modified_prompt = prompt + "\n\nIMPORTANT: Réponds UNIQUEMENT avec une liste JSON de sociétés, même si une seule société est trouvée. Si aucune société n'est trouvée, réponds avec une liste vide []."
                    chain = self.llm
                    result = await chain.ainvoke(modified_prompt)
                    
                    # Si le résultat est une chaîne, on la parse en tant que JSON
                    if isinstance(result, str):
                        # Nettoyer le format markdown s'il y en a
                        import re
                        # Enlever les éventuels marqueurs de code
                        cleaned_result = re.sub(r'^```.*\n?', '', result)
                        cleaned_result = re.sub(r'\n?```.*$', '', cleaned_result)
                        try:
                            parsed_result = json.loads(cleaned_result)
                            # Retourner sous forme de liste
                            if isinstance(parsed_result, list):
                                # Vérifier que chaque élément de la liste est correctement formaté
                                validated_list = []
                                for item in parsed_result:
                                    if isinstance(item, dict):
                                        # Assurer que tous les champs requis sont présents
                                        required_fields = ["raison_sociale", "forme_juridique", "pourcentage_detention", 
                                                         "chiffre_affaires_n1", "resultat_net_n1", "dettes_totales", 
                                                         "fonds_propres", "activite"]
                                        for field in required_fields:
                                            if field not in item or item[field] in [None, ""]:
                                                item[field] = "Non spécifié"
                                        validated_list.append(item)
                                return validated_list
                            elif parsed_result is None:
                                return []
                            else:
                                # Si c'est un objet unique, le mettre dans une liste après validation
                                if isinstance(parsed_result, dict):
                                    required_fields = ["raison_sociale", "forme_juridique", "pourcentage_detention", 
                                                     "chiffre_affaires_n1", "resultat_net_n1", "dettes_totales", 
                                                     "fonds_propres", "activite"]
                                    for field in required_fields:
                                        if field not in parsed_result or parsed_result[field] in [None, ""]:
                                            parsed_result[field] = "Non spécifié"
                                    return [parsed_result] if parsed_result else []
                                else:
                                    return [parsed_result] if parsed_result else []
                        except json.JSONDecodeError:
                            logger.warning(f"❌ [SECTION-{section.upper()}] Impossible de parser le JSON pour la section sociétés: {result[:200]}...")
                            # Essayer de trouver des données de société dans le texte brut
                            # Rechercher des entités connues qui pourraient représenter des sociétés
                            return []  # Retourner une liste vide en cas d'échec
                    elif isinstance(result, dict):
                        # Si on reçoit un seul dictionnaire, le mettre dans une liste après validation
                        required_fields = ["raison_sociale", "forme_juridique", "pourcentage_detention", 
                                         "chiffre_affaires_n1", "resultat_net_n1", "dettes_totales", 
                                         "fonds_propres", "activite"]
                        for field in required_fields:
                            if field not in result or result[field] in [None, ""]:
                                result[field] = "Non spécifié"
                        return [result] if result else []
                    elif isinstance(result, list):
                        # Valider chaque élément de la liste
                        validated_list = []
                        for item in result:
                            if isinstance(item, dict):
                                required_fields = ["raison_sociale", "forme_juridique", "pourcentage_detention", 
                                                 "chiffre_affaires_n1", "resultat_net_n1", "dettes_totales", 
                                                 "fonds_propres", "activite"]
                                for field in required_fields:
                                    if field not in item or item[field] in [None, ""]:
                                        item[field] = "Non spécifié"
                                validated_list.append(item)
                        return validated_list
                    else:
                        return []
                except Exception as e2:
                    logger.error(f"❌ [SECTION-{section.upper()}] Erreur secondaire lors de la génération des sociétés: {str(e2)}")
                    return []
            else:
                chain = template | self.llm.with_structured_output(model_mapping[section])
                result = await chain.ainvoke({"prompt": prompt})
                return result.model_dump() if hasattr(result, 'model_dump') else result
        except Exception as e:
            logger.error(f"❌ [SECTION-{section.upper()}] Erreur lors de la génération de la section {section}: {str(e)}")
            # Retourner une instance vide du modèle en cas d'erreur pour les sections autres que sociétés
            if section == "societes":
                return []
            else:
                empty_model = model_mapping[section]()
                return empty_model.model_dump() if hasattr(empty_model, 'model_dump') else {}

    async def generate_synthesis(self, document_ids: List[int], custom_prompt: Optional[str] = None) -> Dict:
        """
        Générer la synthèse à partir des documents avec des appels LLM séparés pour chaque section

        Args:
            document_ids: Liste des IDs des documents à analyser
            custom_prompt: Instructions personnalisées pour enrichir la génération
        """
        import sqlite3  # Ajout de l'import nécessaire
        
        logger.info(f"🔄 [SYNTHESE] Début génération synthèse pour {len(document_ids)} documents")
        try:
            # Récupérer toutes les extractions et textes bruts
            logger.info(f"📄 [SYNTHESE] Récupération des extractions et textes bruts pour documents IDs: {document_ids}")
            extractions_data = self._get_all_extractions_with_texts(document_ids)
            logger.info(f"✅ [SYNTHESE] Données récupérées (extractions: {len(extractions_data['extractions'])}, textes: {len(extractions_data['raw_texts'])})")

            # Générer chaque section séparément
            logger.info(f"🔄 [SYNTHESE] Génération des sections séparément...")
            
            # Définir les sections dans l'ordre
            sections = [
                "synthese_projet", "profil_emprunteur", "revenus", "patrimoine_immobilier",
                "patrimoine_mobilier", "societes", "plan_financement", "analyse_financiere"
            ]
            
            # Initialiser la structure de la synthèse
            synthesis_result = {}
            
            # Générer chaque section
            for section in sections:
                logger.info(f"🔄 [SYNTHESE] Génération de la section: {section}")
                section_data = await self._generate_section(section, extractions_data, custom_prompt)
                
                if section == "societes":
                    # La section societes doit toujours être une liste
                    if section_data is None:
                        synthesis_result[section] = []
                    elif isinstance(section_data, list):
                        synthesis_result[section] = section_data
                    else:
                        # Si ce n'est pas une liste, on le met dans une liste
                        synthesis_result[section] = [section_data] if section_data else []
                else:
                    # Pour les autres sections, on ajoute directement les données
                    synthesis_result[section] = section_data or {}
                
                logger.info(f"✅ [SYNTHESE] Section {section} générée")

            # Ajouter les métadonnées
            logger.info(f"🏷️ [SYNTHESE] Ajout des métadonnées...")
            dossier_id = self._generate_dossier_id()
            
            # Compléter la synthèse avec les champs manquants
            synthesis_result['dossier_id'] = dossier_id
            synthesis_result['date_generation'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            synthesis_result['documents_sources'] = ", ".join([doc['filename'] for doc in extractions_data['extractions']])

            # Sauvegarder en base
            logger.info(f"💾 [SYNTHESE] Sauvegarde en base de données...")
            synthese_id = insert_synthese(
                dossier_id=dossier_id,
                input_documents=json.dumps(document_ids),
                synthese_text=json.dumps(synthesis_result, ensure_ascii=False, indent=2),
                confidence=0.85
            )
            logger.info(f"✅ [SYNTHESE] Sauvegarde réussie, ID: {synthese_id}")

            return {
                "success": True,
                "synthese_id": synthese_id,
                "dossier_id": dossier_id,
                "synthese": synthesis_result,
                "message": "Synthèse générée avec succès"
            }

        except Exception as e:
            logger.error(f"❌ [SYNTHESE] Erreur lors de la génération: {str(e)}")
            import traceback
            logger.error(f"❌ [SYNTHESE] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_complete_synthesis(self, document_ids: List[int], custom_prompt: Optional[str] = None) -> Dict:
        """
        Générer la synthèse complète (JSON + Document Word)

        Args:
            document_ids: Liste des IDs des documents à analyser
            custom_prompt: Instructions personnalisées pour enrichir la génération
        """
        logger.info(f"🚀 [SYNTHESE-COMPLETE] Début génération complète pour {len(document_ids)} documents")
        try:
            # Générer la synthèse
            logger.info(f"📄 [SYNTHESE-COMPLETE] Étape 1/2: Génération de la synthèse...")
            synthese_result = await self.generate_synthesis(document_ids, custom_prompt)

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
            import traceback
            logger.error(f"❌ [SYNTHESE-COMPLETE] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }
