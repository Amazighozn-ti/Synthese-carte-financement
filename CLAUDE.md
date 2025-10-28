# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**synthese-carte-financement** is a FastAPI-based document classification system that automatically detects and classifies administrative and financial documents using OCR (Optical Character Recognition) and Mistral LLM (Large Language Model).

### Core Purpose
The application analyzes uploaded documents (PDFs or images), extracts their text content, and automatically identifies the document type among 40 predefined administrative and financial document types. It's designed specifically for French financing and administrative document processing.

## Architecture & Technology Stack

### Framework
- **FastAPI**: Modern Python web framework for building APIs
- **Uvicorn**: ASGI server for FastAPI applications
- **Python 3.12**: Core runtime requirement

### External Services
- **Mistral AI**:
  - OCR service for image-based text extraction
  - LLM service for document classification
  - Uses `mistral-ocr-latest` and `mistral-large-latest` models

### Document Processing
- **PDF Support**:
  - Text extraction from regular PDFs using pdfminer-six and PyPDF2
  - OCR processing for scanned PDFs using pdf2image conversion
- **Image Support**: PNG, JPG, JPEG, TIFF, BMP formats
- **OCR Processing**: Base64 encoding with Mistral OCR API

### Data Storage
- **SQLite**: Local database for storing documents and metadata
- **Document Types Predefined**: 40 types of documents across 8 categories

## Project Structure

```
synthese-carte-financement/
├── main.py              # FastAPI application entry point (194 lines)
├── config.py            # Application configuration (47 lines)
├── database.py          # Database operations and models (252 lines)
├── services/            # Core business logic
│   ├── __init__.py      # Service package initialization (2 lines)
│   ├── document_processor.py  # Document text extraction (275 lines)
│   └── llm_classifier.py       # LLM-based classification (456 lines)
├── uploads/             # Uploaded file storage directory
├── documents.db         # SQLite database file
├── .env                # Environment variables
├── .gitignore          # Git ignore rules
├── .python-version     # Python version specification (3.12)
├── pyproject.toml      # Project dependencies and metadata
├── uv.lock             # Dependency lock file
├── README.md           # Detailed project documentation
└── CLAUDE.md           # This file
```

## Configuration & Environment

### Environment Variables (.env)
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Mistral API Configuration (Required)
MISTRAL_API_KEY=your_api_key_here
MISTRAL_MODEL=mistral-large-latest

# Database Configuration
DATABASE_URL=sqlite:///documents.db

# Upload Configuration
UPLOAD_DIR=uploads
MAX_FILE_SIZE=50  # MB
```

### Key Dependencies (pyproject.toml)
- **FastAPI**: Web framework
- **MistralAI**: API client for OCR and LLM services
- **PDF2Image**: PDF to image conversion for OCR
- **pdfminer-six**: PDF text extraction
- **Pillow**: Image processing
- **PyPDF2**: PDF manipulation
- **python-dotenv**: Environment variable management
- **python-multipart**: File upload support
- **uvicorn**: ASGI server

## API Endpoints

### Core Functionality
- **POST `/upload`**: Upload and classify a document
- **GET `/documents`**: List all processed documents
- **GET `/documents/{id}`**: Get specific document details
- **DELETE `/documents/{id}`**: Delete a document
- **GET `/document-types`**: List supported document types
- **GET `/stats`**: Get processing statistics
- **GET `/health`**: Health check endpoint

### File Support
- **Formats**: PDF, PNG, JPG, JPEG, TIFF, BMP
- **Size Limit**: 50MB (configurable)
- **Text Extraction**: Direct PDF text + OCR for scanned content

## Database Schema

### `documents` Table
- `id`: INTEGER (Primary Key, Auto-increment)
- `filename`: TEXT (Original filename)
- `file_path`: TEXT (File storage path)
- `extracted_text`: TEXT (Extracted text content)
- `detected_type`: TEXT (Classified document type)
- `detected_category`: TEXT (Document category)
- `confidence`: REAL (Classification confidence score 0-1)
- `created_at`: DATETIME (Timestamp)

### `document_types` Table
- `id`: INTEGER (Primary Key)
- `name`: TEXT (Document type name)
- `category`: TEXT (Document category)

## Supported Document Categories & Types

### 1. Company (Entreprise)
- KBIS société emprunteur
- Statuts société emprunteur
- Bilans, Liasses fiscales
- Organigramme, PV d'AG

### 2. Object (Objet)
- Compromis de vente
- Bail ou projet de bail

### 3. Associates (Associés)
- CV(s) des associés
- Pièce d'identité
- Avis d'imposition

### 4. Financing (Financement)
- Tableau de remboursement
- Offre de prêt
- Plan de financement

### 5. Diagnostics (Diagnostics)
- DPE, Amiante, Plomb, Termites, Gaz, Électricité

### 6. Works (Travaux)
- Devis, Factures, Attestation de fin travaux

### 7. Sale (Vente)
- Acte de vente, Extrait cadastral

### 8. Location (Location)
- États des lieux, Inventaire

## Development Workflow

### 1. Setup Environment
```bash
# Clone repository
git clone <repository-url>
cd synthese-carte-financement

# Install dependencies with uv
uv sync

# Configure environment
cp .env.example .env  # If available, or create .env
# Add MISTRAL_API_KEY

# Start development server
uv run python main.py
```

### 2. Testing
Currently no automated test suite exists. Manual testing via API endpoints is recommended.

### 3. Running in Production
```bash
# Production server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Or with debug mode
uv run python main.py --reload
```

## Performance Characteristics

### Processing Times
- **Textual PDF**: < 2 seconds
- **Scanned PDF (OCR)**: 5-15 seconds (depending on pages)
- **Image (OCR)**: 3-8 seconds (depending on size)
- **LLM Classification**: 1-3 seconds

### File Limits
- **Max File Size**: 50MB (configurable)
- **Supported Formats**: PDF, PNG, JPG, JPEG, TIFF, BMP

## Development Patterns & Conventions

### Code Structure
- **Service Layer**: Business logic separated into services/
- **Configuration**: Centralized in config.py with environment variables
- **Database**: SQLite with connection management
- **Error Handling**: Comprehensive try/catch with logging

### Naming Conventions
- **Classes**: PascalCase (e.g., `DocumentProcessor`)
- **Methods**: snake_case (e.g., `extract_text`)
- **Variables**: snake_case (e.g., `api_key`)
- **Constants**: UPPER_CASE (e.g., `MAX_FILE_SIZE`)

### Error Handling
- **HTTP Exceptions**: FastAPI HTTPException for API errors
- **Database Errors**: SQLite error handling with rollback
- **LLM Errors**: Fallback classification with keyword matching
- **File Errors**: Proper cleanup on failed uploads

## Security Considerations

### API Key Management
- **Environment Variables**: MISTRAL_API_KEY required
- **Input Validation**: File type and size restrictions
- **File Cleanup**: Automatic cleanup on failed processing

### Data Privacy
- **Local Storage**: SQLite database for document metadata
- **File Storage**: Local filesystem for uploaded documents
- **No External Dependencies**: Self-contained application

## Common Issues & Troubleshooting

### 1. API Key Errors
- **Issue**: MISTRAL_API_KEY missing or invalid
- **Solution**: Check .env file and API key validity

### 2. OCR Processing Failures
- **Issue**: Mistral OCR not working
- **Solution**: Ensure internet connection and valid API key
- **Fallback**: System tries alternative extraction methods

### 3. JSON Parsing Errors
- **Issue**: LLM response parsing fails
- **Solution**: Extensive error handling and fallback mechanisms
- **Logging**: Detailed logging for debugging

### 4. File Size Issues
- **Issue**: Files exceed 50MB limit
- **Solution**: Check MAX_FILE_SIZE configuration

## Extension Points & Customization

### Adding New Document Types
1. Update `database.py` with new document types
2. Update `llm_classifier.py` classifications
3. Add to fallback keyword mapping

### Custom Processing
- **DocumentProcessor**: Override text extraction methods
- **LLMClassifier**: Modify prompt engineering and classification logic
- **Database**: Switch to PostgreSQL for production

### Deployment Options
- **Docker**: Basic Dockerfile support mentioned in README
- **Cloud**: Can be deployed on cloud services with API key configuration
- **Scaling**: Horizontal scaling possible with stateless design

## Recent Development Updates

Based on git commit history:
- **JSON Prompt Optimization**: Improved LLM prompts for concise, valid JSON responses
- **Enhanced Logging**: Added detailed logging for JSON parsing debugging
- **Initial Implementation**: First version initialization

## Contributing Guidelines

1. **Code Style**: Follow existing Python conventions
2. **Testing**: Add tests for new functionality
3. **Documentation**: Update README.md for new features
4. **Environment**: Test changes in development environment
5. **API Key**: Never commit API keys to version control

## License

License to be defined - currently no license specified in project files.