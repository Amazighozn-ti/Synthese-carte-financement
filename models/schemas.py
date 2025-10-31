"""
Modèles Pydantic pour la sortie structurée du LLM
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


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


# Modèles Pydantic pour l'extraction structurée
class AdresseExtraction(BaseModel):
    """Structure d'adresse normalisée"""
    numero_voie: str = Field(description="Numéro dans la rue (ex: 12, 23bis)")
    nom_voie: str = Field(description="Nom de la rue/avenue/boulevard (ex: rue de la Paix)")
    code_postal: str = Field(description="Code postal à 5 chiffres (ex: 75001)")
    ville: str = Field(description="Nom de la ville (ex: Paris)")
    pays: Optional[str] = Field(default="France", description="Pays (ex: France)")
    complement: Optional[str] = Field(default="Non spécifié", description="Complément d'adresse (ex: appartement 4, étage 3)")

    class Config:
        json_schema_extra = {
            "example": {
                "numero_voie": "23",
                "nom_voie": "Rue de Ménilmontant",
                "code_postal": "75011",
                "ville": "Paris",
                "pays": "France",
                "complement": "Escalier B, 3ème étage"
            }
        }


class PersonneExtraction(BaseModel):
    """Informations personnelles d'une personne physique"""
    civilite: Optional[str] = Field(default="Non spécifié", description="Civilité (M, Mme, Mlle)")
    nom: str = Field(description="Nom de famille")
    prenoms: str = Field(description="Prénom(s) - séparer par des espaces si plusieurs")
    date_naissance: Optional[str] = Field(default="Non spécifié", description="Date de naissance (format JJ/MM/AAAA ou AAAA-MM-JJ)")
    lieu_naissance: Optional[str] = Field(default="Non spécifié", description="Lieu de naissance (ville, pays)")
    nationalite: Optional[str] = Field(default="Non spécifié", description="Nationalité")
    email: Optional[str] = Field(default="Non spécifié", description="Adresse email valide")
    telephone: Optional[str] = Field(default="Non spécifié", description="Numéro de téléphone avec indicatif si présent")
    profession: Optional[str] = Field(default="Non spécifié", description="Profession ou activité")

    class Config:
        json_schema_extra = {
            "example": {
                "civilite": "M",
                "nom": "DUPONT",
                "prenoms": "Jean Marie",
                "date_naissance": "15/03/1985",
                "lieu_naissance": "Paris, France",
                "nationalite": "Française",
                "email": "jean.dupont@email.com",
                "telephone": "+33 6 12 34 56 78",
                "profession": "Ingénieur"
            }
        }


class EntrepriseExtraction(BaseModel):
    """Informations complètes sur une entreprise"""
    raison_sociale: str = Field(description="Nom officiel complet de l'entreprise")
    forme_juridique: Optional[str] = Field(default="Non spécifié", description="Forme juridique exacte (SARL, SAS, EURL, etc.)")
    siren: Optional[str] = Field(default="Non spécifié", description="Numéro SIREN à 9 chiffres")
    siret: Optional[str] = Field(default="Non spécifié", description="Numéro SIRET à 14 chiffres")
    capital_social: Optional[str] = Field(default="Non spécifié", description="Capital social en euros avec devise si précisée")
    date_immatriculation: Optional[str] = Field(default="Non spécifié", description="Date d'immatriculation (format JJ/MM/AAAA)")
    adresse_siege: Optional[AdresseExtraction] = Field(default=None, description="Adresse complète du siège social")
    activite_principale: Optional[str] = Field(default="Non spécifié", description="Activité principale ou code NAF/APE")
    representant_legal: Optional[str] = Field(default="Non spécifié", description="Nom du représentant légal (gérant, président, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "raison_sociale": "SOCIÉTÉ ALPHA CONSEIL",
                "forme_juridique": "SAS",
                "siren": "812345678",
                "siret": "81234567800012",
                "capital_social": "10 000 €",
                "date_immatriculation": "12/05/2019",
                "adresse_siege": {
                    "numero_voie": "12",
                    "nom_voie": "Rue du Parc",
                    "code_postal": "75001",
                    "ville": "Paris",
                    "pays": "France"
                },
                "activite_principale": "Conseil en gestion",
                "representant_legal": "Jean MARTIN"
            }
        }


class BilanExtraction(BaseModel):
    """Extraction des données financières d'un bilan"""
    exercice_fiscal: str = Field(description="Exercice fiscal concerné (ex: 2023, N-1)")
    date_cloture: Optional[str] = Field(default="Non spécifié", description="Date de clôture de l'exercice (JJ/MM/AAAA)")
    total_actif: str = Field(description="Total de l'actif en euros")
    total_passif: str = Field(description="Total du passif en euros")
    chiffre_affaires: str = Field(description="Chiffre d'affaires en euros")
    resultat_exploitation: Optional[str] = Field(default="Non spécifié", description="Résultat d'exploitation en euros")
    resultat_net: str = Field(description="Résultat net en euros")
    fonds_propres: str = Field(description="Fonds propres en euros")
    endettement_total: Optional[str] = Field(default="Non spécifié", description="Endettement total en euros")
    effectif_moyen: Optional[str] = Field(default="Non spécifié", description="Effectif moyen de salariés")

    class Config:
        json_schema_extra = {
            "example": {
                "exercice_fiscal": "2023",
                "date_cloture": "31/12/2023",
                "total_actif": "1 250 000 €",
                "total_passif": "1 250 000 €",
                "chiffre_affaires": "2 100 000 €",
                "resultat_exploitation": "150 000 €",
                "resultat_net": "120 000 €",
                "fonds_propres": "450 000 €",
                "endettement_total": "800 000 €",
                "effectif_moyen": "12"
            }
        }


class VenteExtraction(BaseModel):
    """Informations sur une transaction immobilière"""
    vendeur: str = Field(description="Nom complet du vendeur")
    acheteur: str = Field(description="Nom complet de l'acheteur")
    adresse_bien: str = Field(description="Adresse complète du bien immobilier")
    nature_bien: Optional[str] = Field(default="Non spécifié", description="Nature du bien (appartement, maison, local commercial, etc.)")
    surface_habitable: Optional[str] = Field(default="Non spécifié", description="Surface habitable en m²")
    prix_vente: str = Field(description="Prix de vente en euros")
    frais_agence: Optional[str] = Field(default="Non spécifié", description="Frais d'agence en euros")
    date_signature: str = Field(description="Date de signature du compromis (JJ/MM/AAAA)")
    date_disponibilite: Optional[str] = Field(default="Non spécifié", description="Date de disponibilité du bien")
    conditions_suspensives: Optional[str] = Field(default="Non spécifié", description="Conditions suspensives principales")

    class Config:
        json_schema_extra = {
            "example": {
                "vendeur": "Marie DURAND",
                "acheteur": "Jean MARTIN",
                "adresse_bien": "15 Avenue des Champs-Élysées, 75008 Paris",
                "nature_bien": "Appartement T3",
                "surface_habitable": "75 m²",
                "prix_vente": "650 000 €",
                "frais_agence": "15 000 €",
                "date_signature": "15/03/2024",
                "date_disponibilite": "01/06/2024",
                "conditions_suspensives": "Obtention prêt bancaire"
            }
        }


class ImpotExtraction(BaseModel):
    """Informations fiscales d'un avis d'imposition"""
    annee_imposition: str = Field(description="Année d'imposition concernée")
    contribuable: str = Field(description="Nom complet du contribuable")
    foyer_fiscal: Optional[str] = Field(default="Non spécifié", description="Composition du foyer fiscal")
    revenu_fiscal_reference: str = Field(description="Revenu fiscal de référence en euros")
    revenu_imposable: Optional[str] = Field(default="Non spécifié", description="Revenu imposable en euros")
    nombre_parts: str = Field(description="Nombre de parts fiscales")
    impot_revenu: str = Field(description="Montant de l'impôt sur le revenu en euros")
    contributions_sociales: Optional[str] = Field(default="Non spécifié", description="Contributions sociales en euros")
    date_mise_en_recouvrement: Optional[str] = Field(default="Non spécifié", description="Date de mise en recouvrement")

    class Config:
        json_schema_extra = {
            "example": {
                "annee_imposition": "2023",
                "contribuable": "Jean DUPONT",
                "foyer_fiscal": "Marié, 2 enfants",
                "revenu_fiscal_reference": "75 000 €",
                "revenu_imposable": "68 000 €",
                "nombre_parts": "3",
                "impot_revenu": "8 500 €",
                "contributions_sociales": "2 500 €",
                "date_mise_en_recouvrement": "01/09/2024"
            }
        }


class CompteBancaireExtraction(BaseModel):
    """Informations d'un relevé bancaire"""
    titulaire: str = Field(description="Nom du titulaire du compte")
    iban: Optional[str] = Field(default="Non spécifié", description="IBAN du compte")
    banque: Optional[str] = Field(default="Non spécifié", description="Nom de la banque")
    periode: str = Field(description="Période concernée (ex: Janvier 2024, 01/01/2024 au 31/01/2024)")
    solde_initial: str = Field(description="Solde au début de période en euros")
    solde_final: str = Field(description="Solde à la fin de période en euros")
    total_credits: str = Field(description="Total des crédits/encaissements en euros")
    total_debits: str = Field(description="Total des débits/décaissements en euros")
    solde_moyen: Optional[str] = Field(default="Non spécifié", description="Solde moyen en euros")

    class Config:
        json_schema_extra = {
            "example": {
                "titulaire": "Jean DUPONT",
                "iban": "FR76 1234 5678 9012 3456 7890 123",
                "banque": "BNP Paribas",
                "periode": "Janvier 2024",
                "solde_initial": "2 500,00 €",
                "solde_final": "2 150,00 €",
                "total_credits": "3 200,00 €",
                "total_debits": "3 550,00 €",
                "solde_moyen": "2 325,00 €"
            }
        }


class JustificatifDomicileExtraction(BaseModel):
    """Extraction d'un justificatif de domicile"""
    nom_titulaire: str = Field(description="Nom complet du titulaire")
    adresse: AdresseExtraction = Field(description="Adresse complète du domicile")
    type_document: str = Field(description="Type de document (facture électricité, eau, internet, quittance loyer, etc.)")
    emetteur: str = Field(description="Émetteur du document (EDF, SFR, propriétaire, etc.)")
    date_document: str = Field(description="Date du document (JJ/MM/AAAA)")
    reference_client: Optional[str] = Field(default="Non spécifié", description="Référence client ou numéro de compte")
    periode_concernee: Optional[str] = Field(default="Non spécifié", description="Période concernée par le document")

    class Config:
        json_schema_extra = {
            "example": {
                "nom_titulaire": "Marie DURAND",
                "adresse": {
                    "numero_voie": "63",
                    "nom_voie": "Rue de Ménilmontant",
                    "code_postal": "75011",
                    "ville": "Paris",
                    "pays": "France"
                },
                "type_document": "Facture d'électricité",
                "emetteur": "EDF",
                "date_document": "15/03/2024",
                "reference_client": "1234567890",
                "periode_concernee": "Février 2024"
            }
        }


class ExtractionGenerale(BaseModel):
    """Modèle générique pour les documents non spécifiques"""
    type_document: str = Field(description="Type de document identifié")
    titre_document: Optional[str] = Field(default="Non spécifié", description="Titre ou objet du document")
    date_document: Optional[str] = Field(default="Non spécifié", description="Date du document si présente")
    emetteur: Optional[str] = Field(default="Non spécifié", description="Organisme ou personne qui a émis le document")
    destinataire: Optional[str] = Field(default="Non spécifié", description="Personne ou entité destinataire")
    informations_principales: str = Field(description='Informations principales extraites sous forme de chaîne JSON. Exemple: \'{"clé1": "valeur1", "clé2": "valeur2"}\'')
    details_supplementaires: str = Field(description='Détails supplémentaires pertinents sous forme de chaîne JSON. Exemple: \'{"cléA": "valeurA", "cléB": "valeurB"}\'')
    resume: Optional[str] = Field(default="Non spécifié", description="Résumé du contenu du document")

    class Config:
        json_schema_extra = {
            "example": {
                "type_document": "Document administratif",
                "titre_document": "Attestation de residence",
                "date_document": "15/03/2024",
                "emetteur": "Mairie du 11ème arrondissement",
                "destinataire": "Jean DUPONT",
                "informations_principales": '{"statut": "Résident depuis 5 ans", "adresse_confirmee": "63 Rue de Ménilmontant"}',
                "details_supplementaires": '{"numéro_attestation": "ATT-2024-01234", "validité": "6 mois"}',
                "resume": "Attestation de résidence confirmant l'adresse de Jean DUPONT"
            }
        }


# Mapping des types de documents vers les modèles Pydantic
EXTRACTION_MODELS = {
    "KBIS société emprunteur": EntrepriseExtraction,
    "KBIS de la société contrôlée": EntrepriseExtraction,
    "Statuts société emprunteur": EntrepriseExtraction,
    "Statuts de la société contrôlée": EntrepriseExtraction,
    "Projet de statuts société emprunteur": EntrepriseExtraction,
    "Compromis de vente": VenteExtraction,
    "Bail ou projet de bail du bien objet de l'acquisition": ExtractionGenerale,
    "Bail": ExtractionGenerale,
    "Justificatif de domicile": JustificatifDomicileExtraction,
    "Avis d'imposition N - 1": ImpotExtraction,
    "Avis d'imposition N - 2": ImpotExtraction,
    "Avis d'imposition N - 3": ImpotExtraction,
    "Bilan et compte de résultat détaillés de l'emprunteur N-1": BilanExtraction,
    "Bilan et compte de résultat détaillés de l'emprunteur N-2": BilanExtraction,
    "Bilan et compte de résultat détaillés de l'emprunteur N-3": BilanExtraction,
    "Bilans et comptes de résultat de la société contrôlée N-1": BilanExtraction,
    "Bilans et comptes de résultat de la société contrôlée N-2": BilanExtraction,
    "Bilans et comptes de résultat de la société contrôlée N-3": BilanExtraction,
    "Relevé de compte Mois M - 1": CompteBancaireExtraction,
    "Relevé de compte Mois M - 2": CompteBancaireExtraction,
    "Relevé de compte Mois M - 3": CompteBancaireExtraction,
    "Relevé de compte de la société contrôlée M - 1": CompteBancaireExtraction,
    "Relevé de compte de la société contrôlée M - 2": CompteBancaireExtraction,
    "Relevé de compte de la société contrôlée M - 3": CompteBancaireExtraction,
    "Dernier relevé d'épargne": ExtractionGenerale,
    "Tableau d'amortissement du crédit immobilier": ExtractionGenerale,
    "Tableau d'amortissement crédit en cours": ExtractionGenerale,
    "CV(s) du(des) associés": PersonneExtraction,
    "Carte d'identité(recto verso) ou Passeport": PersonneExtraction,
    "Livret de famille": ExtractionGenerale,
    "Contrat de mariage": ExtractionGenerale,
    "Dernière taxe foncière": ExtractionGenerale,
    "Attestation notariée d'acquisition indiquant le prix": ExtractionGenerale,
    "Dernière déclaration 2044": ExtractionGenerale,
    "Organigramme des sociétés de la société emprunteur": ExtractionGenerale,
    "Organigramme des sociétés contrôlées": ExtractionGenerale,
    "PV d'AG autorisant la société à emprunter": ExtractionGenerale,
    "Liasses fiscales société emprunteur N-1": ExtractionGenerale,
    "Liasses fiscales société emprunteur N-2": ExtractionGenerale,
    "Liasses fiscales société emprunteur N-3": ExtractionGenerale,
    "Liasses fiscales de la société contrôlée N-1": ExtractionGenerale,
    "Liasses fiscales de la société contrôlée N-2": ExtractionGenerale,
    "Liasses fiscales de la société contrôlée N-3": ExtractionGenerale,
    "Dernière déclaration 2072": ExtractionGenerale,
    "Arrêté du permis de construire": ExtractionGenerale,
    "Autre": ExtractionGenerale,
}


# ===== MODÈLES POUR LA CARTE DE FINANCEMENT =====

class SyntheseProjet(BaseModel):
    """Synthèse du projet à financer"""
    description: str = Field(description="Description complète du projet immobilier ou professionnel")
    objectif_financement: str = Field(description="Objectif principal du financement")
    lieu: Optional[str] = Field(default="Non spécifié", description="Lieu du projet (ville, département)")
    montant_total: Optional[str] = Field(default="Non spécifié", description="Montant total du projet en euros")
    duree: Optional[str] = Field(default="Non spécifié", description="Durée du projet ou du financement")
    garanties: Optional[str] = Field(default="Non spécifié", description="Garanties prévues")

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Acquisition d'un appartement T3 de 75m² dans le 11ème arrondissement de Paris",
                "objectif_financement": "Achat résidence principale",
                "lieu": "Paris 11ème",
                "montant_total": "650 000 €",
                "duree": "20 ans",
                "garanties": "Hypothèque sur le bien"
            }
        }


class ProfilEmprunteur(BaseModel):
    """Profil complet de l'emprunteur"""
    identite: PersonneExtraction = Field(description="Informations d'identité complètes")
    situation_familiale: Optional[str] = Field(default="Non spécifié", description="Situation familiale (marié, pacsé, célibataire, etc.)")
    regime_matrimonial: Optional[str] = Field(default="Non spécifié", description="Régime matrimonial si applicable")
    adresse: Optional[AdresseExtraction] = Field(default=None, description="Adresse personnelle")
    enfants_a_charge: Optional[str] = Field(default="Non spécifié", description="Nombre et âge des enfants à charge")

    class Config:
        json_schema_extra = {
            "example": {
                "identite": {
                    "civilite": "M",
                    "nom": "DUPONT",
                    "prenoms": "Jean Marie",
                    "date_naissance": "15/03/1985",
                    "lieu_naissance": "Paris, France",
                    "nationalite": "Française",
                    "email": "jean.dupont@email.com",
                    "telephone": "+33 6 12 34 56 78",
                    "profession": "Ingénieur informatique"
                },
                "situation_familiale": "Marié",
                "regime_matrimonial": "Communauté de biens",
                "adresse": {
                    "numero_voie": "23",
                    "nom_voie": "Rue de Ménilmontant",
                    "code_postal": "75011",
                    "ville": "Paris",
                    "pays": "France"
                },
                "enfants_a_charge": "2 enfants (8 et 12 ans)"
            }
        }


class RevenusEmprunteur(BaseModel):
    """Détail des revenus de l'emprunteur"""
    revenus_annuels_moyens: str = Field(description="Revenus annuels moyens sur 3 ans en euros")
    dernier_revenu_fiscal: str = Field(description="Dernier revenu fiscal de référence en euros")
    revenus_mensuels: Optional[str] = Field(default="Non spécifié", description="Revenus mensuels nets en euros")
    bonus_primes: Optional[str] = Field(default="Non spécifié", description="Bonus et primes annuels en euros")
    revenus_fonciers: Optional[str] = Field(default="Non spécifié", description="Revenus fonciers annuels en euros")
    autres_revenus: Optional[str] = Field(default="Non spécifié", description="Autres revenus réguliers en euros")

    class Config:
        json_schema_extra = {
            "example": {
                "revenus_annuels_moyens": "85 000 €",
                "dernier_revenu_fiscal": "88 000 €",
                "revenus_mensuels": "5 800 €",
                "bonus_primes": "5 000 €",
                "revenus_fonciers": "12 000 €",
                "autres_revenus": "Non spécifié"
            }
        }


class PatrimoineImmobilier(BaseModel):
    """Détail du patrimoine immobilier"""
    biens_immobiliers: str = Field(description="Liste des biens immobiliers possédés")
    valeur_estimee_totale: str = Field(description="Valeur estimée totale du patrimoine immobilier en euros")
    credits_restants_dus: str = Field(description="Total des crédits restants dus en euros")
    loyers_percus_annuels: Optional[str] = Field(default="Non spécifié", description="Loyers perçus annuellement en euros")
    patrimoine_net_immobilier: str = Field(description="Patrimoine net immobilier en euros")

    class Config:
        json_schema_extra = {
            "example": {
                "biens_immobiliers": "Appartement T3 Paris 11ème (75m²) - estimation 420 000 €",
                "valeur_estimee_totale": "420 000 €",
                "credits_restants_dus": "85 000 €",
                "loyers_percus_annuels": "Non spécifié",
                "patrimoine_net_immobilier": "335 000 €"
            }
        }


class PatrimoineMobilier(BaseModel):
    """Patrimoine mobilier et financier"""
    comptes_bancaires: str = Field(description="Solde total des comptes bancaires en euros")
    epargne_financiere: str = Field(description="Montant total de l'épargne financière en euros")
    assurance_vie: Optional[str] = Field(default="Non spécifié", description="Montant assurance vie en euros")
    autres_investissements: Optional[str] = Field(default="Non spécifié", description="Autres investissements financiers en euros")
    patrimoine_mobilier_total: str = Field(description="Total patrimoine mobilier en euros")

    class Config:
        json_schema_extra = {
            "example": {
                "comptes_bancaires": "25 000 €",
                "epargne_financiere": "85 000 €",
                "assurance_vie": "45 000 €",
                "autres_investissements": "15 000 €",
                "patrimoine_mobilier_total": "170 000 €"
            }
        }


class SocieteInformation(BaseModel):
    """Informations sur une société détenue par l'emprunteur"""
    raison_sociale: str = Field(description="Nom de la société")
    forme_juridique: str = Field(description="Forme juridique (SAS, SARL, etc.)")
    pourcentage_detention: str = Field(description="Pourcentage de détention")
    chiffre_affaires_n1: str = Field(description="Chiffre d'affaires N-1 en euros")
    resultat_net_n1: str = Field(description="Résultat net N-1 en euros")
    dettes_totales: str = Field(description="Dettes totales en euros")
    fonds_propres: str = Field(description="Fonds propres en euros")
    activite: str = Field(description="Description de l'activité principale")

    class Config:
        json_schema_extra = {
            "example": {
                "raison_sociale": "ALPHA CONSEIL SAS",
                "forme_juridique": "SAS",
                "pourcentage_detention": "80%",
                "chiffre_affaires_n1": "450 000 €",
                "resultat_net_n1": "65 000 €",
                "dettes_totales": "125 000 €",
                "fonds_propres": "210 000 €",
                "activite": "Conseil en informatique et transformation digitale"
            }
        }


class PlanFinancement(BaseModel):
    """Plan de financement détaillé du projet"""
    apport_personnel: str = Field(description="Montant de l'apport personnel en euros")
    pret_sollicite: str = Field(description="Montant du prêt sollicité en euros")
    duration_pret: str = Field(description="Durée du prêt souhaitée")
    taux_estime: Optional[str] = Field(default="Non spécifié", description="Taux d'intérêt estimé")
    mensualite_estimee: Optional[str] = Field(default="Non spécifié", description="Mensualité estimée en euros")
    garanties_prevues: str = Field(description="Garanties prévues pour le financement")
    autres_financements: Optional[str] = Field(default="Non spécifié", description="Autres sources de financement")

    class Config:
        json_schema_extra = {
            "example": {
                "apport_personnel": "130 000 €",
                "pret_sollicite": "520 000 €",
                "duration_pret": "20 ans",
                "taux_estime": "4.2%",
                "mensualite_estimee": "3 200 €",
                "garanties_prevues": "Hypothèque première rang sur le bien",
                "autres_financements": "Non spécifié"
            }
        }


class AnalyseFinanciere(BaseModel):
    """Analyse financière globale et points de vigilance"""
    capacite_emprunt: str = Field(description="Capacité d'emprunt mensuelle estimée en euros")
    ratio_endettement: str = Field(description="Ratio d'endettement actuel en pourcentage")
    patrimoine_net_total: str = Field(description="Patrimoine net total en euros")
    ratio_patrimoine_emprunt: Optional[str] = Field(default="Non spécifié", description="Ratio patrimoine/emprunt")
    points_forts: str = Field(description="Principaux points forts du dossier")
    points_vigilance: str = Field(description="Points de vigilance identifiés")
    recommandation: str = Field(description="Recommandation finale sur le financement")

    class Config:
        json_schema_extra = {
            "example": {
                "capacite_emprunt": "3 500 €",
                "ratio_endettement": "28%",
                "patrimoine_net_total": "505 000 €",
                "ratio_patrimoine_emprunt": "103%",
                "points_forts": "Bon patrimoine, revenus stables, apport conséquent (20%)",
                "points_vigilance": "Endettement proche de 33% après financement",
                "recommandation": "Projet viable avec bonne capacité de remboursement"
            }
        }


class CarteFinancement(BaseModel):
    """Modèle complet pour la Carte de Financement"""
    synthese_projet: SyntheseProjet = Field(description="Synthèse complète du projet")
    profil_emprunteur: ProfilEmprunteur = Field(description="Profil détaillé de l'emprunteur")
    revenus: RevenusEmprunteur = Field(description="Détail des revenus")
    patrimoine_immobilier: PatrimoineImmobilier = Field(description="Patrimoine immobilier")
    patrimoine_mobilier: PatrimoineMobilier = Field(description="Patrimoine mobilier et financier")
    societes: list[SocieteInformation] = Field(description="Sociétés détenues par l'emprunteur")
    plan_financement: PlanFinancement = Field(description="Plan de financement détaillé")
    analyse_financiere: AnalyseFinanciere = Field(description="Analyse financière globale")

    # Informations de traçabilité
    dossier_id: str = Field(description="Identifiant unique du dossier")
    date_generation: str = Field(description="Date de génération de la synthèse")
    documents_sources: str = Field(description="Liste des documents utilisés pour la génération")

    class Config:
        json_schema_extra = {
            "example": {
                "synthese_projet": {
                    "description": "Acquisition appartement T3 Paris 11ème",
                    "objectif_financement": "Résidence principale",
                    "lieu": "Paris 11ème",
                    "montant_total": "650 000 €",
                    "duree": "20 ans",
                    "garanties": "Hypothèque sur le bien"
                },
                "dossier_id": "DOSS-2024-001",
                "date_generation": "29/10/2025",
                "documents_sources": "KBIS, Bilans N-1, Avis imposition N-1, Relevés bancaires"
            }
        }


# Export du modèle principal pour la synthèse
CARTE_FINANCEMENT_MODEL = CarteFinancement