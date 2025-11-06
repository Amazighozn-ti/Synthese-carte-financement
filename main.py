"""
Application de détection et classification de documents avec OCR + LLM
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
import os
import shutil
from datetime import datetime
from typing import List, Optional

from database import init_database, insert_document, get_documents
from services.document_processor import DocumentProcessor
from services.llm_classifier import LLMClassifier
from services.synthesis_generator import SynthesisGenerator
from config import config

# Variables globales pour les services
document_processor = None
llm_classifier = None
synthesis_generator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Démarrage
    print("Démarrage de l'application...")
    global document_processor, llm_classifier, synthesis_generator

    # Initialiser la base de données
    init_database()

    # Initialiser les services
    print("Initialisation des services...")
    try:
        document_processor = DocumentProcessor()
        print("✅ DocumentProcessor initialisé")

        llm_classifier = LLMClassifier()
        print("✅ LLMClassifier initialisé")

        synthesis_generator = SynthesisGenerator()
        print("✅ SynthesisGenerator initialisé")

    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation des services: {e}")
        raise

    print("Application démarrée avec succès")

    yield

    # Arrêt
    print("Arrêt de l'application...")

app = FastAPI(
    title="Document Classification API",
    version="1.0.0",
    description="API de classification de documents avec OCR + LLM",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Endpoint racine"""
    return {"message": "Document Classification API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Vérification de santé de l'API"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint pour téléverser et classifier un document (compatibilité ascendante)
    """
    files = [file]
    return await process_multiple_files(files, custom_synthesis_prompt=None)

@app.post("/upload-multiple")
async def upload_multiple_documents(
    files: List[UploadFile] = File(...),
    generate_synthesis: bool = Query(False),
    custom_synthesis_prompt: Optional[str] = Query(None, description="Instructions personnalisées pour enrichir la génération de synthèse")
):
    """
    Endpoint pour téléverser, classifier, extraire et générer une synthèse de financement

    Args:
        files: Liste des fichiers à traiter
        generate_synthesis: Si True, génère une Carte de Financement après traitement
        custom_synthesis_prompt: Instructions personnalisées qui seront intégrées dans tous les prompts de génération des sections
    """
    if len(files) > 50:  # Limite raisonnable pour éviter la surcharge
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 fichiers autorisés par requête"
        )

    return await process_multiple_files(files, generate_synthesis, custom_synthesis_prompt)

async def process_multiple_files(files: List[UploadFile], generate_synthesis: bool = False, custom_synthesis_prompt: Optional[str] = None):
    """
    Traiter plusieurs fichiers (upload simple ou multiple) avec génération de synthèse optionnelle

    Args:
        files: Liste des fichiers à traiter
        generate_synthesis: Si True, génère une Carte de Financement après traitement
        custom_synthesis_prompt: Instructions personnalisées pour enrichir la génération de synthèse
    """
    global document_processor, llm_classifier, synthesis_generator

    print(f"DEBUG: Services status - document_processor: {document_processor is not None}, "
          f"llm_classifier: {llm_classifier is not None}, synthesis_generator: {synthesis_generator is not None}")

    if document_processor is None or llm_classifier is None or synthesis_generator is None:
        raise HTTPException(status_code=503, detail="Services non initialisés")

    results = []
    total_start_time = datetime.now()

    # Traitement parallèle des fichiers
    import asyncio

    async def process_single_file(file: UploadFile):
        try:
            # Vérifier le type de fichier
            if not file.filename.lower().endswith(tuple(config.SUPPORTED_EXTENSIONS)):
                return {
                    "success": False,
                    "filename": file.filename,
                    "error": f"Type de fichier non supporté. Extensions supportées: {', '.join(config.SUPPORTED_EXTENSIONS)}"
                }

            # Vérifier la taille du fichier
            if file.size and file.size > config.MAX_FILE_SIZE:
                return {
                    "success": False,
                    "filename": file.filename,
                    "error": f"Fichier trop volumineux. Taille maximale: {config.MAX_FILE_SIZE // (1024*1024)}MB"
                }

            # Sauvegarder le fichier avec un nom unique pour éviter les conflits
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{timestamp}_{file.filename}"
            file_path = os.path.join(config.UPLOAD_DIR, filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Extraire le texte du document
            extracted_text = await document_processor.extract_text(file_path)

            if not extracted_text.strip():
                os.remove(file_path)  # Nettoyer le fichier
                return {
                    "success": False,
                    "filename": file.filename,
                    "error": "Impossible d'extraire le texte du document"
                }

            # Pipeline complet de traitement : classification + extraction
            processing_result = await llm_classifier.process_document_complete(extracted_text)

            # Sauvegarder en base de données
            classification_data = processing_result.get("classification", {}).get("classification", {})
            document_id = insert_document(
                filename=file.filename,
                file_path=file_path,
                extracted_text=extracted_text,
                detected_type=classification_data.get("document_type"),
                detected_category=classification_data.get("category"),
                confidence=classification_data.get("confidence")
            )

            # Sauvegarder les résultats d'extraction si disponibles
            extraction_id = None
            extraction_data = processing_result.get("extraction")
            if extraction_data and extraction_data.get("success"):
                try:
                    from database import insert_document_extraction
                    extraction_id = insert_document_extraction(
                        document_id=document_id,
                        extracted_data=extraction_data.get("extracted_data"),
                        llm_used=extraction_data.get("llm_used", "magistral-medium-latest"),
                        confidence=extraction_data.get("confidence", 0.0)
                    )
                except Exception as e:
                    print(f"Erreur lors de la sauvegarde de l'extraction: {e}")

            # Supprimer le fichier après traitement si configuré
            if config.DELETE_AFTER_PROCESSING:
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Erreur lors de la suppression du fichier {file_path}: {e}")

            return {
                "success": True,
                "document_id": document_id,
                "extraction_id": extraction_id,
                "filename": file.filename,
                "processing_result": processing_result,
                "message": "Document traité avec succès"
            }

        except Exception as e:
            # Nettoyer le fichier en cas d'erreur
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            return {
                "success": False,
                "filename": file.filename,
                "error": str(e)
            }

    # Traiter tous les fichiers en parallèle (avec limite pour éviter la surcharge)
    semaphore = asyncio.Semaphore(5)  # Maximum 5 traitements simultanés

    async def process_with_semaphore(file):
        async with semaphore:
            return await process_single_file(file)

    # Lancer tous les traitements en parallèle
    tasks = [process_with_semaphore(file) for file in files]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Nettoyer les exceptions et formater les résultats
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "success": False,
                "filename": files[i].filename,
                "error": f"Erreur de traitement: {str(result)}"
            })
        else:
            processed_results.append(result)

    # Calculer les statistiques
    successful_count = sum(1 for r in processed_results if r.get("success", False))
    total_processing_time = (datetime.now() - total_start_time).total_seconds()

    response_content = {
        "success": True,
        "total_files": len(files),
        "successful_count": successful_count,
        "failed_count": len(files) - successful_count,
        "total_processing_time": round(total_processing_time, 2),
        "results": processed_results,
        "message": f"Traitement terminé: {successful_count}/{len(files)} fichiers traités avec succès"
    }

    # Générer la synthèse complète (JSON + Word) si demandée et si des documents ont été traités avec succès
    if generate_synthesis and successful_count > 0:
        try:
            # Récupérer les IDs des documents traités avec succès
            successful_document_ids = [
                result["document_id"] for result in processed_results
                if result.get("success") and "document_id" in result
            ]

            if successful_document_ids:
                print(f"Génération de la synthèse complète pour {len(successful_document_ids)} documents...")

                try:
                    # Générer la synthèse complète via le service (JSON + Word)
                    complete_result = await synthesis_generator.generate_complete_synthesis(successful_document_ids, custom_synthesis_prompt)

                    if complete_result["success"]:
                        response_content["synthesis"] = complete_result["synthese"]
                        response_content["word_document"] = complete_result["word_document"]
                        response_content["message"] += " - Carte de Financement complète générée avec succès"
                        print("✅ Synthèse générée avec succès")
                    else:
                        error_msg = complete_result.get("error", "Erreur inconnue")
                        print(f"❌ Erreur lors de la génération de la synthèse: {error_msg}")
                        response_content["synthesis"] = {
                            "success": False,
                            "error": error_msg
                        }
                        response_content["message"] += " - Erreur lors de la génération de la Carte de Financement"
                except Exception as e:
                    error_msg = f"Exception lors de la génération: {str(e)}"
                    import traceback
                    traceback.print_exc()
                    print(f"❌ {error_msg}")
                    response_content["synthesis"] = {
                        "success": False,
                        "error": error_msg
                    }
                    response_content["message"] += " - Erreur lors de la génération de la Carte de Financement"
            else:
                response_content["synthesis"] = {
                    "success": False,
                    "error": "Aucun document valide pour la génération de synthèse"
                }

        except Exception as e:
            response_content["synthesis"] = {
                "success": False,
                "error": f"Erreur lors de la génération de la synthèse: {str(e)}"
            }

    return JSONResponse(content=response_content)

@app.get("/documents")
async def list_documents():
    """Lister tous les documents traités"""
    documents = get_documents()
    return {"documents": documents}

@app.get("/documents/{document_id}")
async def get_document(document_id: int):
    """Récupérer un document spécifique par son ID avec ses extractions"""
    documents = get_documents(document_id)
    if not documents:
        raise HTTPException(status_code=404, detail="Document non trouvé")

    # Récupérer les extractions associées
    from database import get_document_extractions
    extractions = get_document_extractions(document_id)

    return {
        "document": documents[0],
        "extractions": extractions
    }

@app.delete("/documents/{document_id}")
async def delete_document(document_id: int):
    """Supprimer un document par son ID"""
    from database import delete_document as db_delete_document

    success = db_delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document non trouvé")

    return {"success": True, "message": "Document supprimé avec succès"}

@app.get("/document-types")
async def get_document_types():
    """Lister tous les types de documents supportés"""
    from database import get_document_types as db_get_document_types

    return {"document_types": db_get_document_types()}

@app.get("/extraction-prompts")
async def get_extraction_prompts():
    """Lister tous les prompts d'extraction disponibles"""
    from database import get_extraction_prompts

    return {"extraction_prompts": get_extraction_prompts()}

@app.get("/extractions")
async def get_extractions(document_id: int = None):
    """Récupérer les extractions de documents"""
    from database import get_document_extractions

    extractions = get_document_extractions(document_id)
    return {"extractions": extractions}

@app.get("/syntheses")
async def get_syntheses(dossier_id: str = None):
    """Récupérer les synthèses de financement"""
    from database import get_syntheses

    syntheses = get_syntheses(dossier_id)
    return {"syntheses": syntheses}

@app.get("/syntheses/{dossier_id}")
async def get_synthesis_details(dossier_id: str):
    """Récupérer les détails d'une synthèse spécifique"""
    from database import get_syntheses

    syntheses = get_syntheses(dossier_id)
    if not syntheses:
        raise HTTPException(status_code=404, detail="Synthèse non trouvée")

    return {"synthesis": syntheses[0]}

@app.get("/documents-generes")
async def list_documents_generes(dossier_id: str = None):
    """Lister tous les documents générés"""
    from database import get_documents_generes

    documents_generes = get_documents_generes(dossier_id)
    return {"documents_generes": documents_generes}

@app.get("/documents-generes/{document_id}")
async def get_document_genere(document_id: int):
    """Récupérer un document généré spécifique par son ID"""
    from database import get_document_genere

    document = get_document_genere(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document généré non trouvé")

    return {"document_genere": document}

@app.get("/documents-generes/{document_id}/download")
async def download_document_genere(document_id: int):
    """Télécharger un document généré"""
    from database import get_document_genere

    document = get_document_genere(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document généré non trouvé")

    file_path = document["file_path"]
    file_name = document["file_name"]

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé sur le serveur")

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@app.delete("/documents-generes/{document_id}")
async def delete_document_genere(document_id: int):
    """Supprimer un document généré par son ID"""
    from database import delete_document_genere as db_delete_document_genere

    success = db_delete_document_genere(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document généré non trouvé")

    return {"success": True, "message": "Document généré supprimé avec succès"}

@app.post("/generate-synthesis")
async def generate_synthesis_endpoint(
    document_ids: List[int] = Query(..., description="Liste des IDs de documents à analyser")
):
    """Endpoint pour générer une Carte de Financement à partir de documents existants"""
    global synthesis_generator

    if synthesis_generator is None:
        raise HTTPException(status_code=503, detail="Service de synthèse non initialisé")

    try:
        result = await synthesis_generator.generate_complete_synthesis(document_ids)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Statistiques sur les documents traités"""
    documents = get_documents()

    if not documents:
        return {
            "total_documents": 0,
            "categories": {},
            "recent_documents": []
        }

    # Compter par catégorie
    categories = {}
    for doc in documents:
        category = doc.get('detected_category', 'Non catégorisé')
        categories[category] = categories.get(category, 0) + 1

    # Documents récents (5 derniers)
    recent_documents = [
        {
            "id": doc["id"],
            "filename": doc["filename"],
            "type": doc["detected_type"],
            "category": doc["detected_category"],
            "confidence": doc["confidence"],
            "created_at": doc["created_at"]
        }
        for doc in documents[:5]
    ]

    return {
        "total_documents": len(documents),
        "categories": categories,
        "recent_documents": recent_documents
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT, reload=config.DEBUG)
