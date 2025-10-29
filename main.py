"""
Application de détection et classification de documents avec OCR + LLM
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from datetime import datetime

from database import init_database, insert_document, get_documents
from services.document_processor import DocumentProcessor
from services.llm_classifier import LLMClassifier
from config import config

# Variables globales pour les services
document_processor = None
llm_classifier = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Démarrage
    print("Démarrage de l'application...")
    global document_processor, llm_classifier

    # Initialiser la base de données
    init_database()

    # Initialiser les services
    document_processor = DocumentProcessor()
    llm_classifier = LLMClassifier()

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
    Endpoint pour téléverser et classifier un document
    """
    if document_processor is None or llm_classifier is None:
        raise HTTPException(status_code=503, detail="Services non initialisés")

    try:
        # Vérifier le type de fichier
        if not file.filename.lower().endswith(tuple(config.SUPPORTED_EXTENSIONS)):
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non supporté. Extensions supportées: {', '.join(config.SUPPORTED_EXTENSIONS)}"
            )

        # Vérifier la taille du fichier
        if file.size and file.size > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux. Taille maximale: {config.MAX_FILE_SIZE // (1024*1024)}MB"
            )

        # Sauvegarder le fichier
        file_path = os.path.join(config.UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extraire le texte du document
        extracted_text = await document_processor.extract_text(file_path)

        if not extracted_text.strip():
            os.remove(file_path)  # Nettoyer le fichier
            raise HTTPException(status_code=400, detail="Impossible d'extraire le texte du document")

        # Pipeline complet de traitement : classification + extraction
        processing_result = await llm_classifier.process_document_complete(extracted_text)

        # Sauvegarder en base de données
        # Adapter le format pour la base de données (compatibilité ascendante)
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
        extraction_data = processing_result.get("extraction")
        if extraction_data and extraction_data.get("success"):
            try:
                from database import insert_document_extraction
                insert_document_extraction(
                    document_id=document_id,
                    extracted_data=extraction_data.get("extracted_data"),
                    llm_used=extraction_data.get("llm_used", "mistral-large-latest"),
                    confidence=extraction_data.get("confidence", 0.0)
                )
            except Exception as e:
                print(f"Erreur lors de la sauvegarde de l'extraction: {e}")
                # Ne pas échouer le traitement si l'extraction ne sauvegarde pas

        # Supprimer le fichier après traitement si configuré
        message = "Document traité avec succès"
        if config.DELETE_AFTER_PROCESSING:
            try:
                os.remove(file_path)
                message += " (fichier supprimé automatiquement)"
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier {file_path}: {e}")

        return JSONResponse(content={
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "processing_result": processing_result,
            "message": message
        })

    except HTTPException as he:
        raise he
    except Exception as e:
        # Nettoyer le fichier en cas d'erreur
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

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
