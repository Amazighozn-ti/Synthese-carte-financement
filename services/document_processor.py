"""
Service de traitement et d'extraction de texte des documents
"""

import os
import io
import base64
import json
from typing import Optional
from pdf2image import convert_from_path
from PIL import Image
import PyPDF2
from pdfminer.high_level import extract_text as pdfminer_extract_text
from pdfminer.pdfparser import PDFSyntaxError
from pathlib import Path
from mistralai import Mistral, ImageURLChunk
from config import config

class DocumentProcessor:
    """Classe pour traiter différents types de documents et extraire le texte"""

    def __init__(self):
        """Initialiser le client Mistral OCR"""
        self.api_key = config.MISTRAL_API_KEY
        self.client = Mistral(api_key=self.api_key) if self.api_key else None
        self.ocr_model = "mistral-ocr-latest"

        if not self.client:
            raise ValueError("MISTRAL_API_KEY est obligatoire. Veuillez configurer votre clé API Mistral.")

    async def extract_text(self, file_path: str) -> str:
        """
        Extraire le texte d'un document en fonction de son type

        Args:
            file_path: Chemin vers le fichier

        Returns:
            str: Texte extrait du document
        """
        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension == '.pdf':
                return await self._extract_from_pdf(file_path)
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                return await self._extract_from_image(file_path)
            else:
                raise ValueError(f"Type de fichier non supporté: {file_extension}")
        except Exception as e:
            raise Exception(f"Erreur lors de l'extraction du texte: {str(e)}")

    async def _extract_from_pdf(self, file_path: str) -> str:
        """
        Extraire le texte d'un fichier PDF

        Essaie d'abord l'extraction directe, puis OCR si nécessaire
        """
        try:
            # Essayer d'abord l'extraction de texte directe
            text = self._extract_pdf_text_direct(file_path)

            # Si le texte extrait est trop court, essayer OCR
            if len(text.strip()) < 50:
                print("Texte direct trop court, tentative avec OCR...")
                text = await self._extract_pdf_ocr(file_path)

            return text

        except Exception as e:
            print(f"Erreur extraction PDF directe, tentative avec OCR: {e}")
            return await self._extract_pdf_ocr(file_path)

    def _extract_pdf_text_direct(self, file_path: str) -> str:
        """
        Extraire le texte directement d'un PDF (PDF avec du texte extractible)
        """
        try:
            # Essayer avec pdfminer d'abord (plus robuste)
            text = pdfminer_extract_text(file_path)

            if text.strip():
                return text

        except (PDFSyntaxError, Exception) as e:
            print(f"Erreur avec pdfminer: {e}")

        try:
            # Essayer avec PyPDF2 en backup
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""

                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"

                return text

        except Exception as e:
            print(f"Erreur avec PyPDF2: {e}")
            raise Exception("Impossible d'extraire le texte du PDF")

    async def _extract_pdf_ocr(self, file_path: str) -> str:
        """
        Extraire le texte d'un PDF scanné en utilisant Mistral OCR
        """
        try:
            # Convertir le PDF en images
            images = convert_from_path(file_path, dpi=200, fmt='jpeg')

            text = ""
            for i, image in enumerate(images):
                # Extraire le texte de chaque page avec Mistral OCR
                page_text = await self._extract_with_mistral_ocr(image)
                text += f"--- Page {i+1} ---\n{page_text}\n"

            return text

        except Exception as e:
            raise Exception(f"Erreur lors de l'OCR sur PDF: {str(e)}")

    async def _extract_from_image(self, file_path: str) -> str:
        """
        Extraire le texte d'une image en utilisant Mistral OCR
        """
        try:
            # Ouvrir l'image avec PIL
            image = Image.open(file_path)

            # Convertir en RGB si nécessaire (pour les images en niveaux de gris ou RGBA)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Extraire le texte avec Mistral OCR
            text = await self._extract_with_mistral_ocr(image)
            return text

        except Exception as e:
            raise Exception(f"Erreur lors de l'OCR sur image: {str(e)}")

    async def _extract_with_mistral_ocr(self, image: Image.Image) -> str:
        """
        Extraire le texte d'une image en utilisant Mistral OCR
        """
        try:
            # Convertir l'image en base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            base64_data_url = f"data:image/jpeg;base64,{img_str}"

            # Traiter l'image avec Mistral OCR
            image_response = self.client.ocr.process(
                document=ImageURLChunk(image_url=base64_data_url),
                model=self.ocr_model
            )

            # Extraire le texte de la réponse
            if hasattr(image_response, 'pages') and image_response.pages:
                text = ""
                for page in image_response.pages:
                    if hasattr(page, 'markdown'):
                        text += page.markdown + "\n"
                    elif hasattr(page, 'text'):
                        text += page.text + "\n"
                return text
            else:
                # Parser la réponse JSON si structure différente
                response_dict = json.loads(image_response.model_dump_json())
                if 'pages' in response_dict:
                    text = ""
                    for page in response_dict['pages']:
                        if 'markdown' in page:
                            text += page['markdown'] + "\n"
                        elif 'text' in page:
                            text += page['text'] + "\n"
                    return text

            return ""

        except Exception as e:
            print(f"Erreur avec Mistral OCR: {e}")
            # Retourner chaîne vide si Mistral OCR échoue
            return ""

    def is_pdf_scanned(self, file_path: str) -> bool:
        """
        Vérifier si un PDF est scanné (ne contient pas de texte extractible)

        Args:
            file_path: Chemin vers le fichier PDF

        Returns:
            bool: True si le PDF est scanné
        """
        try:
            # Essayer d'extraire du texte
            text = self._extract_pdf_text_direct(file_path)

            # Si très peu de texte, considérer comme scanné
            return len(text.strip()) < 50

        except Exception:
            # Si erreur lors de l'extraction, considérer comme scanné
            return True

    def get_file_info(self, file_path: str) -> dict:
        """
        Obtenir des informations sur le fichier

        Args:
            file_path: Chemin vers le fichier

        Returns:
            dict: Informations sur le fichier
        """
        try:
            stat = os.stat(file_path)
            file_extension = os.path.splitext(file_path)[1].lower()

            info = {
                'filename': os.path.basename(file_path),
                'file_path': file_path,
                'file_size': stat.st_size,
                'file_extension': file_extension,
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime,
            }

            # Informations spécifiques aux PDFs
            if file_extension == '.pdf':
                try:
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        info['page_count'] = len(pdf_reader.pages)
                        info['is_scanned'] = self.is_pdf_scanned(file_path)
                except Exception:
                    info['page_count'] = 0
                    info['is_scanned'] = True

            # Informations spécifiques aux images
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                try:
                    with Image.open(file_path) as img:
                        info['image_size'] = img.size
                        info['image_mode'] = img.mode
                except Exception:
                    pass

            return info

        except Exception as e:
            raise Exception(f"Erreur lors de la lecture des informations du fichier: {str(e)}")

    async def preview_text(self, file_path: str, max_chars: int = 500) -> str:
        """
        Obtenir un aperçu du texte extrait

        Args:
            file_path: Chemin vers le fichier
            max_chars: Nombre maximum de caractères à retourner

        Returns:
            str: Aperçu du texte
        """
        try:
            text = await self.extract_text(file_path)

            if len(text) <= max_chars:
                return text
            else:
                return text[:max_chars] + "..."

        except Exception as e:
            raise Exception(f"Erreur lors de la génération de l'aperçu: {str(e)}")