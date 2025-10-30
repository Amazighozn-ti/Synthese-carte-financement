"""
Service de génération de la Carte de Financement
"""

import json
from datetime import datetime
from typing import List, Dict
from pathlib import Path
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from config import config
from models.schemas import CARTE_FINANCEMENT_MODEL
from database import get_documents_with_extractions, insert_synthese


class SynthesisGenerator:
    """Service pour générer la synthèse de financement (Carte de Financement)"""

    @staticmethod
    def format_json_readable(data: dict) -> str:
        """
        Formatter un JSON de manière lisible et美化

        Args:
            data: Données à formater

        Returns:
            str: JSON formaté avec indentation
        """
        return json.dumps(data, indent=2, ensure_ascii=False)

    def __init__(self):
        """Initialiser le service de synthèse"""
        try:
            self.llm = ChatMistralAI(
                model=config.MISTRAL_MODEL,
                temperature=0.1,  # Température basse pour plus de cohérence
                max_tokens=4000
            )
            self.initialized = True
            print("✅ SynthesisGenerator LLM initialisé")

        except Exception as e:
            print(f"❌ Erreur initialisation SynthesisGenerator: {e}")
            self.initialized = False
            raise

    def _generate_dossier_id(self) -> str:
        """Générer un identifiant de dossier unique"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"DOSS-{timestamp}"

    def _prepare_documents_data(self, document_ids: List[int]) -> Dict:
        """
        Préparer et structurer les données des documents pour la synthèse

        Args:
            document_ids: Liste des IDs de documents à analyser

        Returns:
            Dict: Données structurées par catégorie
        """
        print(f"📥 Récupération des documents avec extractions pour IDs: {document_ids}")
        # Récupérer les documents avec leurs extractions
        documents = get_documents_with_extractions(document_ids)
        print(f"📄 Documents récupérés: {len(documents)}")

        if not documents:
            raise ValueError("Aucun document trouvé ou aucun document avec des données d'extraction")

        # Structurer les données par catégorie
        structured_data = {
            "emprunteur": {},
            "revenus": {},
            "patrimoine_immobilier": {},
            "patrimoine_mobilier": {},
            "societes": [],
            "projet": {},
            "documents_sources": []
        }
        print(f"✅ Données structurées initialisées avec {len(structured_data)} catégories")

        for doc in documents:
            # Ajouter à la liste des sources
            structured_data["documents_sources"].append(f"{doc['detected_type']} ({doc['filename']})")

            # Traiter les données d'extraction selon la catégorie
            extraction = doc["extracted_data"]
            if not extraction:
                continue

            doc_type = doc["detected_type"]
            doc_category = doc["detected_category"]

            # Utiliser la catégorie détectée pour classer les documents plus efficacement
            if doc_category in ["Associés", "Etat civil"]:
                structured_data["emprunteur"][doc_type] = extraction
            
            elif doc_category == "Revenus":
                structured_data["revenus"][doc_type] = extraction
            
            elif doc_category == "Patrimoine immobilier":
                structured_data["patrimoine_immobilier"][doc_type] = extraction
            
            elif doc_category in ["Banque et épargne", "Crédits et charges divers hors immobilier"]:
                structured_data["patrimoine_mobilier"][doc_type] = extraction
            
            elif doc_category in ["Company", "Sociétés contrôlées"]:
                structured_data["societes"].append({
                    "type": doc_type,
                    "data": extraction,
                    "category": doc_category
                })
            
            elif doc_category in ["Object", "Sale", "Works"]:
                structured_data["projet"][doc_type] = extraction
            
            # Si la catégorie n'est pas disponible ou manquante, on utilise une logique de secours
            else:
                # Informations sur l'emprunteur
                if doc_type in ["CV(s) du(des) associés", "Carte d'identité(recto verso) ou Passeport",
                               "Justificatif de domicile", "Livret de famille", "Contrat de mariage"]:
                    structured_data["emprunteur"][doc_type] = extraction

                # Revenus
                elif doc_type.startswith("Avis d'imposition"):
                    structured_data["revenus"][doc_type] = extraction

                # Patrimoine immobilier
                elif doc_type in ["Dernière taxe foncière", "Attestation notariée d'acquisition indiquant le prix",
                                 "Bail", "Tableau d'amortissement du crédit immobilier", "Dernière déclaration 2044"]:
                    structured_data["patrimoine_immobilier"][doc_type] = extraction

                # Patrimoine mobilier/bancaire
                elif doc_type.startswith("Relevé de compte") or doc_type == "Dernier relevé d'épargne":
                    structured_data["patrimoine_mobilier"][doc_type] = extraction

                # Sociétés - Ajoutons tous les types liés aux sociétés
                elif ("société" in doc_type.lower() or
                      "kbis" in doc_type.lower() or
                      "statuts" in doc_type.lower() or
                      "bilan" in doc_type.lower() or
                      "liasses" in doc_type.lower() or
                      doc_type in ["Organigramme des sociétés de la société emprunteur", "PV d'AG autorisant la société à emprunter"]):
                    structured_data["societes"].append({
                        "type": doc_type,
                        "data": extraction,
                        "category": doc_category
                    })

                # Projet
                elif doc_type in ["Compromis de vente", "Bail ou projet de bail du bien objet de l'acquisition",
                                "Arrêté du permis de construire"]:
                    structured_data["projet"][doc_type] = extraction

                # Autres documents qui pourraient contenir des informations pertinentes
                else:
                    # Vérifier si c'est un document d'assurance-vie, IFI, ou autres documents financiers
                    if "ifi" in doc_type.lower() or "assurance vie" in doc_type.lower():
                        structured_data["patrimoine_mobilier"][doc_type] = extraction
                    elif "relevé" in doc_type.lower() or "épargne" in doc_type.lower():
                        structured_data["patrimoine_mobilier"][doc_type] = extraction
                    elif "synthese" in doc_type.lower() or "projet" in doc_type.lower():
                        structured_data["projet"][doc_type] = extraction
                    elif "devis" in doc_type.lower() or "travaux" in doc_type.lower():
                        structured_data["projet"][doc_type] = extraction
                    elif "compromis" in doc_type.lower() or "vente" in doc_type.lower():
                        structured_data["projet"][doc_type] = extraction
                    elif "valeur" in doc_type.lower() or "estimation" in doc_type.lower():
                        structured_data["patrimoine_immobilier"][doc_type] = extraction
                    else:
                        # Pour les documents 'Autre', tentons de comprendre le contenu
                        structured_data["emprunteur"][doc_type] = extraction

        return structured_data

    def _enhance_documents_data(self, documents_data: Dict) -> Dict:
        """
        Enrichir et structurer les données pour faciliter l'extraction par le LLM

        Args:
            documents_data: Données structurées des documents

        Returns:
            Dict: Données enrichies avec calculs automatiques
        """
        # Créer une copie pour ne pas modifier l'original
        enhanced_data = documents_data.copy()

        # === ENRICHISSEMENT DES DONNÉES EMPRUNTEUR ===
        emprunteur = enhanced_data.get("emprunteur", {})
        identite_info = {}

        # Extraire les informations d'identité depuis tous les documents emprunteur
        for extraction in emprunteur.values():
            try:
                if isinstance(extraction, str):
                    extraction_data = json.loads(extraction)
                else:
                    extraction_data = extraction

                # Récupérer les informations d'identité
                if "extracted_fields" in extraction_data:
                    fields = extraction_data["extracted_fields"]
                else:
                    fields = extraction_data

                # Fusionner les informations d'identité
                for key in ["civilite", "nom", "prenoms", "date_naissance", "lieu_naissance",
                           "nationalite", "profession"]:
                    if key in fields and identite_info.get(key) == "Non spécifié":
                        identite_info[key] = fields[key]

                # Récupérer l'adresse
                if "adresse" in fields and isinstance(fields["adresse"], dict):
                    identite_info["adresse_complete"] = fields["adresse"]

            except (json.JSONDecodeError, AttributeError, TypeError):
                continue

        enhanced_data["emprunteur"]["identite_fusionnee"] = identite_info

        # === ENRICHISSEMENT DES REVENUS ===
        revenus = enhanced_data.get("revenus", {})
        revenus_info = {}

        for extraction in revenus.values():
            try:
                if isinstance(extraction, str):
                    extraction_data = json.loads(extraction)
                else:
                    extraction_data = extraction

                if "extracted_fields" in extraction_data:
                    fields = extraction_data["extracted_fields"]
                else:
                    fields = extraction_data

                # Extraire les informations fiscales
                if "revenu_fiscal_reference" in fields:
                    revenus_info["revenu_fiscal_reference"] = fields["revenu_fiscal_reference"]
                    # Calculer les revenus mensuels approximatifs
                    try:
                        rfr_value = fields["revenu_fiscal_reference"].replace("€", "").replace(" ", "").replace(",", ".")
                        rfr_float = float(rfr_value)
                        revenus_info["revenus_mensuels_estimes"] = f"{int(rfr_float / 12):,} €".replace(",", " ")
                    except (ValueError, AttributeError):
                        pass

            except (json.JSONDecodeError, AttributeError, TypeError):
                continue

        enhanced_data["revenus"]["infusions_fusionnees"] = revenus_info

        # === ENRICHISSEMENT DU PATRIMOINE ===
        patrimoine_mobilier = enhanced_data.get("patrimoine_mobilier", {})

        # Calculer le patrimoine mobilier total
        patrimoine_total = 0
        for extraction in patrimoine_mobilier.values():
            try:
                if isinstance(extraction, str):
                    extraction_data = json.loads(extraction)
                else:
                    extraction_data = extraction

                if "extracted_fields" in extraction_data:
                    fields = extraction_data["extracted_fields"]
                else:
                    fields = extraction_data

                # Chercher des montants dans les champs
                for value in fields.values():
                    if isinstance(value, str) and ("€" in value or "euros" in value.lower()):
                        try:
                            # Nettoyer et convertir le montant
                            montant_str = value.replace("€", "").replace(" ", "").replace(",", ".").lower()
                            montant_str = montant_str.replace("euros", "").strip()
                            montant = float(montant_str)
                            patrimoine_total += montant
                        except (ValueError, AttributeError):
                            continue

            except (json.JSONDecodeError, AttributeError, TypeError):
                continue

        if patrimoine_total > 0:
            enhanced_data["patrimoine_mobilier"]["total_calcule"] = f"{patrimoine_total:,.0f} €".replace(",", " ")

        # === ENRICHISSEMENT DES SOCIÉTÉS ===
        societes = enhanced_data.get("societes", [])
        societes_info = []

        for societe in societes:
            try:
                if isinstance(societe, dict) and "data" in societe:
                    data = societe["data"]
                    if isinstance(data, str):
                        data = json.loads(data)

                    if "extracted_fields" in data:
                        fields = data["extracted_fields"]
                    else:
                        fields = data

                    societes_info.append(fields)
            except (json.JSONDecodeError, AttributeError, TypeError):
                continue

        # Remplacer la liste par un dictionnaire avec les données enrichies
        enhanced_data["societes"] = {
            "original_data": societes,
            "donnees_fusionnees": societes_info
        }

        # === ENRICHISSEMENT DU PROJET ===
        projet = enhanced_data.get("projet", {})
        projet_info = {}

        for extraction in projet.values():
            try:
                if isinstance(extraction, str):
                    extraction_data = json.loads(extraction)
                else:
                    extraction_data = extraction

                if "extracted_fields" in extraction_data:
                    fields = extraction_data["extracted_fields"]
                else:
                    fields = extraction_data

                # Fusionner les informations du projet
                for key, value in fields.items():
                    if key not in projet_info or projet_info[key] == "Non spécifié":
                        projet_info[key] = value

            except (json.JSONDecodeError, AttributeError, TypeError):
                continue

        enhanced_data["projet"]["infos_fusionnees"] = projet_info

        return enhanced_data

    def _create_synthesis_prompt(self, documents_data: Dict) -> str:
        """
        Créer le prompt pour la génération de la synthèse

        Args:
            documents_data: Données structurées des documents

        Returns:
            str: Prompt pour le LLM
        """
        return f"""Tu es un expert analyste financier pour la société Carte Financement.

À partir des données extraites de plusieurs documents administratifs et financiers, tu dois générer une "Carte de Financement" complète et structurée.

INSTRUCTIONS DÉTAILLÉES :

1. UTILISATION DES DONNÉES :
   - AVIS D'IMPOSITION : Utilise le "revenu_fiscal_reference" pour "dernier_revenu_fiscal" et calcule "revenus_annuels_moyens"
   - BILANS SOCIÉTÉS : Extrais le chiffre d'affaires, résultat net, dettes totales, fonds propres
   - KBIS/STATUTS : Récupère la raison sociale, forme juridique, activité, représentant légal
   - ESTIMATIONS IMMOBILIÈRES : Utilise les valorisations pour le patrimoine immobilier
   - ASSURANCE-VIE/ÉPARGNE : Utilise ces montants pour le patrimoine mobilier
   - COMPROMIS/VENTE : Extrais les informations sur le projet (prix, lieu, description)

2. CHAMPS OBLIGATOIRES :
   - profil_emprunteur.identite : Utilise les données d'identité disponibles (nom, prénom, date naissance, etc.)
   - revenus : Utilise TOUJOURS le revenu fiscal de référence des avis d'imposition
   - patrimoine_immobilier : Compile tous les biens identifiés avec leurs valeurs
   - patrimoine_mobilier : Somme l'épargne, assurance-vie, liquidités
   - societes : Pour chaque société, extrais CA, résultat net, dettes, fonds propres

3. CALCULS AUTOMATIQUES :
   - patrimoine_net_total = patrimoine_immobilier + patrimoine_mobilier
   - ratio_patrimoine_emprunt = (patrimoine_net_total / pret_sollicite) * 100
   - ages des enfants : Si "enfants à charge" mentionné sans âge, indique "âges non spécifiés"

4. FORMATAGE :
   - Montants en euros avec espaces : "150 000 €"
   - Dates au format JJ/MM/AAAA
   - Points_forts et points_vigilance : TEXTES complets, PAS de listes

5. RÉDUIRE LES "Non spécifié" :
   - Utilise TOUTES les informations disponibles dans les documents
   - Pour un champ sans donnée directe, infère intelligemment (ex: profession → "Marchand de biens")
   - Uniquement "Non spécifié" si VRAIMENT aucune information n'est disponible
   - UTILISE les sections _fusionnees et _calcule pour des données plus précises

6. DONNÉES ENRICHISSES :
   - identite_fusionnee : Informations d'identité consolidées
   - infusions_fusionnees : Revenus avec calculs automatiques (revenus_mensuels_estimes)
   - total_calcule : Patrimoine mobilier total calculé automatiquement
   - donnees_fusionnees : Données des sociétés consolidées
   - infos_fusionnees : Informations du projet consolidées

DONNÉES DES DOCUMENTS À ANALYSER :

<EMPRUNTEUR>
{json.dumps(documents_data['emprunteur'], indent=2, ensure_ascii=False)}
</EMPRUNTEUR>

<REVENUS>
{json.dumps(documents_data['revenus'], indent=2, ensure_ascii=False)}
</REVENUS>

<PATRIMOINE IMMOBILIER>
{json.dumps(documents_data['patrimoine_immobilier'], indent=2, ensure_ascii=False)}
</PATRIMOINE IMMOBILIER>

<PATRIMOINE MOBILIER>
{json.dumps(documents_data['patrimoine_mobilier'], indent=2, ensure_ascii=False)}
</PATRIMOINE MOBILIER>

<SOCIÉTÉS>
{json.dumps(documents_data['societes'], indent=2, ensure_ascii=False)}
</SOCIÉTÉS>

<PROJET>
{json.dumps(documents_data['projet'], indent=2, ensure_ascii=False)}
</PROJET>

Génère maintenant une Carte de Financement complète en suivant exactement le modèle Pydantic CarteFinancement. Sois exhaustif et précis dans l'extraction des informations. Priorise les données enrichies (_fusionnees, _calcule) quand disponibles.
"""

    async def generate_synthesis(self, document_ids: List[int]) -> Dict:
        """
        Générer la synthèse de financement à partir des documents

        Args:
            document_ids: Liste des IDs de documents à analyser

        Returns:
            Dict: Résultat de la génération avec la synthèse
        """
        start_time = datetime.now()

        try:
            print(f"🔄 Début generation_synthesis pour {len(document_ids)} documents")

            # Préparer les données
            print("📋 Préparation des données...")
            documents_data = self._prepare_documents_data(document_ids)
            print(f"✅ Données préparées: {len(documents_data)} catégories")

            # Enrichir les données avec des calculs automatiques
            print("🔧 Enrichissement des données...")
            enhanced_data = self._enhance_documents_data(documents_data)

            # Créer le prompt
            print("📝 Création du prompt...")
            prompt = self._create_synthesis_prompt(enhanced_data)

            # Créer le template de prompt avec le modèle Pydantic
            extraction_template = ChatPromptTemplate.from_messages([
                ("system", """Tu es un expert en analyse financière. Génère une Carte de Financement complète
                et structurée en suivant EXACTEMENT le modèle Pydantic fourni. Sois précis, professionnel
                et exhaustif dans ton analyse. Les données doivent être cohérentes et bien formatées.

                CRUCIAL : Tous les champs de type string doivent rester des chaînes de caractères, notamment
                "points_forts" et "points_vigilance" qui doivent être du texte et non des listes."""),
                ("user", "{prompt}")
            ])

            # Générer la chaîne avec le modèle Pydantic
            chain = extraction_template | self.llm.with_structured_output(CARTE_FINANCEMENT_MODEL)

            # Invoquer le LLM
            print("🤖 Appel au LLM pour génération synthèse...")
            result = await chain.ainvoke({"prompt": prompt})
            print("✅ LLM a retourné un résultat")

            # Ajouter les informations de traçabilité
            dossier_id = self._generate_dossier_id()
            result.dossier_id = dossier_id
            result.date_generation = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            result.documents_sources = ", ".join(documents_data["documents_sources"])

            # Calculer le temps de traitement
            processing_time = (datetime.now() - start_time).total_seconds()

            # Sauvegarder en base de données
            print(f"💾 Sauvegarde en base de données (dossier_id: {dossier_id})...")
            synthese_id = insert_synthese(
                dossier_id=dossier_id,
                input_documents=json.dumps(document_ids),
                synthese_text=json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
                confidence=0.85  # Confiance par défaut pour la synthèse
            )
            print(f"✅ Synthèse sauvegardée (synthese_id: {synthese_id})")

            return {
                "success": True,
                "synthese_id": synthese_id,
                "dossier_id": dossier_id,
                "synthese": result.model_dump(),
                "processing_time": round(processing_time, 2),
                "documents_used": len(document_ids),
                "message": "Carte de Financement générée avec succès"
            }

        except ValueError as e:
            print(f"❌ ValueError dans generate_synthesis: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Erreur de données: {str(e)}",
                "processing_time": round((datetime.now() - start_time).total_seconds(), 2)
            }

        except ValidationError as e:
            print(f"❌ ValidationError dans generate_synthesis: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Erreur de validation du modèle: {str(e)}",
                "processing_time": round((datetime.now() - start_time).total_seconds(), 2)
            }

        except Exception as e:
            print(f"❌ Exception dans generate_synthesis: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Erreur lors de la génération de la synthèse: {str(e)}",
                "processing_time": round((datetime.now() - start_time).total_seconds(), 2)
            }

    async def generate_complete_synthesis(self, document_ids: List[int]) -> Dict:
        """
        Générer la synthèse complète (JSON + Document Word)

        Args:
            document_ids: Liste des IDs de documents à analyser

        Returns:
            Dict: Résultat complet avec synthèse et document généré
        """
        try:
            print(f"📄 Début génération synthèse complète pour {len(document_ids)} documents")

            # Étape 1: Générer la synthèse JSON
            print("🔄 Étape 1: Génération de la synthèse JSON...")
            synthese_result = await self.generate_synthesis(document_ids)

            if not synthese_result["success"]:
                print(f"❌ Échec génération synthèse JSON: {synthese_result.get('error')}")
                return synthese_result

            print(f"✅ Synthèse JSON générée (dossier_id: {synthese_result['dossier_id']})")

            # Étape 2: Générer le document Word à partir de la synthèse
            synthese_data = synthese_result["synthese"]
            dossier_id = synthese_result["dossier_id"]

            print("🔄 Étape 2: Génération du document Word...")
            # Utiliser le service dédié WordDocumentGenerator
            from services.word_generator import WordDocumentGenerator
            word_generator = WordDocumentGenerator()
            word_result = word_generator.generate_word_document(synthese_data, dossier_id)

            if not word_result["success"]:
                # Si la génération du Word échoue, on retourne quand même la synthèse
                print(f"⚠️  Échec génération Word: {word_result.get('error')}")
                return {
                    "success": True,
                    "synthese": synthese_result,
                    "word_document": {
                        "success": False,
                        "error": word_result["error"]
                    },
                    "message": "Synthèse générée avec succès, mais échec de la génération du document Word"
                }

            # Retourner le résultat complet
            print("✅ Génération complète réussie (JSON + Word)")
            return {
                "success": True,
                "synthese": synthese_result,
                "word_document": word_result,
                "message": "Carte de Financement complète générée avec succès (JSON + Word)"
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = f"Erreur lors de la génération complète: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }