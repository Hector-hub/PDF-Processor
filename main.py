#!/usr/bin/env python3
"""
Pipeline Maestro: Descarga → Agentic-doc → Transformación Mistral
Orquestra todo el procesamiento de documentos con recuperación ante fallos
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
from typing import Dict, List, Optional
from enum import Enum
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Cargar variables de entorno
load_dotenv()

from mistralai import Mistral
from agentic_doc.parse import parse

# ============================================================================
# CONFIGURACIÓN Y ENUMS
# ============================================================================

class ProcessingStatus(str, Enum):
    """Estado del procesamiento de cada documento"""
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    AGENTIC_PROCESSED = "agentic_processed"
    TRANSFORMED = "transformed"
    COMPLETED = "completed"
    FAILED = "failed"

class PipelineManager:
    """
    Gestor central del pipeline con persistencia de estado y recuperación
    """
    
    def __init__(self, work_dir: str = "work", verbose: bool = False, aip_country: str = None):
        self.work_dir = Path(work_dir)
        self.verbose = verbose
        self.aip_country = aip_country  # País de la AIP (argentina, dominican_republic, etc)
        
        # Crear directorio principal de trabajo
        self.work_dir.mkdir(exist_ok=True)
        
        # Si se especifica country, el estado será independiente por país
        if self.aip_country:
            self.state_dir = self.work_dir / "_AIPs" / self.aip_country / "state"
        else:
            # Fallback a estado centralizado (para compatibilidad)
            self.state_dir = self.work_dir / "state"
        
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Los PDFs se guardarán por país (determinado dinámicamente)
        self.pdfs_dir = None  # Se establece dinámicamente según output_folder
        
        # Inicializar clientes
        self.mistral_client = Mistral(api_key=os.getenv('MISTRAL_API_KEY'))
        
        # Archivo de estado
        self.state_file = self.state_dir / "pipeline_state.json"
        self.state = self._load_state()
    
    def log(self, message: str, level: str = "INFO"):
        """Log con formato"""
        if self.verbose or level in ["ERROR", "WARNING"]:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            icon = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️", "DEBUG": "🔍"}
            print(f"[{timestamp}] {icon.get(level, '•')} {message}")
    
    def _load_state(self) -> Dict:
        """Cargar estado del procesamiento"""
        if self.state_file.exists():
            try:
                self.log(f"Cargando estado desde {self.state_file}", "DEBUG")
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    # Validar que tiene la estructura correcta
                    if isinstance(state, dict) and "documents" in state:
                        return state
            except (json.JSONDecodeError, IOError):
                pass
        
        return {
            "created_at": datetime.now().isoformat(),
            "documents": {},
            "pipeline_version": "1.0"
        }
    
    def _save_state(self):
        """Persistir estado del procesamiento"""
        self.state["updated_at"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
        self.log(f"Estado guardado en {self.state_file}", "DEBUG")
    
    def _get_document_id(self, url: str) -> str:
        """Generar ID único para un documento basado en la URL"""
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    def _get_filename_from_url(self, url: str) -> str:
        """Extrae el nombre original del archivo de la URL y asegura extensión .pdf"""
        parsed = urlparse(url)
        filename = parsed.path.split('/')[-1]
        
        # Si no hay filename o está vacío, generar uno
        if not filename:
            return f"document_{int(__import__('time').time())}.pdf"
        
        # Asegurarse de que tiene extensión .pdf
        if not filename.lower().endswith('.pdf'):
            filename = filename + '.pdf'
        
        return filename
    
    def _get_output_dirs(self, doc_id: str) -> tuple:
        """Obtener directorios de salida (pdfs, agentic_outputs, pdf_processed) basados en output_folder"""
        doc = self.get_document_status(doc_id)
        if not doc:
            raise ValueError(f"Documento no encontrado: {doc_id}")
        
        output_folder = doc.get("metadata", {}).get("output_folder", "")
        
        if output_folder:
            # Crear directorios dentro de work/{output_folder}
            pdfs_dir = self.work_dir / output_folder / "pdfs"
            agentic_dir = self.work_dir / output_folder / "agentic_outputs"
            pdf_processed_dir = self.work_dir / output_folder / "pdf_processed"
        else:
            # Fallback a directorios estándar (no recomendado)
            pdfs_dir = self.work_dir / "pdfs"
            agentic_dir = self.work_dir / "agentic_outputs"
            pdf_processed_dir = self.work_dir / "pdf_processed"
        
        # Crear directorios si no existen
        pdfs_dir.mkdir(parents=True, exist_ok=True)
        agentic_dir.mkdir(parents=True, exist_ok=True)
        pdf_processed_dir.mkdir(parents=True, exist_ok=True)
        
        return pdfs_dir, agentic_dir, pdf_processed_dir
    
    def add_document(self, url: str, doc_id: Optional[str] = None, original_filename: Optional[str] = None) -> str:
        """Agregar documento a procesar"""
        if doc_id is None:
            doc_id = self._get_document_id(url)
        
        if original_filename is None:
            original_filename = self._get_filename_from_url(url)
        
        if doc_id not in self.state["documents"]:
            self.state["documents"][doc_id] = {
                "url": url,
                "original_filename": original_filename,
                "metadata": {},  # Metadata adicional (país, sección, etc)
                "status": ProcessingStatus.PENDING,
                "created_at": datetime.now().isoformat(),
                "steps": {
                    "download": {"status": ProcessingStatus.PENDING, "timestamp": None},
                    "agentic_process": {"status": ProcessingStatus.PENDING, "timestamp": None},
                    "transform": {"status": ProcessingStatus.PENDING, "timestamp": None}
                },
                "files": {},
                "errors": []
            }
            self._save_state()
            self.log(f"Documento agregado: {doc_id} ({original_filename})")
        
        return doc_id
    
    def add_document_from_json(self, doc_info: Dict) -> str:
        """Agregar documento desde diccionario JSON con metadata completa"""
        url = doc_info.get("source")
        if not url:
            self.log("Error: falta 'source' en documento", "ERROR")
            return None
        
        # SIEMPRE tomar el name del JSON, es obligatorio
        original_filename = doc_info.get("name")
        if not original_filename:
            self.log(f"Error: falta 'name' en documento con URL {url}", "ERROR")
            return None
        
        # Asegurar que tiene extensión .pdf
        if not original_filename.lower().endswith('.pdf'):
            original_filename = original_filename + '.pdf'
        
        doc_id = self._get_document_id(url)
        
        # Si ya existe, retornar el ID (recovery)
        if doc_id in self.state["documents"]:
            self.log(f"Documento ya existe (recovery): {doc_id} ({original_filename})", "DEBUG")
            return doc_id
        
        # Crear entrada para el documento
        self.state["documents"][doc_id] = {
            "url": url,
            "original_filename": original_filename,
            "metadata": {
                "document_type": doc_info.get("document_type", "AIP"),
                "access": doc_info.get("access", "public"),
                "language": doc_info.get("language", ["english", "spanish"]),
                "country": doc_info.get("country", "unknown"),
                "publisher": doc_info.get("publisher", "unknown"),
                "section": doc_info.get("section", "GEN"),
                "output_folder": doc_info.get("output_folder", ""),
            },
            "status": ProcessingStatus.PENDING,
            "created_at": datetime.now().isoformat(),
            "steps": {
                "download": {"status": ProcessingStatus.PENDING, "timestamp": None},
                "agentic_process": {"status": ProcessingStatus.PENDING, "timestamp": None},
                "transform": {"status": ProcessingStatus.PENDING, "timestamp": None}
            },
            "files": {},
            "errors": []
        }
        self._save_state()
        self.log(f"Documento agregado: {doc_id} ({original_filename}) - {doc_info.get('country')} / {doc_info.get('section')}")
        
        return doc_id
    
    def get_document_status(self, doc_id: str) -> Dict:
        """Obtener estado de un documento"""
        return self.state["documents"].get(doc_id)
    
    def update_step_status(self, doc_id: str, step: str, status: ProcessingStatus, 
                          file_path: Optional[str] = None, error: Optional[str] = None):
        """Actualizar estado de un paso del procesamiento"""
        if doc_id not in self.state["documents"]:
            raise ValueError(f"Documento no encontrado: {doc_id}")
        
        doc = self.state["documents"][doc_id]
        doc["steps"][step]["status"] = status
        doc["steps"][step]["timestamp"] = datetime.now().isoformat()
        
        if file_path:
            doc["files"][step] = str(file_path)
        
        if error:
            doc["errors"].append({
                "step": step,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
        
        # Actualizar estado general
        all_steps = [s["status"] for s in doc["steps"].values()]
        if all(s == ProcessingStatus.COMPLETED for s in all_steps):
            doc["status"] = ProcessingStatus.COMPLETED
        elif any(s == ProcessingStatus.FAILED for s in all_steps):
            doc["status"] = ProcessingStatus.FAILED
        elif all(s in [ProcessingStatus.PENDING, ProcessingStatus.COMPLETED] for s in all_steps):
            doc["status"] = ProcessingStatus.DOWNLOADED if ProcessingStatus.PENDING not in all_steps else ProcessingStatus.PENDING
        
        self._save_state()
    
    # ========================================================================
    # PASO 1: DESCARGA DE PDF
    # ========================================================================
    
    def download_pdf(self, doc_id: str) -> bool:
        """Descargar PDF desde URL (con skip si ya existe)"""
        doc = self.get_document_status(doc_id)
        if not doc:
            self.log(f"Documento no encontrado: {doc_id}", "ERROR")
            return False
        
        url = doc["url"]
        # Usar el nombre original guardado, NO extraer de la URL
        filename = doc.get("original_filename", self._get_filename_from_url(url))
        
        # Obtener directorios dinámicos (incluyendo pdfs_dir)
        pdfs_dir, _, _ = self._get_output_dirs(doc_id)
        pdf_path = pdfs_dir / filename
        
        # Si ya está descargado, saltar
        if pdf_path.exists():
            self.log(f"PDF ya descargado: {filename}")
            self.update_step_status(doc_id, "download", ProcessingStatus.COMPLETED, str(pdf_path))
            return True
        
        self.log(f"Descargando PDF: {filename} desde {url}", "INFO")
        
        try:
            import requests
            from urllib3.exceptions import InsecureRequestWarning
            import urllib3
            urllib3.disable_warnings(InsecureRequestWarning)
            
            response = requests.get(url, verify=False, timeout=30)
            response.raise_for_status()
            
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            
            self.log(f"PDF descargado: {filename} ({len(response.content) / 1024 / 1024:.2f} MB)", "SUCCESS")
            self.update_step_status(doc_id, "download", ProcessingStatus.COMPLETED, str(pdf_path))
            return True
            
        except Exception as e:
            error_msg = f"Error descargando PDF: {str(e)}"
            self.log(error_msg, "ERROR")
            self.update_step_status(doc_id, "download", ProcessingStatus.FAILED, error=error_msg)
            return False
    
    # ========================================================================
    # PASO 2: PROCESAR CON AGENTIC-DOC
    # ========================================================================
    
    def process_with_agentic_doc(self, doc_id: str) -> bool:
        """Procesar PDF con Agentic Document Extraction"""
        doc = self.get_document_status(doc_id)
        if not doc:
            self.log(f"Documento no encontrado: {doc_id}", "ERROR")
            return False
        
        # Verificar que el PDF está descargado
        if doc["steps"]["download"]["status"] != ProcessingStatus.COMPLETED:
            self.log(f"PDF no descargado para {doc_id}", "WARNING")
            return False
        
        pdf_path = Path(doc["files"]["download"])
        
        # Obtener directorios de salida basados en output_folder
        _, agentic_outputs_dir, _ = self._get_output_dirs(doc_id)
        
        # Usar nombre original para el archivo JSON (sin sufijo)
        original_filename_no_ext = doc.get("original_filename", f"document_{doc_id}").rsplit('.', 1)[0]
        output_json_path = agentic_outputs_dir / f"{original_filename_no_ext}.json"
        
        # Si ya está procesado, saltar
        if output_json_path.exists():
            self.log(f"Agentic-doc output ya existe: {output_json_path.name}")
            self.update_step_status(doc_id, "agentic_process", ProcessingStatus.COMPLETED, str(output_json_path))
            return True
        
        self.log(f"Procesando con Agentic-doc: {pdf_path.name}", "INFO")
        
        try:
            # Procesar documento con agentic-doc
            result = parse(str(pdf_path), result_save_dir=None)
            
            # Extraer información
            chunks_list = []
            figure_chunks = []  # Chunks de tipo figura/imagen
            markdown_text = ""
            total_chars = 0
            
            # Procesar los resultados
            if result and len(result) > 0:
                doc_result = result[0]
                
                # Obtener markdown
                if hasattr(doc_result, 'markdown'):
                    markdown_text = doc_result.markdown
                    total_chars = len(markdown_text)
                
                # Procesar chunks
                if hasattr(doc_result, 'chunks') and doc_result.chunks:
                    for i, chunk in enumerate(doc_result.chunks):
                        chunk_type_str = str(chunk.chunk_type)
                        
                        # Separar figuras del resto
                        if "figure" in chunk_type_str.lower():
                            figure_chunks.append(chunk)
                        else:
                            chunk_data = {
                                "id": f"chunk_{i}",
                                "content": chunk.text if hasattr(chunk, 'text') else str(chunk),
                                "type": chunk_type_str,
                            }
                            
                            # Agregar información de ubicación si existe
                            if hasattr(chunk, 'grounding') and chunk.grounding:
                                grounding_list = []
                                for grounding in chunk.grounding:
                                    grounding_data = {}
                                    if hasattr(grounding, 'page'):
                                        grounding_data['page'] = grounding.page + 1  # Convertir de 0-indexed a 1-indexed
                                    if hasattr(grounding, 'box') and grounding.box:
                                        grounding_data['bbox'] = grounding.box.model_dump() if hasattr(grounding.box, 'model_dump') else str(grounding.box)
                                    grounding_list.append(grounding_data)
                                chunk_data['grounding'] = grounding_list
                            
                            chunks_list.append(chunk_data)
            
            agentic_output = {
                "metadata": {
                    "document_id": doc_id,
                    "source_url": doc["url"],
                    "pdf_path": str(pdf_path),
                    "processed_date": datetime.now().isoformat(),
                    "total_chunks": len(chunks_list),
                    "total_figures": len(figure_chunks),
                    "total_characters": total_chars
                },
                "document": {
                    "id": doc_id,
                    "filename": doc.get("original_filename", "unknown"),
                    "markdown": markdown_text,
                    "chunks": chunks_list,
                    "figures": []
                }
            }
            
            # Procesar figuras
            for i, figure_chunk in enumerate(figure_chunks):
                figure_data = {
                    "id": f"figure_{i}",
                    "text": figure_chunk.text if hasattr(figure_chunk, 'text') else "",
                    "type": str(figure_chunk.chunk_type)
                }
                
                # Agregar grounding de figuras
                if hasattr(figure_chunk, 'grounding') and figure_chunk.grounding:
                    grounding_list = []
                    for grounding in figure_chunk.grounding:
                        grounding_data = {}
                        if hasattr(grounding, 'page'):
                            grounding_data['page'] = grounding.page + 1  # Convertir de 0-indexed a 1-indexed
                        if hasattr(grounding, 'box') and grounding.box:
                            grounding_data['bbox'] = grounding.box.model_dump() if hasattr(grounding.box, 'model_dump') else str(grounding.box)
                        grounding_list.append(grounding_data)
                    figure_data['grounding'] = grounding_list
                
                agentic_output["document"]["figures"].append(figure_data)
            
            # Guardar JSON
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(agentic_output, f, ensure_ascii=False, indent=2)
            
            self.log(f"Agentic-doc completado: {output_json_path.name} ({len(chunks_list)} chunks, {len(figure_chunks)} figuras)", "SUCCESS")
            self.update_step_status(doc_id, "agentic_process", ProcessingStatus.COMPLETED, str(output_json_path))
            return True
            
        except Exception as e:
            error_msg = f"Error procesando con Agentic-doc: {str(e)}"
            self.log(error_msg, "ERROR")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", "DEBUG")
            self.update_step_status(doc_id, "agentic_process", ProcessingStatus.FAILED, error=error_msg)
            return False
    
    # ========================================================================
    # PASO 3: TRANSFORMAR A PDF_PROCESSED CON MISTRAL
    # ========================================================================
    
    def transform_to_pdf_processed(self, doc_id: str) -> bool:
        """Transformar JSON de Agentic-doc a pdf_processed usando Mistral"""
        doc = self.get_document_status(doc_id)
        if not doc:
            self.log(f"Documento no encontrado: {doc_id}", "ERROR")
            return False
        
        # Verificar que agentic-doc está completo
        if doc["steps"]["agentic_process"]["status"] != ProcessingStatus.COMPLETED:
            self.log(f"Agentic-doc no completado para {doc_id}", "WARNING")
            return False
        
        agentic_json_path = Path(doc["files"]["agentic_process"])
        
        # Obtener directorios de salida basados en output_folder
        _, _, pdf_processed_dir = self._get_output_dirs(doc_id)
        
        # Usar nombre original para el archivo PDF transformado (sin sufijo)
        original_filename_no_ext = doc.get("original_filename", f"document_{doc_id}").rsplit('.', 1)[0]
        pdf_processed_path = pdf_processed_dir / f"{original_filename_no_ext}.json"
        
        # Si ya está transformado, saltar
        if pdf_processed_path.exists():
            self.log(f"PDF_processed ya existe: {pdf_processed_path.name}")
            self.update_step_status(doc_id, "transform", ProcessingStatus.COMPLETED, str(pdf_processed_path))
            return True
        
        self.log(f"Transformando a pdf_processed: {agentic_json_path.name}", "INFO")
        
        try:
            # Cargar JSON de agentic-doc
            with open(agentic_json_path, 'r', encoding='utf-8') as f:
                agentic_json = json.load(f)
            
            # Usar Mistral para transformación
            pdf_processed = self._mistral_transform(doc_id, agentic_json, doc)
            
            if not pdf_processed:
                error_msg = "Error en transformación de Mistral"
                self.log(error_msg, "ERROR")
                self.update_step_status(doc_id, "transform", ProcessingStatus.FAILED, error=error_msg)
                return False
            
            # Guardar JSON transformado
            with open(pdf_processed_path, 'w', encoding='utf-8') as f:
                json.dump(pdf_processed, f, ensure_ascii=False, indent=2)
            
            self.log(f"Transformación completada: {pdf_processed_path}", "SUCCESS")
            self.update_step_status(doc_id, "transform", ProcessingStatus.COMPLETED, str(pdf_processed_path))
            
            # Marcar como completado
            doc = self.state["documents"][doc_id]
            doc["status"] = ProcessingStatus.COMPLETED
            self._save_state()
            
            return True
            
        except Exception as e:
            error_msg = f"Error transformando: {str(e)}"
            self.log(error_msg, "ERROR")
            self.update_step_status(doc_id, "transform", ProcessingStatus.FAILED, error=error_msg)
            return False
    
    def _mistral_transform(self, doc_id: str, agentic_json: Dict, doc: Dict) -> Optional[Dict]:
        """Transformar JSON de agentic-doc a pdf_processed con Mistral para estructuración"""
        self.log(f"Transformando documento con Mistral para {doc_id}...", "DEBUG")
        
        # Extraer metadatos
        doc_metadata = doc.get("metadata", {})
        doc_name = doc.get("original_filename", "unknown").rsplit('.', 1)[0]
        source_url = agentic_json.get('metadata', {}).get('source_url', 'unknown')
        
        # Obtener chunks y figuras
        chunks = agentic_json.get("document", {}).get("chunks", [])
        figures = agentic_json.get("document", {}).get("figures", [])
        
        # Agrupar chunks por página
        pages_dict = {}
        for chunk in chunks:
            grounding = chunk.get("grounding", [])
            if grounding:
                for ground in grounding:
                    page_num = ground.get("page", 1)
                    if page_num not in pages_dict:
                        pages_dict[page_num] = []
                    pages_dict[page_num].append(chunk)
            else:
                if 1 not in pages_dict:
                    pages_dict[1] = []
                pages_dict[1].append(chunk)
        
        # Agrupar figuras por página
        figures_dict = {}
        for fig in figures:
            grounding = fig.get("grounding", [])
            if grounding:
                for ground in grounding:
                    page_num = ground.get("page", 1)
                    if page_num not in figures_dict:
                        figures_dict[page_num] = []
                    figures_dict[page_num].append(fig)
            else:
                if 1 not in figures_dict:
                    figures_dict[1] = []
                figures_dict[1].append(fig)
        
        # Construir content para todas las páginas
        content = []
        total_pages = max(pages_dict.keys()) if pages_dict else 1
        
        for page_num in range(1, total_pages + 1):
            # Extraer texto de la página
            page_chunks = pages_dict.get(page_num, [])
            page_text = "\n".join([chunk.get("content", "") for chunk in page_chunks])
            
            # Usar Mistral para estructurar el texto de la página
            structured_page = self._mistral_structure_page(doc_name, page_text, doc_metadata, source_url)
            
            # Extraer y estructurar figuras de la página
            page_figures = figures_dict.get(page_num, [])
            structured_images = []
            
            for i, fig in enumerate(page_figures):
                fig_text = fig.get("text", "")
                structured_fig = self._mistral_structure_image(fig_text, i, page_num, doc_metadata)
                if structured_fig:
                    structured_images.append(structured_fig)
            
            # Crear objeto de página
            page_obj = {
                "page_number": page_num,
                "text": page_text,
                "structured_page_content": structured_page,
                "structured_image_content": structured_images,
                "text_embedding": []
            }
            
            content.append(page_obj)
        
        # Construir JSON final
        pdf_processed = {
            "metadata": {
                "document_name": doc_name,
                "total_pages": total_pages,
                "document_type": doc_metadata.get('document_type', 'AIP'),
                "source": source_url,
                "processing_stack": ["agentic-doc", "mistral-codestral"],
                "processed_date": datetime.now().isoformat(),
                "country": doc_metadata.get('country', 'unknown'),
                "publisher": doc_metadata.get('publisher', 'unknown'),
                "section": doc_metadata.get('section', 'GEN'),
                "access": doc_metadata.get('access', 'public'),
                "language": doc_metadata.get('language', ['english', 'spanish']),
                "total_chunks": len(chunks),
                "total_figures": len(figures)
            },
            "content": content
        }
        
        self.log(f"Documento transformado: {total_pages} páginas, {len(chunks)} chunks, {len(figures)} figuras", "DEBUG")
        
        return pdf_processed
    
    def _mistral_structure_page(self, doc_name: str, page_text: str, doc_metadata: Dict, source_url: str) -> Dict:
        """Usar Mistral para estructurar el contenido de texto de una página"""
        if not page_text or not page_text.strip():
            return {
                "file_name": doc_name,
                "topics": ["aviation", "navigation", "charts"],
                "languages": doc_metadata.get('language', ['english', 'spanish']),
                "description": "Empty page",
                "ocr_contents": {}
            }
        
        prompt = (
            "This is the pages OCR in markdown:\n"
            "====MARKDOWN====\n"
            f"{page_text}\n"
            "====END MARKDOWN====\n"
            "Convert this into a structured JSON response with the following fields:\n"
            "- file_name: string\n"
            "- topics: list of strings\n"
            "- languages: list of strings\n"
            "- description: string\n"
            "- ocr_contents: dictionary with the main extracted information\n"
            "Respond only with the JSON object."
        )
        
        try:
            response = self.mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=4000
            )
            
            result = response.choices[0].message.content
            return json.loads(result)
        except Exception as e:
            self.log(f"Error estructurando página con Mistral: {str(e)}", "WARNING")
        
        # Fallback si falla Mistral
        return {
            "file_name": doc_name,
            "topics": ["aviation", "navigation", "charts"],
            "languages": doc_metadata.get('language', ['english', 'spanish']),
            "description": "Page content from aeronautical document",
            "ocr_contents": {
                "raw_content": page_text[:500]
            }
        }
    
    def _mistral_structure_image(self, image_text: str, index: int, page_num: int, doc_metadata: Dict) -> Optional[Dict]:
        """Usar Mistral para estructurar el contenido extraído de una imagen"""
        if not image_text or not image_text.strip():
            return None
        
        prompt = (
            "This is the image OCR in markdown:\n"
            "====MARKDOWN====\n"
            f"{image_text}\n"
            "====END MARKDOWN====\n"
            "Convert this into a structured JSON response with the following fields:\n"
            "- file_name: string\n"
            "- topics: list of strings\n"
            "- languages: list of strings\n"
            "- description: string\n"
            "- ocr_contents: dictionary with the main extracted information\n"
            "Respond only with the JSON object."
        )
        
        try:
            response = self.mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=3000
            )
            
            result = response.choices[0].message.content
            return json.loads(result)
        except Exception as e:
            self.log(f"Error estructurando imagen con Mistral: {str(e)}", "WARNING")
        
        # Fallback
        return {
            "file_name": f"imagen_p{page_num}_i{index}.jpg",
            "topics": ["aeronautical_charts", "navigation"],
            "languages": doc_metadata.get('language', ['english', 'spanish']),
            "description": "Image from aeronautical document",
            "ocr_contents": {
                "raw_content": image_text[:200]
            }
        }
    
    # ========================================================================
    # ORQUESTACIÓN PRINCIPAL
    # ========================================================================
    
    def process_all_documents(self, urls: List[str]) -> Dict:
        """Procesar lista de URLs a través del pipeline completo"""
        self.log("=" * 60, "INFO")
        self.log("INICIANDO PIPELINE MAESTRO", "INFO")
        self.log("=" * 60, "INFO")
        
        # Agregar documentos
        doc_ids = [self.add_document(url) for url in urls]
        
        results = {
            "started_at": datetime.now().isoformat(),
            "total_documents": len(doc_ids),
            "documents": {}
        }
        
        # Procesar cada documento
        for i, doc_id in enumerate(doc_ids, 1):
            self.log(f"\n[{i}/{len(doc_ids)}] Procesando documento: {doc_id}", "INFO")
            
            # Paso 1: Descargar
            if not self.download_pdf(doc_id):
                results["documents"][doc_id] = {"status": "failed", "step": "download"}
                continue
            
            # Paso 2: Agentic-doc
            if not self.process_with_agentic_doc(doc_id):
                results["documents"][doc_id] = {"status": "failed", "step": "agentic_process"}
                continue
            
            # Paso 3: Transformar
            if not self.transform_to_pdf_processed(doc_id):
                results["documents"][doc_id] = {"status": "failed", "step": "transform"}
                continue
            
            results["documents"][doc_id] = {"status": "completed"}
            self.log(f"✅ Documento {doc_id} completado", "SUCCESS")
        
        results["completed_at"] = datetime.now().isoformat()
        
        # Mostrar resumen
        self._print_summary(results)
        
        return results
    
    def process_all_documents_from_json(self, documents: List[Dict]) -> Dict:
        """Procesar documentos desde array JSON con metadata"""
        self.log("=" * 60, "INFO")
        self.log("INICIANDO PIPELINE MAESTRO (desde JSON)", "INFO")
        self.log("=" * 60, "INFO")
        
        # Agregar documentos desde JSON
        doc_ids = []
        for doc_info in documents:
            doc_id = self.add_document_from_json(doc_info)
            if doc_id:
                doc_ids.append((doc_id, doc_info))
        
        results = {
            "started_at": datetime.now().isoformat(),
            "total_documents": len(doc_ids),
            "documents": {}
        }
        
        # Procesar cada documento (solo los no completados)
        for i, (doc_id, doc_info) in enumerate(doc_ids, 1):
            doc_status = self.state["documents"][doc_id]
            
            # Si ya está completado, saltar
            if doc_status["status"] == ProcessingStatus.COMPLETED:
                self.log(f"[{i}/{len(doc_ids)}] Documento ya procesado (recovery): {doc_id}", "DEBUG")
                results["documents"][doc_id] = {"status": "completed", "recovered": True}
                continue
            
            self.log(f"\n[{i}/{len(doc_ids)}] Procesando documento: {doc_id} ({doc_info['name']})", "INFO")
            
            # Paso 1: Descargar (saltar si ya está descargado)
            if doc_status["steps"]["download"]["status"] != ProcessingStatus.COMPLETED:
                if not self.download_pdf(doc_id):
                    results["documents"][doc_id] = {"status": "failed", "step": "download"}
                    continue
            else:
                self.log(f"PDF ya descargado (recovery): {doc_info['name']}", "DEBUG")
            
            # Paso 2: Agentic-doc (saltar si ya está procesado)
            if doc_status["steps"]["agentic_process"]["status"] != ProcessingStatus.COMPLETED:
                if not self.process_with_agentic_doc(doc_id):
                    results["documents"][doc_id] = {"status": "failed", "step": "agentic_process"}
                    continue
            else:
                self.log(f"Agentic-doc ya procesado (recovery): {doc_info['name']}", "DEBUG")
            
            # Paso 3: Transformar (saltar si ya está transformado)
            if doc_status["steps"]["transform"]["status"] != ProcessingStatus.COMPLETED:
                if not self.transform_to_pdf_processed(doc_id):
                    results["documents"][doc_id] = {"status": "failed", "step": "transform"}
                    continue
            else:
                self.log(f"Transformación completada (recovery): {doc_info['name']}", "DEBUG")
            
            results["documents"][doc_id] = {"status": "completed"}
            self.log(f"✅ Documento {doc_id} completado", "SUCCESS")
        
        results["completed_at"] = datetime.now().isoformat()
        
        # Mostrar resumen
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict):
        """Mostrar resumen del procesamiento"""
        self.log("\n" + "=" * 60, "INFO")
        self.log("RESUMEN DEL PROCESAMIENTO", "INFO")
        self.log("=" * 60, "INFO")
        
        completed = sum(1 for r in results["documents"].values() if r["status"] == "completed")
        failed = sum(1 for r in results["documents"].values() if r["status"] == "failed")
        
        self.log(f"Total de documentos: {results['total_documents']}", "INFO")
        self.log(f"Completados: {completed}", "SUCCESS")
        self.log(f"Fallidos: {failed}", "ERROR" if failed > 0 else "INFO")
        
        self.log(f"\n📁 Estructura organizada por país en: {self.work_dir}", "INFO")
        
        # Mostrar estructura de salida por output_folder
        output_folders = set()
        for doc_id, doc_info in self.state["documents"].items():
            output_folder = doc_info.get("metadata", {}).get("output_folder", "")
            if output_folder:
                output_folders.add(output_folder)
        
        for folder in sorted(output_folders):
            country_path = self.work_dir / folder
            pdfs_path = country_path / "pdfs"
            agentic_path = country_path / "agentic_outputs"
            pdf_proc_path = country_path / "pdf_processed"
            self.log(f"  📦 {folder}/", "INFO")
            if pdfs_path.exists():
                self.log(f"     ├─ pdfs/ ({len(list(pdfs_path.glob('*.pdf')))} archivos)", "DEBUG")
            if agentic_path.exists():
                self.log(f"     ├─ agentic_outputs/ ({len(list(agentic_path.glob('*.json')))} archivos)", "DEBUG")
            if pdf_proc_path.exists():
                self.log(f"     └─ pdf_processed/ ({len(list(pdf_proc_path.glob('*.json')))} archivos)", "DEBUG")
        
    def get_final_files(self) -> Dict[str, Dict[str, str]]:
        """Retornar mapeo de archivos finales por documento"""
        files_map = {}
        for doc_id, doc_info in self.state["documents"].items():
            if doc_info["status"] == ProcessingStatus.COMPLETED:
                files_map[doc_id] = {
                    "pdf": doc_info["files"].get("download"),
                    "agentic_json": doc_info["files"].get("agentic_process"),
                    "pdf_processed_json": doc_info["files"].get("transform"),
                    "url": doc_info["url"]
                }
        return files_map

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Pipeline Maestro: Descarga → Agentic-doc → PDF-Processed'
    )
    parser.add_argument(
        '--aip',
        default=None,
        choices=['argentina', 'dominican_republic', 'spain'],
        help='AIP a procesar: argentina, dominican_republic, o spain'
    )
    parser.add_argument(
        '--docs-json', '-d',
        default=None,
        help='Ruta del archivo JSON con array de documentos a procesar (auto-detecta si no se proporciona)'
    )
    parser.add_argument(
        '--work-dir', '-w',
        default='work',
        help='Directorio de trabajo (default: work)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Modo verbose'
    )
    
    args = parser.parse_args()
    
    # Si no se especifica JSON, intentar encontrarlo en docs_to_process
    docs_json_path = args.docs_json
    aip_country = args.aip  # Puede ser None, 'argentina', 'dominican_republic', o 'spain'
    
    if not docs_json_path:
        if aip_country:
            # Si se especifica AIP, buscar su JSON
            docs_json_path = str(Path(args.work_dir) / "_AIPs" / aip_country / "docs_to_process" / f"{aip_country}_Docs_AIP_links.json")
            if not Path(docs_json_path).exists():
                print(f"❌ Error: Archivo JSON no encontrado para {aip_country}")
                print(f"   Esperado: {docs_json_path}")
                sys.exit(1)
        else:
            # Si no se especifica AIP, buscar automáticamente
            possible_paths = [
                Path(args.work_dir) / "_AIPs" / "argentina" / "docs_to_process" / "argentina_Docs_AIP_links.json",
                Path(args.work_dir) / "_AIPs" / "dominican_republic" / "docs_to_process" / "dominican_republic_Docs_AIP_links.json",
                Path(args.work_dir) / "_AIPs" / "spain" / "docs_to_process" / "spain_Docs_AIP_links.json",
                Path("work") / "_AIPs" / "argentina" / "docs_to_process" / "argentina_Docs_AIP_links.json",
                Path("work") / "_AIPs" / "dominican_republic" / "docs_to_process" / "dominican_republic_Docs_AIP_links.json",
                Path("work") / "_AIPs" / "spain" / "docs_to_process" / "spain_Docs_AIP_links.json",
            ]
            
            for possible_path in possible_paths:
                if possible_path.exists():
                    docs_json_path = str(possible_path)
                    # Detectar AIP del path
                    parts = possible_path.parts
                    for i, part in enumerate(parts):
                        if part == "_AIPs" and i + 1 < len(parts):
                            aip_country = parts[i + 1]
                            break
                    print(f"✅ Archivo JSON detectado automáticamente: {docs_json_path}")
                    break
            
            if not docs_json_path:
                print("❌ Error: No se encontró archivo JSON")
                print("   Opciones:")
                print("   1. Proporciona --aip argentina|dominican_republic|spain")
                print("   2. Proporciona --docs-json <ruta>")
                print("   3. Coloca el JSON en: work/_AIPs/{aip}/docs_to_process/{aip}_Docs_AIP_links.json")
                sys.exit(1)
    
    # Cargar documentos desde JSON
    try:
        with open(docs_json_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        if not isinstance(documents, list):
            print("❌ Error: El archivo JSON debe contener un array de documentos")
            sys.exit(1)
        
        print(f"\n✅ Cargados {len(documents)} documentos desde {docs_json_path}")
    except FileNotFoundError:
        print(f"❌ Error: Archivo no encontrado: {docs_json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error al parsear JSON: {e}")
        sys.exit(1)
    
    # Si aún no tenemos el país (cuando se usa --docs-json), intentar detectarlo del output_folder
    if not aip_country:
        if documents and len(documents) > 0:
            output_folder = documents[0].get("output_folder", "")
            if output_folder:
                # output_folder es como "_AIPs/argentina" o "_AIPs/dominican_republic"
                parts = output_folder.split('/')
                if len(parts) == 2 and parts[0] == "_AIPs":
                    aip_country = parts[1]
    
    if not aip_country:
        print("❌ Error: No se pudo determinar el AIP")
        print("   Proporciona --aip argentina|dominican_republic|spain")
        sys.exit(1)
    
    # Crear gestor con el país detectado
    manager = PipelineManager(work_dir=args.work_dir, verbose=args.verbose, aip_country=aip_country)
    
    # Procesar documentos
    results = manager.process_all_documents_from_json(documents)
    
    # Mostrar archivos finales
    files_map = manager.get_final_files()
    if files_map:
        print("\n" + "=" * 60)
        print("ARCHIVOS GENERADOS:")
        print("=" * 60)
        for doc_id, files in files_map.items():
            print(f"\n📄 {doc_id}:")

            print(f"  PDF: {files['pdf']}")
            print(f"  Agentic JSON: {files['agentic_json']}")
            print(f"  PDF Processed JSON: {files['pdf_processed_json']}")
    
    # Guardar resumen en la carpeta de la AIP
    if aip_country:
        summary_path = Path(args.work_dir) / "_AIPs" / aip_country / "state" / "final_results.json"
    else:
        summary_path = Path(args.work_dir) / "state" / "final_results.json"
    
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Resumen guardado en: {summary_path}")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
